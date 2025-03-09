from fastapi import APIRouter
from .endpoints.transaction import router as transaction_router

router = APIRouter()

router.get("/")(lambda: {"Hello": "Welcome To Watson Router"})

router.include_router(transaction_router, prefix="/transaction", tags=["transaction"])
