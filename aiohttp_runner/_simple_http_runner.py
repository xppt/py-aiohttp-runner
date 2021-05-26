from typing import Optional, AsyncIterator

import aiohttp.web
from async_generator import asynccontextmanager

from aiohttp_runner._utils import parse_bind_addr, KwArgs
from aiohttp_runner._http_runner import HttpAppFactory


@asynccontextmanager
async def simple_http_runner(
        http_app_factory: HttpAppFactory, bind: str,
        server_args: Optional[KwArgs] = None,
) -> AsyncIterator[None]:

    host, port = parse_bind_addr(bind)

    async with http_app_factory() as http_app:
        aiohttp_app_runner = aiohttp.web.AppRunner(http_app, **(server_args or {}))
        await aiohttp_app_runner.setup()

        await aiohttp.web.TCPSite(aiohttp_app_runner, host=host, port=port).start()

        try:
            yield
        finally:
            await aiohttp_app_runner.cleanup()
