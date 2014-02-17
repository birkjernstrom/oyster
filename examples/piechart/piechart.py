#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import pygal
from flask import Flask
app = Flask(__name__)

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '../../src'))

import oyster

@app.route('/')
def index():
    statistics = {}
    with open(os.path.expanduser('~/.bash_history')) as f:
        for line in f.readlines():
            try:
                chain = oyster.parse(line)
                for command in chain:
                    if command.program not in statistics:
                        statistics[command.program] = 0
                    statistics[command.program] += 1
            except:
                pass

    chart = pygal.Pie()
    ordered = sorted(statistics, key=statistics.__getitem__, reverse=True)[:5]
    for name in ordered:
        chart.add(name, statistics[name])
    return chart.render()

if __name__ == '__main__':
    app.run(debug=True)
