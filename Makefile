.DEFAULT_GOAL := help

.PHONY: help dev run_local prod stop_prod uv_lock uv_sync check \
	makemigrations migrate downgrade alembic_current

help:
	@echo "usage: make <target>"
	@echo ""
	@echo "  dev              launch vscode + the watson tmux session"
	@echo "  run_local        docker compose up (local.yml, --watch)"
	@echo "  prod             docker compose up (prod.yml)"
	@echo "  stop_prod        docker compose down (prod.yml)"
	@echo "  uv_lock          lock backend dependencies"
	@echo "  uv_sync          sync backend dependencies"
	@echo "  check            run pre-commit on all files"
	@echo "  makemigrations   alembic autogenerate  (message=<message>)"
	@echo "  migrate          alembic upgrade head"
	@echo "  downgrade        alembic downgrade -1"
	@echo "  alembic_current  show current db revision"

	@[ -n "$(MAKECMDGOALS)" ] || exit 2

dev:
	@echo "Launching dev environment..."
	@code .
	@SESSION="watson"; \
	if tmux has-session -t $$SESSION 2>/dev/null; then \
		echo "Session '$$SESSION' already exists, attaching..."; \
	else \
		tmux new-session -d -s $$SESSION -x 220 -y 50; \
		tmux rename-window -t $$SESSION:1 "lazygit"; \
		tmux send-keys -t $$SESSION:1 "cd $(PWD) && lazygit" Enter; \
		tmux new-window -t $$SESSION; \
		tmux new-window -t $$SESSION -n "backend"; \
		tmux send-keys -t $$SESSION:3 "cd $(PWD)/backend" Enter; \
		tmux new-window -t $$SESSION -n "frontend"; \
		tmux send-keys -t $$SESSION:4 "cd $(PWD)/frontend" Enter; \
		tmux new-window -t $$SESSION; \
		tmux select-window -t $$SESSION:1; \
	fi; \
	if [ -n "$$TMUX" ]; then \
		tmux switch-client -t $$SESSION; \
	else \
		tmux attach-session -t $$SESSION; \
	fi

run_local:
	@echo "Running in local mode with docker."
	docker compose -f local.yml up --build --watch

prod:
	@echo "Running in production mode with docker."
	docker compose -f prod.yml up --build

stop_prod:
	@echo "Stopping production mode."
	docker compose -f prod.yml down

uv_lock:
	@echo "Locking dependencies."
	uv --directory ./backend lock

uv_sync:
	@echo "Syncing dependencies."
	uv --directory ./backend sync

check:
	uv run --directory ./backend pre-commit run -a

makemigrations:
	@echo "Generating migrations."
	@if [ -z "$(message)" ]; then \
		echo "No message provided, Use: make makemigrations message=<message>"; \
	else \
		echo "Using custom message: $(message)"; \
		uv run --directory ./backend/app --env-file ../../.env alembic revision --autogenerate -m "$(message)"; \
	fi

migrate:
	@echo "Migrating database."
	uv run --directory ./backend/app --env-file ../../.env alembic upgrade head


downgrade:
	@echo "Downgrading database."
	uv run --directory ./backend/app --env-file ../../.env alembic downgrade -1

alembic_current:
	@echo "Current database revision."
	uv run --directory ./backend/app --env-file ../../.env alembic current
