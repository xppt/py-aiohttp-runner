import asyncio
import os
import sys
from contextlib import suppress
from typing import Optional, NoReturn, AsyncIterator, Tuple

from async_exit_stack import AsyncExitStack
from async_generator import asynccontextmanager
from attr import dataclass

from aiohttp_runner._serialize import serialize_obj
from aiohttp_runner._utils import run_task_in_context, OnError, error_handler
from aiohttp_runner._http_runner import (
    HttpAppFactory,
)


@asynccontextmanager
async def gunicorn_http_runner(
        http_app_factory: HttpAppFactory,
        bind: str,
        on_error: OnError = error_handler,
        workers: Optional[int] = None,
        use_uvloop: Optional[bool] = None,
        gunicorn_options: Optional[dict] = None,
):
    options = _Options(
        root_pid=os.getpid(),
        http_app_factory=http_app_factory,
        bind=bind,
        workers=workers,
        use_uvloop=use_uvloop,
        gunicorn_options=gunicorn_options,
    )

    process = await _start_subprocess(options)

    async with run_task_in_context(_manage_subprocess(process, options, on_error), on_error):
        yield


class _InitError(Exception):
    pass


class _GunicornExitError(Exception):
    pass


@asynccontextmanager
async def _init_pipe() -> AsyncIterator[Tuple[int, asyncio.StreamReader]]:
    async with AsyncExitStack() as stack:
        rpipe, wpipe = os.pipe()
        stack.callback(lambda: os.close(wpipe))

        rpipe_file = stack.enter_context(os.fdopen(rpipe, 'rb'))

        stream_reader = asyncio.StreamReader()

        transport, _ = await asyncio.get_event_loop().connect_read_pipe(
            lambda: asyncio.StreamReaderProtocol(stream_reader),
            rpipe_file,
        )
        stack.callback(lambda: transport.close())

        yield wpipe, stream_reader


async def _start_subprocess(options: '_Options') -> asyncio.subprocess.Process:
    async with _init_pipe() as (wpipe, stream_reader):
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'aiohttp_runner._gunicorn_subprocess',
            'run', serialize_obj(_SubprocessCtx(options, wpipe)),
            pass_fds=[wpipe],
        )

        wait_future = asyncio.ensure_future(process.wait())
        read_future = asyncio.ensure_future(stream_reader.read(1))

        done, pending = await asyncio.wait(
            [wait_future, read_future],
            return_when=asyncio.FIRST_COMPLETED,
        )

        if wait_future in done:
            read_future.cancel()
            raise _InitError(process.returncode)

        wait_future.cancel()

        assert read_future in done
        read_msg = await read_future
        assert read_msg == _PipeMsg.init, read_msg

        return process


async def _manage_subprocess(
        process: asyncio.subprocess.Process,
        options: '_Options',
        on_error: OnError,
) -> NoReturn:

    while True:
        try:
            await process.wait()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise

        with suppress(BaseException):
            on_error(_GunicornExitError(process.returncode))

        while True:
            await asyncio.sleep(10)

            try:
                process = await _start_subprocess(options)
            except Exception as e:
                with suppress(BaseException):
                    on_error(e)
            else:
                break


@dataclass
class _Options:
    root_pid: int
    http_app_factory: HttpAppFactory
    bind: str
    workers: Optional[int]
    use_uvloop: Optional[bool]
    gunicorn_options: Optional[dict]


@dataclass
class _SubprocessCtx:
    options: _Options
    wpipe: int


class _PipeMsg:
    init = b'i'
