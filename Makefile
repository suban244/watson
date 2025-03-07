run_local:
	@echo "Running in local mode with docker."
	docker compose up --build --watch

check:
	pre-commit run -a
