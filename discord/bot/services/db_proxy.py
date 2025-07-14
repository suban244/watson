import httpx
from core.schema import Transaction
import logfire


class DB_Proxy_Hook:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.client = httpx.AsyncClient(base_url=db_url)

    @logfire.instrument("add_transaction", record_return=True)
    async def add_transaction(self, transaction_data: Transaction):
        response = await self.client.post(
            "/transactions/", json=transaction_data.model_dump(mode="json")
        )
        return response.json()


db_proxy = DB_Proxy_Hook(db_url="http://backend:8000/api/v1/")
