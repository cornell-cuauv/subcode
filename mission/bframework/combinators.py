from multiprocessing import Process

from mission.bframework.helpers import call_if_function
from mission.bframework.task import Task
from mission.bframework.primitive import NoOp, Succeed

class Sequential(Task):
    def run(self, *tasks):
        for task in tasks:
            success = task()
            if not success:
                return False
        return True

class Concurrent(Task):
    def run(self, *tasks):
        processes = []
        successes = []
        for task in tasks:
            process = Process(target=lambda: successes.append(task()))
            process.start()
            processes.append(process)
        while True:
            if len(processes) == len(tasks):
                return successes.all(True)
            if False in successes:
                for process in processes:
                    process.terminate()
                return False

class MasterConcurrent(Task):
    def run(self, master_task, *tasks):
        master_success = []
        master_process = Process(target=lambda: success.append(master_task()))
        master_process.start()
        other_processes = []
        other_successes = []
        for task in tasks:
            process = Process(target=lambda: other_success.append(task()))
            process.start()
            other_processes.append(process)
        while True:
            if len(master_success) == 1:
                for process in other_processes:
                    process.terminate()
                return success[0]
            if False in other_successes:
                master_process.terminate()
                for process in other_processes:
                    process.terminate()
                return False

class Retry(Task):
    def run(self, task, attempts):
        for _ in range(attempts):
            if task():
                return True
        return False

class Conditional(Task):
    def run(self, main_task, on_success=None, on_fail=None):
        if main_task():
            if on_success:
                return on_success()
            return True
        if on_fail:
            return on_fail()
        return True

class While(Task):
    def run(self, task, condition):
        while call_if_function(condition):
            if not task():
                return False
        return True

class Defer(Task):
    def run(self, main_task, deferred):
        main_success = main_task()
        if deferred():
            return main_success
        return False

class Either(Task):
    def run(self, *tasks):
        processes = []
        successes = []
        for task in tasks:
            process = Process(target=lambda: sucesses.append(task()))
            process.start()
            processes.append(process)
        while len(successes) == 0:
            pass
        for process in processes:
            process.terminate()
        return successes[0]

class Except(Task):
    def run(self, main_task, except_task, *exceptions):
        try:
            return main_task()
        except exceptions:
            return except_task()

class Disjunction(Task):
    def run(self, tasks):
        for task in tasks:
            if task():
                return True
        return False
