from fastapi import APIRouter
from .endpoints.transaction import router as transaction_router
from .endpoints.tags import router as tags_router

router = APIRouter()

router.get("/")(lambda: {"Hello": "Welcome To Watson Router"})

router.include_router(transaction_router, prefix="/transaction", tags=["transaction"])
router.include_router(tags_router, prefix="/tags", tags=["tags"])
