import os
import signal
import sys
import threading

from gunicorn.app.wsgiapp import WSGIApplication

from aiohttp_runner._gunicorn_http_runner import _Options, _SubprocessCtx, _PipeMsg
from aiohttp_runner._serialize import deserialize_obj
from aiohttp_runner._utils import init_aiohttp_app


def main(args_list=None) -> None:
    args = args_list or sys.argv[1:]
    assert args[0] == 'run'

    ctx: _SubprocessCtx = deserialize_obj(args[1])

    _run(ctx)


def _run(ctx: _SubprocessCtx) -> None:
    options = ctx.options

    async def app_factory():
        http_app = await init_aiohttp_app(lambda: options.http_app_factory())
        return http_app

    gunicorn_app = GunicornApp(
        app_factory=app_factory,
        options=_make_gunicorn_opts(options),
    )

    stop_event = threading.Event()
    monitor_thread = threading.Thread(
        target=_master_monitor_func,
        args=[options.root_pid, stop_event],
    )
    monitor_thread.start()

    try:
        os.write(ctx.wpipe, _PipeMsg.init)

        gunicorn_app.run()
    finally:
        stop_event.set()
        monitor_thread.join()


def _master_monitor_func(root_pid: int, stop_event: threading.Event) -> None:
    while True:
        if os.getppid() != root_pid:
            signal.pthread_kill(threading.main_thread().ident, signal.SIGTERM)

        if stop_event.wait(timeout=1):
            break


def _make_gunicorn_opts(options: _Options) -> dict:
    use_uvloop = options.use_uvloop
    if use_uvloop is None:
        use_uvloop = _is_uvloop_available()

    if use_uvloop:
        worker_class = 'aiohttp.GunicornUVLoopWebWorker'
    else:
        worker_class = 'aiohttp.GunicornWebWorker'

    workers = options.workers
    if workers is None:
        workers = os.cpu_count() or 1

    result = {
        'bind': f'{options.bind}',
        'accesslog': '-',
        'worker_class': worker_class,
        'loglevel': 'info',
        'workers': workers,
    }

    result.update(options.gunicorn_options or {})

    return result


def _is_uvloop_available():
    try:
        import uvloop
    except ImportError:
        return False
    else:
        return True


class GunicornApp(WSGIApplication):
    def __init__(self, app_factory, options=None):
        self.__app_factory = app_factory
        self.__options = options or {}
        super().__init__()

    def init(self, parser, opts, args):
        pass  # do nothing

    def load_config(self):
        for key, value in self.__options.items():
            self.cfg.set(key, value)

    def load(self):
        return self.__app_factory


if __name__ == '__main__':
    main()
