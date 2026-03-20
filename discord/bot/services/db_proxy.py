import uuid

import httpx
from core.config import settings
from core.schema import Transaction
import logfire


class DB_Proxy_Hook:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.client = httpx.AsyncClient(base_url=db_url)

    @logfire.instrument("add_transaction", record_return=True)
    async def add_transaction(self, transaction_data: Transaction):
        response = await self.client.post(
            "/transactions/",
            json=transaction_data.model_dump(mode="json"),
        )
        response.raise_for_status()
        return response.json()

    @logfire.instrument("search_transactions", record_return=True)
    async def search_transactions(self, search_query: str):
        response = await self.client.post(
            "/transactions/search/",
            json={"search_query": search_query},
        )
        response.raise_for_status()
        return response.json()

    @logfire.instrument("get_transaction", record_return=True)
    async def get_transaction(self, transaction_id: uuid.UUID):
        response = await self.client.get(f"/transactions/{transaction_id}/")
        response.raise_for_status()
        return response.json()

    @logfire.instrument("update_transaction", record_return=True)
    async def update_transaction(self, transaction_id: uuid.UUID, update_data: dict):
        response = await self.client.patch(
            f"/transactions/{transaction_id}/",
            json=update_data,
        )
        response.raise_for_status()
        return response.json()

    @logfire.instrument("delete_transaction", record_return=True)
    async def delete_transaction(self, transaction_id: uuid.UUID):
        response = await self.client.delete(f"/transactions/{transaction_id}/")
        return response.status_code

    @logfire.instrument("run_sql", record_return=True)
    async def run_sql(self, query: str):
        response = await self.client.post(
            "/sql/",
            json={"query": query},
            headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
        )
        response.raise_for_status()
        return response.json()


db_proxy = DB_Proxy_Hook(db_url=settings.BACKEND_SERVICE_API_URL)
