import asyncio
from taskiq import ScheduledTask
from scheduler import source
from tasks.finances.calculate_expenses_of_last_week import (
    calculate_expenses_of_last_week,
)


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

    await source.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
