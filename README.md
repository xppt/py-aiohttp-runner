Usage
=====

```python
import aiohttp.web
from async_generator import asynccontextmanager
from aiohttp_runner import (
    SimpleHttpRunner, GunicornHttpRunner, HttpWorkerContext, HttpRequest, HttpResponse,
    create_http_app,
)


@asynccontextmanager
async def app_factory(_context: HttpWorkerContext):
    yield create_http_app(routes=[
        ('GET', '/', http_handler),
    ])


async def http_handler(_req: HttpRequest) -> HttpResponse:
    return aiohttp.web.Response(status=204)


SimpleHttpRunner(bind='0.0.0.0:8080').run(app_factory)
# OR
GunicornHttpRunner(bind='0.0.0.0:8080', workers=3).run(app_factory)
```
