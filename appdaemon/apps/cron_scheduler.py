# cron_scheduler.py

import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, time, timedelta
from croniter import croniter
import pytz

class CronScheduler(hass.Hass):
    def __init__(self, app):
        self.app = app
        self.scheduled_jobs = {}
        self.timezone = pytz.timezone(self.app.get_timezone())

    def schedule(self, time_spec, callback, *args, **kwargs):
        job_id = len(self.scheduled_jobs)
        
        job = {
            'callback': callback,
            'args': args,
            'kwargs': kwargs
        }

        if isinstance(time_spec, str) and self._is_cron(time_spec):
            job['type'] = 'cron'
            job['spec'] = time_spec
            self.app.run_every(self._cron_checker, datetime.now(), 60, job_id=job_id)
        else:
            job['type'] = 'time'
            if isinstance(time_spec, str):
                job['spec'] = self.app.parse_time(time_spec)
            elif isinstance(time_spec, time):
                job['spec'] = time_spec
            else:
                raise ValueError("Invalid time specification")
            self.app.run_daily(self._time_callback, job['spec'], job_id=job_id)

        self.scheduled_jobs[job_id] = job
        return job_id

    def _is_cron(self, time_spec):
        try:
            croniter(time_spec)
            return True
        except ValueError:
            return False

    def _cron_checker(self, kwargs):
        job_id = kwargs['job_id']
        job = self.scheduled_jobs[job_id]
        now = datetime.now(self.timezone)
        iter = croniter(job['spec'], now)
        next_time = iter.get_next(datetime)
        
        if (next_time - now).total_seconds() < 60:
            self._run_job(job)

    def _time_callback(self, kwargs):
        job_id = kwargs['job_id']
        job = self.scheduled_jobs[job_id]
        self._run_job(job)

    def _run_job(self, job):
        job['callback'](*job['args'], **job['kwargs'])

    def schedule_timer(self, entity, callback, cutoff_time=None, time_limit=None, enforcement_window=None):
        job_id = len(self.scheduled_jobs)
        now = datetime.now(self.timezone)
        
        job = {
            'type': 'timer',
            'entity': entity,
            'callback': callback,
            'cutoff_time': self.app.parse_time(cutoff_time) if cutoff_time else None,
            'time_limit': time_limit * 60 if time_limit else None,
            'enforcement_window': enforcement_window
        }

        if cutoff_time:
            seconds_until_cutoff = self._get_seconds_until_time(now, job['cutoff_time'])
            if job['time_limit']:
                seconds_until_off = min(seconds_until_cutoff, job['time_limit'])
            else:
                seconds_until_off = seconds_until_cutoff
        elif job['time_limit']:
            seconds_until_off = job['time_limit']
        else:
            raise ValueError("Either cutoff_time or time_limit must be specified")

        self.app.run_in(self._timer_callback, seconds_until_off, job_id=job_id)
        self.scheduled_jobs[job_id] = job
        return job_id
    

    def _timer_callback(self, kwargs):
        job_id = kwargs['job_id']
        job = self.scheduled_jobs[job_id]
        now = datetime.now(self.timezone)
        
        if self.is_in_enforcement_window(job['enforcement_window'], now):
            job['callback'](job['entity'])
        
        del self.scheduled_jobs[job_id]

    def is_in_enforcement_window(self, enforcement_window, current_time=None):
        """
        Check if the current time (or a specified time) is within the given enforcement window.
        
        :param enforcement_window: A tuple of (start_time, end_time) defining the enforcement window
        :param current_time: Optional. A datetime object to check against. If None, uses the current time.
        :return: Boolean indicating whether the time is within the enforcement window
        """
        if not enforcement_window:
            return True

        start_time, end_time = enforcement_window
        if current_time is None:
            current_time = datetime.now(self.timezone)

        return self._is_time_between(current_time.time(), start_time, end_time)

    def _is_time_between(self, check_time, start_time, end_time):
        if start_time <= end_time:
            return start_time <= check_time < end_time
        else:  # crosses midnight
            return check_time >= start_time or check_time < end_time

    def _get_seconds_until_time(self, current_time, target_time):
        target_datetime = datetime.combine(current_time.date(), target_time)
        target_datetime = self.timezone.localize(target_datetime)
    
        if target_datetime <= current_time:
            target_datetime += timedelta(days=1)
    
        time_diff = target_datetime - current_time
        return time_diff.total_seconds()

    def cancel(self, job_id):
        if job_id in self.scheduled_jobs:
            job = self.scheduled_jobs[job_id]
            if job['type'] in ['cron', 'time', 'timer']:
                self.app.cancel_timer(job_id)
            del self.scheduled_jobs[job_id]

    def run_in_enforcement_window(self, callback, enforcement_window, *args, **kwargs):
        now = datetime.now(self.timezone)
        
        if self.is_in_enforcement_window(enforcement_window, now):
            callback(*args, **kwargs)
        else:
            start_time, _ = enforcement_window
            next_start = self._get_next_window_start(now, start_time)
            self.app.run_at(lambda _: self.run_in_enforcement_window(callback, enforcement_window, *args, **kwargs), next_start)

    def _get_next_window_start(self, current_time, start_time):
        next_start = datetime.combine(current_time.date(), start_time)
        next_start = self.timezone.localize(next_start)
        if next_start <= current_time:
            next_start += timedelta(days=1)
        return next_start

# Example usage:
"""
import appdaemon.plugins.hass.hassapi as hass
from cron_scheduler import CronScheduler
from datetime import time

class MyApp(hass.Hass):
    def initialize(self):
        self.scheduler = CronScheduler(self)
        
        # Regular cron schedule (not affected by enforcement window)
        self.scheduler.schedule("0 22 * * *", self.night_routine)
        
        # Timer with enforcement window
        self.scheduler.schedule_timer("fan.living_room", self.turn_off_fan, 
                                      cutoff_time="23:00:00", time_limit=120,
                                      enforcement_window=(time(9,0), time(22,0)))
        
        # Run a function only within an enforcement window
        self.scheduler.run_in_enforcement_window(self.daytime_check, 
                                                 enforcement_window=(time(8,0), time(20,0)))

    def night_routine(self):
        self.log("Running night routine")

    def turn_off_fan(self, entity):
        self.turn_off(entity)
        self.log(f"Turned off {entity}")

    def daytime_check(self):
        self.log("Running daytime check")
"""
