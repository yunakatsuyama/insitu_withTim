# Created by Yuna Katsuyama and Tim Suhling
# University of Bremen
# yuna@uni-bremen.de
# timsuh@uni-bremen.de
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thread Manager to run both log_insitu.py and write_KML.py at the same time.
It is advisable to instead run both in separate terminals to better manage and restart them in case of errors!
"""

import threading

from log_insitu import runlogging
from write_KML import write_KML

cfg = 'insitu.cfg'


def datasave():
    runlogging()


def plot():
    write_KML(config_filename=cfg)  


if __name__ == "__main__":
    t1 = threading.Thread(target=datasave, daemon=False)
    t2 = threading.Thread(target=plot, daemon=True)

    t1.start()
    t2.start()
