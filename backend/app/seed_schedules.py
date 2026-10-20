import asyncio

from taskiq import ScheduledTask

from scheduler import source
from tasks.external.prabin_spotify.send_invoices import send_prabin_spotify_invoices
from tasks.finances.send_weekly_summary import send_weekly_summary
from tasks.reminders.dispatch_due_reminders import dispatch_due_reminders


async def main() -> None:
    await source.startup()

    for existing in await source.get_schedules():
        await source.delete_schedule(existing.schedule_id)

    # Monday 8:00 AM Asia/Kathmandu = Monday 2:15 AM UTC
    await source.add_schedule(
        ScheduledTask(
            task_name=send_weekly_summary.task_name,
            labels={},
            args=[],
            kwargs={},
            cron="15 2 * * 1",
        )
    )

    # 28th of each month 9:00 AM Asia/Kathmandu = 3:15 AM UTC
    await source.add_schedule(
        ScheduledTask(
            task_name=send_prabin_spotify_invoices.task_name,
            labels={},
            args=[],
            kwargs={},
            cron="15 3 28 * *",
        )
    )

    # Every minute — sweeps for due reminders.
    await source.add_schedule(
        ScheduledTask(
            task_name=dispatch_due_reminders.task_name,
            labels={},
            args=[],
            kwargs={},
            cron="* * * * *",
        )
    )

    await source.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
