def retry(func, e):
    """Retry a function as long as it throws a specific exception.

    This is used to wrap certain socket and queue operations while
    having them throw timeout exceptions. It seems that setting those
    functions to be outright blocking prevents their processes from
    receiving SIGINT and dying, which is inconvenient.

    :param func: function to wrap
    :param e: exception thrown by function
    :return: wrapped function
    """

    def wrapped(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except e:
                pass

    return wrapped