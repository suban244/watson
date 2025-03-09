run_local:
	@echo "Running in local mode with docker."
	docker compose up --build --watch

check:
	pre-commit run -a

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
