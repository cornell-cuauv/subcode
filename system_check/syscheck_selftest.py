import os

from test import vehicle, level, Test, ODYSSEUS, AJAX, WARN, ERR

# Syscheck self-tests, so meta
@vehicle(AJAX)
class IsAjax(Test):
    def is_ajax():
        return "ajax" == os.getenv("CUAUV_VEHICLE")

    class IsAjax(Test):
        def is_ajax():
            return "ajax" == os.getenv("CUAUV_VEHICLE")

    @vehicle(ODYSSEUS)
    class IsOdysseus(Test):
        def is_odysseus():
            return "odysseus" == os.getenv("CUAUV_VEHICLE")

@vehicle(ODYSSEUS)
class IsOdysseus(Test):
    def is_odysseus():
        return "odysseus" == os.getenv("CUAUV_VEHICLE")

    class IsOdysseus(Test):
        def is_odysseus():
            return "odysseus" == os.getenv("CUAUV_VEHICLE")

    @vehicle(AJAX)
    class IsAjax(Test):
        def is_ajax():
            return "ajax" == os.getenv("CUAUV_VEHICLE")
