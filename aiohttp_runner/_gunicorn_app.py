from gunicorn.app.wsgiapp import WSGIApplication


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
