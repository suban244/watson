# Plan: Transaction Groups & AI Agent Tools

## Goal
Allow grouping multiple transactions under an event/purpose (e.g., "Trip to Pokhara" groups food, hotel, travel) and enable queries like "how much did I spend on X?".

---

## Current State

| Layer          | File                                          | What exists                                                       |
| -------------- | --------------------------------------------- | ----------------------------------------------------------------- |
| DB Model       | `backend/app/db/models.py`                    | `Transaction` (amount, title, description, is_expense, date, category) with BM25 + B-tree indexes |
| Pydantic       | `backend/app/schema/transaction.py`           | `TransactionCreate`, `TransactionRead`, `TransactionUpdate`, `TransactionSearch` |
| API            | `backend/app/api/endpoints/transaction.py`    | CRUD + BM25 search                                                |
| Discord Agent  | `discord/bot/agent/base_finance_agent.py`     | `add_expense`, `end_action` tools + raw SQL `query_database_function` |
| DB Proxy       | `discord/bot/services/db_proxy.py`            | HTTP client calling FastAPI: `add_transaction()`, `run_sql()`     |

---

## 1. Database Model Changes (`backend/app/db/models.py`)

### Why Many-to-Many?
A single expense (e.g., a taxi ride) can belong to multiple groups ("Trip to Pokhara" AND "January Travel"). This avoids data duplication and is more flexible than an FK on Transaction.

### New Models

```python
# Association table (no ORM model needed)
transaction_group_association = Table(
    "transaction_group_association",
    Base.metadata,
    Column("transaction_id", UUID, ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", UUID, ForeignKey("transaction_groups.id", ondelete="CASCADE"), primary_key=True),
)

class TransactionGroup(PrimaryUUIDTimestamped):
    __tablename__ = "transaction_groups"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    transactions = relationship("Transaction", secondary=transaction_group_association, back_populates="groups", lazy="selectin")

    __table_args__ = (
        Index("ix_transaction_groups_name_lower", func.lower(name), unique=True),
    )
```

### Update Existing Transaction Model

```python
class Transaction(PrimaryUUIDTimestamped):
    # ...existing columns...

    # New relationship
    groups = relationship("TransactionGroup", secondary=transaction_group_association, back_populates="transactions", lazy="selectin")
```

---

## 2. Pydantic Schemas — new file `backend/app/schema/group.py`

```python
class GroupCreate(BaseModel):
    name: str
    description: str | None = None

class GroupRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None

class GroupWithTransactions(GroupRead):
    transactions: list[TransactionRead] = []
    total_spend: float = 0.0      # computed in endpoint

class GroupMembershipUpdate(BaseModel):
    transaction_ids: list[UUID]
```

Also extend `TransactionRead` (or create `TransactionWithGroups`):
```python
class TransactionWithGroups(TransactionRead):
    groups: list[GroupRead] = []
```

---

## 3. API Endpoints — new file `backend/app/api/endpoints/group.py`

| Method   | Path                            | Description                                     |
| -------- | ------------------------------- | ----------------------------------------------- |
| `POST`   | `/groups/`                      | Create a group                                  |
| `GET`    | `/groups/list/`                 | List all groups (optional `?is_active=true`)     |
| `GET`    | `/groups/{id}/`                 | Get group with transactions + total spend       |
| `PATCH`  | `/groups/{id}/`                 | Update group metadata                           |
| `DELETE` | `/groups/{id}/`                 | Soft-delete (set `is_active=False`)             |
| `POST`   | `/groups/{id}/transactions/`    | Add transactions to group (bulk)                |
| `DELETE` | `/groups/{id}/transactions/`    | Remove transactions from group                  |
| `GET`    | `/groups/{id}/summary/`         | Aggregated spend by category within the group   |

Register in `backend/app/api/api.py`:
```python
from .endpoints.group import router as group_router
router.include_router(group_router, prefix="/groups", tags=["groups"])
```

---

## 4. Discord Agent — New Tools

### 4a. DB Proxy additions (`discord/bot/services/db_proxy.py`)

```python
async def create_group(self, name: str, description: str | None = None) -> dict
async def list_groups(self) -> list[dict]
async def add_transactions_to_group(self, group_id: str, transaction_ids: list[str]) -> dict
async def get_group_summary(self, group_id: str) -> dict
```

### 4b. Agent tools (`discord/bot/agent/base_finance_agent.py`)

| Tool                      | Description                                                                                      |
| ------------------------- | ------------------------------------------------------------------------------------------------ |
| `add_expense` (updated)   | Add optional `group_name: str` param. If provided, look up or create the group, add expense to it. |
| `create_group`            | Create a new transaction group for an event/trip/project.                                        |
| `get_group_summary`       | Return total spend + per-category breakdown for a group.                                         |
| `query_database_function` | (existing) Update DDL constant to include new tables so the LLM knows the schema.                |
| `end_action`              | (existing) No changes.                                                                           |

### 4c. Updated Agent Prompt (instructions)

Add these workflows:

```
2. Group-based Expense Tracking:
    - Trigger: User mentions an event/trip/project name when adding expenses.
    - Example: "Add 500 for lunch for the Pokhara trip"
    - Steps:
        1. Parse expense details AND the group name.
        2. Call `add_expense` with `group_name="Pokhara trip"`.
        3. The tool will auto-create the group if it doesn't exist.

3. Group Summary:
    - Trigger: User asks "how much did I spend on X?"
    - Example: "How much did I spend on the Pokhara trip?"
    - Steps:
        1. Call `query_database_function` to find the group by name.
        2. Call `get_group_summary` with the group ID.
        3. Present the breakdown to the user.

4. Retroactive Grouping:
    - Trigger: User wants to add existing transactions to a group.
    - Example: "Add my last 3 Pathao rides to the Pokhara trip group"
    - Steps:
        1. Query transactions matching the criteria.
        2. Create or look up the group.
        3. Add the transaction IDs to the group.
```

### 4d. Update DDL in `discord/bot/agent/tools/query_database.py`

Add the new table DDLs so the LLM can write SQL against them:
```sql
CREATE TABLE transaction_groups (
    id uuid PRIMARY KEY,
    name varchar(255) NOT NULL,
    description text,
    is_active bool NOT NULL DEFAULT true,
    created_at timestamp DEFAULT now() NOT NULL,
    updated_at timestamp NOT NULL,
    meta jsonb
);

CREATE TABLE transaction_group_association (
    transaction_id uuid REFERENCES transactions(id) ON DELETE CASCADE,
    group_id uuid REFERENCES transaction_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (transaction_id, group_id)
);
```

---

## 5. Migration

```bash
cd backend
alembic revision --autogenerate -m "add_transaction_groups"
alembic upgrade head
```

---

## 6. Complete Agent Tools Inventory

| #  | Tool                        | Status   | Purpose                                                  |
| -- | --------------------------- | -------- | -------------------------------------------------------- |
| 1  | `add_expense`               | Update   | Add expense, optionally to a group                       |
| 2  | `query_database_function`   | Update   | Raw SQL (update DDL to include new tables)               |
| 3  | `end_action`                | Exists   | Signal success/failure with emoji reaction                |
| 4  | `create_group`              | **New**  | Create a transaction group                               |
| 5  | `get_group_summary`         | **New**  | Get spend breakdown for a group                          |
| 6  | `search_transactions`       | **New**  | BM25 search via API (currently API-only, not agent-exposed) |
| 7  | `add_income`                | **New**  | Add income (currently only expenses are tool-supported)   |
| 8  | `get_spending_summary`      | **New**  | Overall spending summary (daily/weekly/monthly)           |
| 9  | `set_budget`                | Future   | Set budget limits (uses commented-out Budget model)       |
| 10 | `check_budget`              | Future   | Check remaining budget vs actual spend                   |

---

## Design Decisions

1. **Many-to-many over FK**: Transactions can belong to multiple groups. More flexible.
2. **Case-insensitive unique group names**: Functional index on `lower(name)` prevents "Pokhara Trip" vs "pokhara trip" duplicates. The agent does a case-insensitive lookup-or-create.
3. **Soft-delete for groups**: `is_active=False` archives finished events. Preserves history for "how much did I spend on events last year?".
4. **`group_name` param on `add_expense`**: Single tool call instead of requiring the LLM to chain `create_group` → `add_expense` → `add_to_group`. Reduces error-prone multi-step flows.
5. **`lazy="selectin"`**: Best practice for async SQLAlchemy — avoids lazy-loading issues in async contexts.

---

## File Change Summary

| File                                              | Action   |
| ------------------------------------------------- | -------- |
| `backend/app/db/models.py`                        | Modify   |
| `backend/app/schema/group.py`                     | Create   |
| `backend/app/schema/transaction.py`               | Modify   |
| `backend/app/api/endpoints/group.py`              | Create   |
| `backend/app/api/api.py`                          | Modify   |
| `backend/app/alembic/versions/xxx_add_groups.py`  | Generate |
| `discord/bot/agent/base_finance_agent.py`         | Modify   |
| `discord/bot/agent/tools/query_database.py`       | Modify   |
| `discord/bot/services/db_proxy.py`                | Modify   |
| `discord/bot/core/schema.py`                      | Modify   |
