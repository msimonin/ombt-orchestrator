#!/usr/bin/env python

import tasks

import logging
import sys

logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        sys.exit(0)

    for cmd in sys.argv[1:]:
        getattr(tasks, cmd)()

