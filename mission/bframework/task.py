class Task:
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def __call__(self):
        self.run(*self._args, **self._kwargs)
