Watson
---

A over-engineered financial tracking app, with AI.
To be deployed on a raspberry pi. (my sd card got lost.)

# Features
- add expenses, get weekly summaries and run basic query over financial data from discord chat
  - you can add basic bills too (photos)

# Technical stuff
- Full observability with logfire
- auto apply migrations with alembic
- Features
  - Adding Financial Transactions:
    - `discord` the frontend to receive text / image (and soon voice) input
    - We run `pydantic_ai` to process input
    - tools integrated with `backend` to save transactions to `postgres`
  - weekly summary:
    - `celery+beat` for scheduling and summary generation
    - `redis` for pub/sub backend
    - `discord` is the consumer, which sends messages to discord

- budgets - grouped transactions
# Configuration
- make a copy of `.env.example` as `.env`  and fill in the necessary keys
- has multiple  individual services, mainly
  - `backend` a fastapi web server.
  - `discord` a 'front-end`
- use `make run_local` for local dev, and `make prod` for prod docker compose file.
