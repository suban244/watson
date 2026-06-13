
dev:
	@echo "Launching dev environment..."
	@code $(PWD)/workspace.code-workspace
	@SESSION="watson"; \
	if tmux has-session -t $$SESSION 2>/dev/null; then \
		echo "Session '$$SESSION' already exists, attaching..."; \
		tmux attach-session -t $$SESSION; \
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
	uv run pre-commit run -a

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
