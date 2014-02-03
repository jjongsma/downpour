import logging
from twisted.internet import reactor, task, defer

DAILY = 'DAILY'
HOURLY = 'HOURLY'
MINUTELY = 'MINUTELY'


class Janitor(object):

    def __init__(self):

        self.log = logging.getLogger(__name__)

        self.jobs = {
            DAILY: [],
            HOURLY: [],
            MINUTELY: []
        }

        task.LoopingCall(self.run, MINUTELY).start(60, False)
        task.LoopingCall(self.run, HOURLY).start(60 * 60, False)
        task.LoopingCall(self.run, DAILY).start(60 * 60 * 24, False)

    def run(self, period):
        if len(self.jobs[period]) > 0:
            self.log.debug('Running jobs for %s' % period)
            for job in self.jobs[period]:
                job['fn'](*job['args'], **job['kwargs'])

    def add_job(self, period, fn, *args, **kwargs):
        job = {'fn': fn, 'args': args, 'kwargs': kwargs}
        self.jobs[period].append(job)
        return job

    def remove_job(self, period, job):
        self.jobs[period].remove(self.jobs[period].index(job))
