import asyncio
import os

import aiohttp.web

from aiohttp_runner._utils import init_aiohttp_app
from aiohttp_runner._http_runner import (
    HttpRunner, HttpAppFactory, HttpWorkerContext,
)


class SimpleHttpRunner(HttpRunner):
    def __init__(self, bind: str):
        self._bind = bind

    def run(self, http_app_factory: HttpAppFactory):
        worker_context = HttpWorkerContext(worker_id=0)
        coro = init_aiohttp_app(lambda: http_app_factory(worker_context))
        http_app = asyncio.get_event_loop().run_until_complete(coro)

        host, port = self._bind.split(':', 1)

        if os.name == 'nt':
            # workaround for graceful stop on Windows
            _wakeup_nt()

        aiohttp.web.run_app(http_app, host=host, port=int(port))


def _wakeup_nt():
    asyncio.get_event_loop().call_later(1, _wakeup_nt)
