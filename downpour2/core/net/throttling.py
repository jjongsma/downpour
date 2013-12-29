from time import time


class ThrottledBucketFilter(object):

    """
    Re-implementation of protocols.htb bucket filter because it is really inefficient
    """

    # noinspection PyPep8Naming
    def __init__(self, rate=0, parentFilter=None):
        self.parentFilter = parentFilter
        self.rate = rate
        self.capacity = rate * 5
        self.content = 0
        self.last_drip = round(time(), 1)

    def add(self, amount):

        self.drip()

        if self.capacity and self.content + amount > self.capacity:
            allowable = self.capacity - self.content
        else:
            allowable = amount

        if self.parentFilter:
            allowable = self.parentFilter.add(allowable)

        self.content += allowable

        return allowable
    
    def drip(self):

        new_drip = round(time(), 1)

        if new_drip != self.last_drip:

            if self.parentFilter is not None:
                self.parentFilter.drip()

            delta_t = new_drip - self.last_drip
            self.content = max(0, self.content - int(delta_t * self.rate))

            self.last_drip = new_drip
