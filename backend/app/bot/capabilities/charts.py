import asyncio
import json
from typing import Any

import vl_convert as vlc
from pydantic_ai import RunContext
from pydantic_ai.capabilities import Capability

from bot.agent.deps import HandleAttachments

charts: Capability[HandleAttachments] = Capability(
    id="charts",
    description="Draw charts of the user's spending and send them to the chat.",
    defer_loading=True,
    instructions="""\
Charting domain:
- A chart reaches the user as an image in the chat. You never see the rendered
  picture, so add one short line about it rather than restating the numbers it
  already shows.
- You can use a variety of data sources for the chart, for example:
    - `query_database` from the `database` capability reads the finance database
- You can then analyze the data and create a chart using plot_chart.
- Amounts are NPR; title the value axis so the unit is visible.

Charting workflows:
1. The user asks to see, plot, chart or graph something:
    - Steps:
        1. Query the rows the chart needs, aggregating in SQL rather than
           pulling every transaction back.
        2. Call `plot_chart` with a Vega-Lite v5 spec whose `data.values` holds
           those rows inline.
        3. Reply with one short line. Do not repeat the table underneath it.

2. The answer is a trend or a breakdown:
    - "How did I do this month", "where is my money going" and month-over-month
      comparisons read better as a chart than as a list. Draw one and keep the
      text brief.

Spec rules:
- Vega-Lite v5. Data goes inline under `data.values` as a list of records; a
  `url` is refused, since the renderer cannot fetch one.
- `bar` for comparing categories (sorted), `line` for change over time, `point`
  for scatter, and a layered `rule` for an average or a budget line.
- It is read on a phone: keep to roughly a dozen bars, aggregating the tail into
  "other" in SQL when there are more, and size the chart around 600px wide.
""",
)


@charts.tool
async def plot_chart(ctx: RunContext[HandleAttachments], spec: dict[str, Any]) -> str:
    """Render a Vega-Lite v5 spec and send the chart to the user.

    Args:
        spec: The full Vega-Lite v5 spec, with the rows inline, e.g.
            {"title": "Expenses by category",
             "width": 600,
             "data": {"values": [{"category": "food", "amount": 10868.6},
                                 {"category": "transport", "amount": 5843.0}]},
             "mark": "bar",
             "encoding": {
                 "y": {"field": "category", "type": "nominal", "sort": "-x"},
                 "x": {"field": "amount", "type": "quantitative",
                       "title": "Spend (NPR)"}}}
    """
    if isinstance(spec.get("data"), dict) and "url" in spec["data"]:
        # vl-convert would happily fetch it; the model has no business naming hosts.
        return "Chart not rendered: put the rows inline in data.values, not a url."

    try:
        # to_thread: rasterising blocks, and this event loop is serving Discord.
        png = await asyncio.to_thread(vlc.vegalite_to_png, json.dumps(spec), scale=2)
    except Exception as exc:  # an invalid spec: hand the message back for a retry
        return f"Chart not rendered: {exc}"

    ctx.deps.attach(f"chart-{len(ctx.deps.attachments) + 1}.png", png)
    return "Chart sent to the user."
