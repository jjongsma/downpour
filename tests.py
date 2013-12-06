#!/usr/bin/env python
import unittest

modules_to_test = (
    'downpour2.core.tests',
    # 'downpour.core.tests.store',
    # 'downpour.core.tests.event',
    # 'downpour.core.tests.rest',
    # 'downpour.core.tests.app',
    # 'downpour.core.tests.flow',
    # 'downpour.core.tests.users',
    # 'downpour.core.tests.plugin',
    # 'downpour.core.tests.http',
    # 'downpour.transfers.tests',
    # 'downpour.library.tests',
    # 'downpour.feeds.tests',
    # 'downpour.search.tests',
    # 'downpour.clients.libtorrent.tests',
    # 'downpour.clients.http.tests',
    # 'downpour.agents.local.tests',
    # 'downpour.agents.rtorrent.tests'
)

def suite():
    alltests = unittest.TestSuite()
    for module in map(__import__, modules_to_test):
        alltests.addTest(unittest.findTestCases(module))
    return alltests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
