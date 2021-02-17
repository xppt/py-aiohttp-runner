from typing import Callable, AsyncContextManager

from async_exit_stack import AsyncExitStack

from aiohttp_runner._http_runner import HttpApp

HttpAppContext = Callable[[], AsyncContextManager[HttpApp]]


async def init_aiohttp_app(http_app_context: HttpAppContext) -> HttpApp:
    async def stop(_app):
        await exit_stack.aclose()

    async with AsyncExitStack() as stack:
        http_app = await stack.enter_async_context(http_app_context())
        http_app.on_cleanup.append(stop)
        exit_stack = stack.pop_all()

    return http_app
