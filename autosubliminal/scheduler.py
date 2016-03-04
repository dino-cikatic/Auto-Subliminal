import abc
import logging
import time
import threading
import os
import traceback

import autosubliminal

log = logging.getLogger(__name__)


class Scheduler(object):
    """
    :param name: Name of the scheduler
    :type name: str
    :param process: process to schedule 
    :type process: Process
    :param interval: interval in seconds between schedules
    :type interval: int
    :param initial_run: indicates if the process should run initially before starting the thread
    :type initial_run: bool
    :type last_run: int
    :type _delay: int
    :type _force_run: bool
    :type _force_stop: bool
    :type _thread: threading.Thread
    """

    def __init__(self, name, process, interval, initial_run=False):
        self.name = name
        self.process = process
        self.interval = interval
        self.last_run = 0
        self._delay = 0
        self._force_run = False
        self._force_stop = False
        self._thread = threading.Thread(target=self._start_scheduler, name=self.name)
        # Run before starting thread will block caller thread until process is executed the first time
        if initial_run:
            log.debug("Starting initial run before starting thread %s" % self.name)
            self._run_process(time.time())
        # Start thread
        log.info("Starting thread %s" % self.name)
        self._start_thread()

    def _start_scheduler(self):
        while True:
            # Check for stop
            if self._force_stop:
                break
            # Check if we need to run the process
            run_needed = False
            current_time = time.time()
            if self._force_run:
                run_needed = True
                if self._delay:
                    log.info("Delaying thread %s with %s seconds" % (self.name, self._delay))
                    time.sleep(self._delay)
            if current_time - self.last_run > self.interval:
                run_needed = True
            if run_needed:
                self._run_process(current_time)
            time.sleep(1)

    def _run_process(self, current_time):
        try:
            self.process._running = True
            log.debug("Running thread process")
            if self.process.run(self._force_run):
                # Update process properties if process has run
                self.last_run = current_time
                if self._force_run:
                    self._force_run = False
                    self._delay = 0
            else:
                # increase delay with 1 second each time the process cannot yet run
                self._delay += 1
            self.process._running = False
        except:
            print traceback.format_exc()
            os._exit(1)

    def _start_thread(self):
        self._thread.start()
        # Add thread to list of threads
        thread_name = self.name
        while thread_name in autosubliminal.THREADS.keys():
            # Add suffix in case of multiple threads with same name (but this shouldn't occur)
            suffix = 1
            suffix_index = thread_name.rfind('-')
            if suffix_index > 0:
                thread_name_suffix = thread_name[suffix_index + 1:]
                try:
                    suffix = int(thread_name_suffix)
                    suffix += 1
                    thread_name = thread_name[:suffix_index] + "-" + str(suffix)
                except:
                    thread_name = thread_name + "-" + str(suffix)
            else:
                thread_name = thread_name + "-" + str(suffix)
        self.name = thread_name
        autosubliminal.THREADS[thread_name] = self

    def stop(self):
        log.info("Stopping thread %s" % self.name)
        self._force_stop = True
        self._thread.join(10)

    def run(self, delay=0):
        log.info("Running thread %s" % self.name)
        self._force_run = True
        self._delay = delay

    @property
    def running(self):
        return self.process.running


class Process(object):
    """
    :type running: bool
    """

    def __init__(self):
        self.running = False

    @abc.abstractmethod
    def run(self, force_run):
        pass
