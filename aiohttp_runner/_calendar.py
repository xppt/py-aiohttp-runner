import asyncio
import time
from contextlib import suppress
from datetime import timedelta
from math import ceil
from typing import NamedTuple, Callable, Awaitable, AsyncIterator

from async_generator import asynccontextmanager

from aiohttp_runner._utils import OnError, run_task_in_context, error_handler


class ScheduledTime(NamedTuple):
    loop_time: float
    calendar_time: int


@asynccontextmanager
async def calendar_scheduler(
        period: timedelta,
        handler: Callable[[ScheduledTime], Awaitable[None]],
        on_error: OnError = error_handler,
) -> AsyncIterator[None]:

    period_secs = int(period.total_seconds())
    if period_secs <= 0 or period.microseconds != 0:
        raise ValueError('unsupported period value', period)

    loop = asyncio.get_event_loop()

    async def task():
        last_scheduled_time = None

        while True:
            cur_time = time.time()
            scheduled_time = ceil(cur_time / period_secs) * period_secs
            if scheduled_time == last_scheduled_time:
                scheduled_time += period_secs

            delay = scheduled_time - cur_time
            last_scheduled_time = scheduled_time

            scheduled_loop_time = loop.time() + delay
            await asyncio.sleep(delay)

            # noinspection PyBroadException
            try:
                await handler(ScheduledTime(scheduled_loop_time, scheduled_time))
            except BaseException as e:
                with suppress(BaseException):
                    on_error(e)

    async with run_task_in_context(task(), on_error):
        yield
