from typing import Callable, AsyncContextManager, Awaitable, Tuple, Iterable, NamedTuple

import aiohttp.web

HttpMethod = str
HttpLocationTemplate = str
HttpApp = aiohttp.web.Application
HttpRequest = aiohttp.web.Request
HttpResponse = aiohttp.web.StreamResponse
HttpHandler = Callable[[HttpRequest], Awaitable[HttpResponse]]

HttpRoute = Tuple[
    HttpMethod,
    HttpLocationTemplate,
    HttpHandler,
]

HttpAppFactory = Callable[[], AsyncContextManager[HttpApp]]


def create_http_app(routes: Iterable[HttpRoute], **options) -> HttpApp:
    aiohttp_app = aiohttp.web.Application(**options)

    for method, path, handler in routes:
        aiohttp_app.router.add_route(method, path, handler)

    return aiohttp_app
