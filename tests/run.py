#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import glob
import unittest


test_directory = os.path.dirname(os.path.abspath(__file__))
os.chdir(test_directory)
sys.path.insert(0, os.path.dirname(test_directory))

# Generate list of modules to add to our suite
test_files = glob.glob(os.path.join(test_directory, 'test_*.py'))
test_names = [os.path.basename(name)[:-3] for name in test_files]
test_suite = unittest.defaultTestLoader.loadTestsFromNames(test_names)


def main():
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    exit_code = not (result.errors or result.failures)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
