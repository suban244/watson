"""Client for a self-hosted Fizzy (https://github.com/basecamp/fizzy).

Endpoints follow the published OpenAPI spec in basecamp/fizzy-sdk. Everything
except identity lives under the account slug: `/{account}/boards.json`.

Fizzy's assignment and tagging endpoints toggle, so callers must check the
card's current state before calling `toggle_assignment` / `toggle_tag`.
"""

import asyncio
from typing import Any, Literal

import httpx

from config import settings
from schema.fizzy import (
    FizzyBoard,
    FizzyCard,
    FizzyCardDetail,
    FizzyColumn,
    FizzyComment,
    FizzyStep,
    FizzyTag,
    FizzyUser,
)

TIMEOUT = httpx.Timeout(10.0)
LIMITS = httpx.Limits(max_connections=10, max_keepalive_connections=5)

# Lanes Fizzy can filter `cards.json` by; omitting it means open cards.
CardLane = Literal["maybe", "not_now", "closed", "golden", "stalled", "all"]

_my_user_id: str | None = None
_shared_client: httpx.AsyncClient | None = None


def is_configured() -> bool:
    return bool(
        settings.FIZZY_API_URL and settings.FIZZY_TOKEN and settings.FIZZY_ACCOUNT
    )


def _client() -> httpx.AsyncClient:
    """One client per process, created on first use so it binds to the running
    loop (the bot shares FastAPI's), and reused so connections stay warm."""
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.AsyncClient(
            base_url=settings.FIZZY_API_URL.rstrip("/"),
            headers={
                "Authorization": f"Bearer {settings.FIZZY_TOKEN}",
                "Accept": "application/json",
            },
            timeout=TIMEOUT,
            limits=LIMITS,
        )
    return _shared_client


async def aclose() -> None:
    global _shared_client
    if _shared_client is not None:
        await _shared_client.aclose()
        _shared_client = None


def _account_path(path: str) -> str:
    return f"/{settings.FIZZY_ACCOUNT.strip('/')}{path}"


def _error_message(response: httpx.Response) -> str:
    if response.status_code in (401, 403):
        return (
            "Fizzy rejected the request; the access token may be wrong or lack access."
        )
    if response.status_code == 404:
        return "Fizzy has no such record."
    try:
        detail = response.json()
    except ValueError:
        detail = response.text[:200]
    return f"Fizzy refused the request ({response.status_code}): {detail}"


async def _request(
    method: str,
    path: str,
    *,
    json: dict | None = None,
    params: dict | list | None = None,
    account: bool = True,
) -> Any:
    url = _account_path(path) if account else path
    client = _client()
    try:
        response = await client.request(method, url, json=json, params=params)
        if response.is_error:
            raise ValueError(_error_message(response))

        # Creates may answer 201 with an empty body and a Location header.
        location = response.headers.get("Location")
        if not response.content and location and method == "POST":
            response = await client.get(location)
            if response.is_error:
                raise ValueError(_error_message(response))
    except httpx.HTTPError as exc:
        raise ValueError(
            f"Could not reach Fizzy at {settings.FIZZY_API_URL}: {exc}"
        ) from exc

    return response.json() if response.content else None


async def _get_list(path: str, params: list | None = None, *, limit: int) -> list[dict]:
    """GET a paginated list, following `Link: rel=next` until `limit` items."""
    items: list[dict] = []
    client = _client()
    try:
        response = await client.get(_account_path(path), params=params)
        while True:
            if response.is_error:
                raise ValueError(_error_message(response))
            items.extend(response.json())
            next_url = response.links.get("next", {}).get("url")
            if len(items) >= limit or not next_url:
                break
            response = await client.get(next_url)
    except httpx.HTTPError as exc:
        raise ValueError(
            f"Could not reach Fizzy at {settings.FIZZY_API_URL}: {exc}"
        ) from exc
    return items[:limit]


async def my_user_id() -> str:
    """The token owner's user id in the configured account."""
    global _my_user_id
    if _my_user_id is None:
        identity = await _request("GET", "/my/identity.json", account=False)
        wanted = settings.FIZZY_ACCOUNT.strip("/")
        for account in identity.get("accounts", []):
            if account.get("slug", "").strip("/") == wanted and account.get("user"):
                _my_user_id = account["user"]["id"]
                break
        else:
            raise ValueError(f"The Fizzy token has no access to account '{wanted}'.")
    assert _my_user_id is not None
    return _my_user_id


async def list_boards(*, with_columns: bool = False) -> list[FizzyBoard]:
    boards = [
        FizzyBoard.model_validate(b) for b in await _get_list("/boards.json", limit=200)
    ]
    if with_columns:
        columns = await asyncio.gather(*(list_columns(board.id) for board in boards))
        for board, board_columns in zip(boards, columns, strict=True):
            board.columns = board_columns
    return boards


async def list_columns(board_id: str) -> list[FizzyColumn]:
    data = await _request("GET", f"/boards/{board_id}/columns.json")
    return [FizzyColumn.model_validate(c) for c in data]


async def list_users() -> list[FizzyUser]:
    users = await _get_list("/users.json", limit=500)
    return [FizzyUser.model_validate(u) for u in users if u.get("active", True)]


async def list_tags() -> list[FizzyTag]:
    return [
        FizzyTag.model_validate(t) for t in await _get_list("/tags.json", limit=500)
    ]


async def list_cards(
    *,
    board_ids: list[str] | None = None,
    assignee_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    terms: list[str] | None = None,
    lane: CardLane | None = None,
    limit: int = 20,
) -> list[FizzyCard]:
    params: list[tuple[str, str]] = []
    params += [("board_ids[]", i) for i in board_ids or []]
    params += [("assignee_ids[]", i) for i in assignee_ids or []]
    params += [("tag_ids[]", i) for i in tag_ids or []]
    params += [("terms[]", t) for t in terms or []]
    if lane:
        params.append(("indexed_by", lane))
    cards = await _get_list("/cards.json", params, limit=limit)
    return [FizzyCard.model_validate(c) for c in cards]


async def get_card(number: int) -> FizzyCard:
    try:
        return FizzyCard.model_validate(await _request("GET", f"/cards/{number}"))
    except ValueError as exc:
        if "no such record" in str(exc):
            raise ValueError(f"There is no Fizzy card #{number}.") from exc
        raise


async def get_card_detail(number: int, *, comment_limit: int = 20) -> FizzyCardDetail:
    card, comments = await asyncio.gather(
        get_card(number),
        _get_list(f"/cards/{number}/comments.json", limit=comment_limit),
    )
    return FizzyCardDetail(
        **card.model_dump(exclude={"lane"}),
        comments=[FizzyComment.model_validate(c) for c in comments],
    )


async def create_card(
    *,
    board_id: str,
    title: str,
    description: str | None = None,
    column_id: str | None = None,
    assignee_ids: list[str] | None = None,
    tag_names: list[str] | None = None,
) -> FizzyCard:
    body: dict[str, Any] = {"board_id": board_id, "title": title}
    if description:
        body["description"] = description
    if column_id:
        body["column_id"] = column_id
    if assignee_ids:
        body["assignee_ids"] = assignee_ids
    if tag_names:
        body["tag_names"] = tag_names
    return FizzyCard.model_validate(await _request("POST", "/cards.json", json=body))


async def update_card(
    number: int, *, title: str | None = None, description: str | None = None
) -> FizzyCard:
    body = {
        k: v
        for k, v in {"title": title, "description": description}.items()
        if v is not None
    }
    await _request("PATCH", f"/cards/{number}", json=body)
    return await get_card(number)


async def close_card(number: int) -> None:
    await _request("POST", f"/cards/{number}/closure.json")


async def reopen_card(number: int) -> None:
    await _request("DELETE", f"/cards/{number}/closure.json")


async def postpone_card(number: int) -> None:
    await _request("POST", f"/cards/{number}/not_now.json")


async def triage_card(number: int, column_id: str) -> None:
    await _request(
        "POST", f"/cards/{number}/triage.json", json={"column_id": column_id}
    )


async def untriage_card(number: int) -> None:
    await _request("DELETE", f"/cards/{number}/triage.json")


async def move_card_to_board(
    number: int, board_id: str, column_id: str | None = None
) -> None:
    body = {"board_id": board_id}
    if column_id:
        body["column_id"] = column_id
    await _request("PATCH", f"/cards/{number}/board.json", json=body)


async def toggle_assignment(number: int, user_id: str) -> None:
    await _request(
        "POST", f"/cards/{number}/assignments.json", json={"assignee_id": user_id}
    )


async def toggle_tag(number: int, tag_title: str) -> None:
    await _request(
        "POST", f"/cards/{number}/taggings.json", json={"tag_title": tag_title}
    )


async def add_comment(number: int, body: str) -> FizzyComment:
    data = await _request("POST", f"/cards/{number}/comments.json", json={"body": body})
    return FizzyComment.model_validate(data)


async def add_step(number: int, content: str) -> FizzyStep:
    data = await _request(
        "POST", f"/cards/{number}/steps.json", json={"content": content}
    )
    return FizzyStep.model_validate(data)


async def set_step_completed(number: int, step_id: str, *, completed: bool) -> None:
    await _request(
        "PATCH", f"/cards/{number}/steps/{step_id}", json={"completed": completed}
    )
