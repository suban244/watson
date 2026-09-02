# Watson

> A personal finance assistant you talk to on Discord.

Message a Discord channel — text, or a photo of a receipt — and Watson files the
transaction, tags it, answers questions about your spending, draws charts, and nags you
about reminders. A SvelteKit dashboard sits on the same database for the things a chat
window is bad at.

Runs on a Raspberry Pi in my room, behind a Cloudflare tunnel.
The point is to be over-engineered.

## How it works

A FastAPI app with the Discord bot running inside it, a taskiq worker and scheduler for
background jobs, Postgres (ParadeDB, for full-text search, pgvector, for vector search) and Redis. The agent is
`pydantic-ai` on an OpenRouter model, built from the capability modules in
`backend/app/bot/capabilities/` — transactions, tags, reminders, charts, and read-only
SQL over its own database. Receipt photos go to Mistral for extraction first.

CodeMode for some lite data analysis and charting, and read only sql queries over the database.

## Running it

```sh
cp .env.example .env      # then fill in the keys
make run_local
```

Backend on `http://localhost:8000` (docs at `/docs`). Code changes sync into the
container and restart it.

You need `DISCORD_TOKEN` and `SOURCE_CHANNEL_ID` (the one channel the bot listens to),
`OPENROUTER_API_KEY` for the agent, and `MISTRAL_API_KEY` for receipt images.
`LOGFIRE_TOKEN` is optional.

For the dashboard on its own: `cd frontend && npm install && npm run dev`.
`make check` runs the linters. `make prod` is the production stack.

## Migrations

Alembic runs **outside** the container — there was never a clean way to keep revisions in
sync across the volume boundary, and I got lazy. The make targets handle the env loading:

```sh
make makemigrations message="Create transaction tables"
make migrate
```

Containers run `alembic upgrade head` on startup, so deploys migrate themselves.
Scheduled jobs live in Redis rather than in code — re-run `backend/app/seed_schedules.py`
after changing them.

## Deploying

Pushing to `main` builds and restarts the stack on the Pi via a self-hosted runner. The Pi
publishes no ports; `cloudflared` holds an outbound-only tunnel and Cloudflare Access gates
the hostname. See [deployment/cloudflare-tunnel-setup.md](deployment/cloudflare-tunnel-setup.md)
and [docs/BACKUP.md](docs/BACKUP.md).

## Roadmap

- [x] Notifications of spending
- [x] Reminders
- [x] Budgets
- [ ] RAG over personal Obsidian notes
- [ ] Backup and restore DB
- [ ] Voice input
- [ ] Integrate with self hosted Fizzy (https://fizzy.do)
