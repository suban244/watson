# Watson
> A Simple AI Assistant

# Running the thing
The point is to be over-engineered
- A Backend Written in python

# DB Migrations
The `env.py` for alembic assumes you will be running alembic outside the container.
No particular reason other than, i could not figure out a proper way of syncing stuff inside and outside the contaienr without volumes and now I am too lazy.
*Do a `source .env` to load the envs when working with alembic.*

```
uv run --env-file ../../.env  alembic revision --autogenerate -m "Create Transaction Tables"
- notifications of spendings - easiest
- Todolist + remainder hybrid
- budgets
- RAG Over personal notes of obsidian
- Handle recepts
```
