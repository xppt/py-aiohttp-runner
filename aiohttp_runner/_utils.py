import asyncio
import os
import signal
import sys
import traceback
from contextlib import suppress
from typing import Callable, AsyncContextManager, Tuple, Dict, Any, AsyncIterator

from async_exit_stack import AsyncExitStack
from async_generator import asynccontextmanager

from aiohttp_runner._http_runner import HttpApp

HttpAppContext = Callable[[], AsyncContextManager[HttpApp]]
KwArgs = Dict[str, Any]
OnError = Callable[[BaseException], None]


async def wait_for_interrupt(*, nt_check_secs: float = 0.5) -> None:
    if os.name == 'posix':
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        sig_nums = [signal.SIGINT, signal.SIGTERM]
        for sig_num in sig_nums:
            loop.add_signal_handler(sig_num, lambda: future.set_result(None))

        await future

        for sig_num in sig_nums:
            loop.remove_signal_handler(sig_num)

    elif os.name == 'nt':
        shutdown = False

        def signal_handler(_signum, _frame) -> None:
            # we can't use loop here
            nonlocal shutdown
            shutdown = True

        prev_signal = signal.signal(signal.SIGINT, signal_handler)

        while not shutdown:
            await asyncio.sleep(nt_check_secs)

        signal.signal(signal.SIGINT, prev_signal)

    else:
        raise NotImplementedError


async def init_aiohttp_app(http_app_context: HttpAppContext) -> HttpApp:
    async def stop(_app):
        await exit_stack.aclose()

    async with AsyncExitStack() as stack:
        http_app = await stack.enter_async_context(http_app_context())
        http_app.on_cleanup.append(stop)
        exit_stack = stack.pop_all()

    return http_app


def parse_bind_addr(bind: str) -> Tuple[str, int]:
    if ':' not in bind:
        bind = f'0.0.0.0:{bind}'

    host, port = bind.split(':', 1)

    try:
        port_int = int(port)
    except ValueError:
        raise ValueError(f'bad port number {port!r}') from None

    return host, port_int


def error_handler(exc: BaseException) -> None:
    traceback.print_tb(exc.__traceback__, file=sys.stderr)


@asynccontextmanager
async def run_task_in_context(coro, on_error: OnError) -> AsyncIterator[None]:
    def _callback(f: asyncio.Future) -> None:
        if not f.cancelled():
            e = f.exception()
            if e is not None:
                on_error(e)

    future = asyncio.ensure_future(coro)
    future.add_done_callback(_callback)

    try:
        yield
    finally:
        future.cancel()
        with suppress(asyncio.CancelledError):
            await future
