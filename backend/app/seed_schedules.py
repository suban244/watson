import asyncio
from taskiq import ScheduledTask
from scheduler import source
from tasks.finances.calculate_expenses_of_last_week import (
    calculate_expenses_of_last_week,
)
from tasks.external.prabin_spotify.send_invoices import send_prabin_spotify_invoices


async def main() -> None:
    await source.startup()

    for existing in await source.get_schedules():
        await source.delete_schedule(existing.schedule_id)

    # Monday 8:00 AM Asia/Kathmandu = Monday 2:15 AM UTC
    await source.add_schedule(
        ScheduledTask(
            task_name=calculate_expenses_of_last_week.task_name,
            labels={},
            args=[],
            kwargs={},
            cron="15 2 * * 1",
        )
    )

    # 11th of each month 9:00 AM Asia/Kathmandu = 3:15 AM UTC
    await source.add_schedule(
        ScheduledTask(
            task_name=send_prabin_spotify_invoices.task_name,
            labels={},
            args=[],
            kwargs={},
            cron="15 3 1 * *",
        )
    )

    await source.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
