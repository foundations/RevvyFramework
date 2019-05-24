import doctest
from application import functions


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(functions))
    return tests
