import logfire

from config import settings


def setup_logfire(service_name: str) -> None:
    """Configure logfire and the instrumentation shared by every Watson process."""
    logfire.configure(
        service_name=service_name,
        token=settings.LOGFIRE_TOKEN,
        send_to_logfire="if-token-present",
        environment=settings.APP_ENV,
        scrubbing=False,
        distributed_tracing=True,
    )

    # Imported here so the beat process, which loads taskiq_app but never
    # touches the DB, doesn't pull in SQLAlchemy.
    from db.session import engine

    logfire.instrument_sqlalchemy(engine=engine)
