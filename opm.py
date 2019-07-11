#!/usr/bin/env python3

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ElementTree

from opm.app import App

def main():
    try:
        parser = argparse.ArgumentParser(description="one-pf-manage")
        parser.add_argument("-l", "--log-level", metavar="LVL", choices=["critical", "error", "warning", "info", "debug"], default="warning")
        parser.add_argument("action", choices=["status", "create-missing", "synchronize", "delete-unreferenced", "delete-all", "parse-only"], default="status")
        parser.add_argument("jsonfile", nargs='+')
        args = parser.parse_args()
        app = App(args)
        app.run_all()
        sys.exit(0)

    except KeyboardInterrupt as e:
        logging.warning("Caught SIGINT (Ctrl-C), exiting.")
        sys.exit(1)

    except SystemExit as e:
        message = "Exiting with return code {0}".format(e.code)
        if e.code == 0:
            logging.info(message)
        else:
            logging.warn(message)
            raise e

    except Exception as e:
        logging.critical("{0}: {1}".format(e.__class__.__name__, e))
        # when debugging, we want the stack-trace
        if args.log_level == "debug":
            raise e

if __name__ == '__main__':
    main()
