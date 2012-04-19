from twisted.protocols.htb import Bucket, HierarchicalBucketFilter
from time import time

"""
Re-implementation of protocols.htb bucket filter because that
implementation is *horrendously* inefficient
"""

class ThrottledBucketFilter(object):

    def __init__(self, rate=0, parentFilter=None):
        self.parentFilter = parentFilter
        self.rate = rate
        self.capacity = rate * 5
        self.content = 0
        self.lastDrip = round(time(), 1)

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

        newDrip = round(time(), 1)

        if newDrip != self.lastDrip:

            if self.parentFilter is not None:
                self.parentFilter.drip()

            deltaT = newDrip - self.lastDrip
            self.content = max(0, self.content - int(deltaT * self.rate))

            self.lastDrip = newDrip
