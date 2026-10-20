from fastapi import APIRouter

from .endpoints.budget import router as budget_router
from .endpoints.ledger import router as ledger_router
from .endpoints.person import router as person_router
from .endpoints.tag import router as tag_router
from .endpoints.task import router as task_router
from .endpoints.transaction import router as transaction_router

router = APIRouter()


@router.get("/")
def router_root():
    return {"Hello": "Welcome To Watson Router"}


router.include_router(transaction_router, prefix="/transactions", tags=["transactions"])
router.include_router(tag_router, prefix="/tags", tags=["tags"])
router.include_router(budget_router, prefix="/budget", tags=["budget"])
router.include_router(person_router, prefix="/people", tags=["people"])
router.include_router(ledger_router, prefix="/ledger", tags=["ledger"])
router.include_router(task_router, prefix="/tasks", tags=["tasks"])
