Install
---
```
pip install aiohttp-runner
```

Example usage
---

```python
import asyncio
import aiohttp.web
from async_generator import asynccontextmanager
from aiohttp_runner import (
    simple_http_runner, gunicorn_http_runner,
    HttpRequest, HttpResponse,
    create_http_app, wait_for_interrupt,
)


@asynccontextmanager
async def app_factory():
    yield create_http_app(routes=[
        ('GET', '/', http_handler),
    ])


async def http_handler(_req: HttpRequest) -> HttpResponse:
    return aiohttp.web.Response(status=204)


async def main() -> None:
    bind = '127.0.0.1:8080'

    runner = gunicorn_http_runner(app_factory, bind, workers=2)
    # OR
    runner = simple_http_runner(app_factory, bind)

    async with runner:
        await wait_for_interrupt()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
```
