
run_local:
	@echo "Running in local mode with docker."
	docker compose -f local.yml up --build --watch


# DOES NOT WORK
.ONESHELL:
venv: ${PWD}/discord/.venv/bin/activate
	@echo "Activating Virtual Environment"
	source $(PWD)/discord/.venv/bin/activate && python --version
	python --version
	@echo done

prod:
	@echo "Running in local mode with docker."
	docker compose -f prod.yml up --build


uv_lock:
	@echo "Locking dependencies."
	uv --directory ./backend lock

uv_sync:
	@echo "Syncing dependencies."
	uv --directory ./backend sync

check:
	source ./backend/.venv/bin/activate && pre-commit run -a

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
