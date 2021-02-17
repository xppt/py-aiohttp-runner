import os
from typing import Optional

from aiohttp_runner._utils import init_aiohttp_app
from aiohttp_runner._http_runner import (
    HttpRunner, HttpWorkerContext, HttpAppFactory,
)

_worker_id_var = 'GUNICORN_RUNNER_WORKER_ID'


class GunicornHttpRunner(HttpRunner):
    def __init__(
            self,
            bind: str,
            workers: Optional[int] = None,
            use_uvloop: Optional[bool] = None,
            gunicorn_options: Optional[dict] = None,
    ):
        self._bind = bind
        self._workers = workers
        self._use_uvloop = use_uvloop
        self._gunicorn_options = gunicorn_options or {}

    def run(self, http_app_factory: HttpAppFactory):
        from aiohttp_runner._gunicorn_app import GunicornApp

        if os.getenv(_worker_id_var):
            raise RuntimeError(f'{_worker_id_var} shouldn\'t be set')

        async def app_factory():
            worker_id = os.getenv(_worker_id_var, 0)
            if worker_id is None:
                raise RuntimeError('unable to determine worker id')

            worker_context = HttpWorkerContext(worker_id=int(worker_id))
            return await init_aiohttp_app(lambda: http_app_factory(worker_context))

        gunicorn_app = GunicornApp(
            app_factory=app_factory,
            options=self._make_options(),
        )
        gunicorn_app.run()

    def _make_options(self):
        use_uvloop = self._use_uvloop
        if use_uvloop is None:
            use_uvloop = _is_uvloop_available()

        if use_uvloop:
            worker_class = 'aiohttp.GunicornUVLoopWebWorker'
        else:
            worker_class = 'aiohttp.GunicornWebWorker'

        workers = self._workers
        if workers is None:
            workers = os.cpu_count() or 1

        options = {
            'bind': f'{self._bind}',
            'accesslog': '-',
            'worker_class': worker_class,
            'loglevel': 'info',
            'workers': workers,
        }

        options.update(self._gunicorn_options)
        options.update(_hooks)

        return options


def _is_uvloop_available():
    try:
        import uvloop
    except ImportError:
        return False
    else:
        return True


def _nworkers_changed_hook(server, new_value, old_value):
    """
    Gets called on startup too.
    Set the current number of workers.  Required if we raise the worker count
    temporarily using TTIN because server.cfg.workers won't be updated and if
    one of those workers dies, we wouldn't know the ids go that far.
    """
    server._worker_id_current_workers = new_value


# noinspection PyProtectedMember
def _next_worker_id(server):
    """
    Look for a free worker_id to use.
    """
    in_use = set(w._worker_id for w in tuple(server.WORKERS.values()) if w.alive)
    free = set(range(1, server._worker_id_current_workers + 1)) - in_use

    return free.pop()


def _on_reload_hook(server):
    """
    Disable reload to ensure allow one worker with given id.
    """
    raise RuntimeError('reload is not supported')


def _pre_fork_hook(server, worker):
    """
    Attach the next free worker_id before forking off.
    """
    worker._worker_id = _next_worker_id(server)


def _post_fork_hook(server, worker):
    """
    Put the worker_id into an env variable for further use within the app.
    """
    # noinspection PyProtectedMember
    os.environ[_worker_id_var] = str(worker._worker_id)


_hooks = {
    'nworkers_changed': _nworkers_changed_hook,
    'pre_fork': _pre_fork_hook,
    'post_fork': _post_fork_hook,
}
