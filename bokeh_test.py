#!/usr/bin/python2

from functools import partial

# dirty fix for py2 incompatibility between @wraps and partial from functools
# this should be just: from functools import partial
# more info: http://bit.ly/29xoM9p
# def partial(func, *args, **keywords):
#     def newfunc(*fargs, **fkeywords):
#         newkeywords = keywords.copy()
#         newkeywords.update(fkeywords)
#         return func(*(args + fargs), **newkeywords)
#     newfunc.func = func
#     newfunc.args = args
#     newfunc.keywords = keywords
#     return newfunc

from random import random
from threading import Thread
import time
import sys

from bokeh.client import push_session
from bokeh.models import ColumnDataSource
from bokeh.plotting import curdoc, figure, show

from tornado import gen

import ocperf as ocp
import web_ocperf as wocp

source = ColumnDataSource(data=dict(x=[0], y=[0]))

doc = curdoc()
session = push_session(doc)


# @gen.coroutine
# def update(x, y):
#     source.stream(dict(x=[x], y=[y]))

@gen.coroutine
def update2(line):
    s = line.split(',')

    timestamp = None
    value = None
    event = None

    try:
        timestamp = float(s[0])
    except:
        print "Problem with timestamp: " + s[0]

    try:
        event = s[3]
    except:
        print "Problem with event name: " + s[3]

    try:
        value = int(s[1])
    except:
        value = 0
        print "problem with value parsing: " + s[1]

    # print(timestamp, value, event)
    source.stream(dict(x=[timestamp], y=[value]))

def blocking_task():
    # TODO: 1
    # run perf task with callback
    # get pipe object

    # workload = "sleep 5".split(' ')
    # workload = "/home/nhardi/code/cl_forward/bin/x86_64/Release/clpixel -serial -bin -file /home/nhardi/code/cl_forward/bin/x86_64/Release/test.small.arg".split(' ')
    workload = "/home/nhardi/code/cl_forward/bin/x86_64/Release/clpixel -serial -bin -file /home/nhardi/code/cl_forward/bin/x86_64/Release/test.medium.arg".split(' ')
    # workload = "/usr/bin/yes"
    events = ['instructions']
    cmd = wocp.ocperf_utils.build_ocperf_cmd(workload, events, interval=100)

    pipe = ocp.get_perf_output_pipe(cmd)

    while True:
        # TODO: 2:
        # read line
        # schedule update
        # read again and repeat until the end of stream
        out = pipe.stderr.readline()

        if out == '':
            break
        else:
            doc.add_next_tick_callback(partial(update2, line=out))

        # TODO: 3
        # should I recognize bulk reads by myself or read known number of lines?
        # use Queue module?

    # this was original code
    # while True:
    #     time.sleep(0.1)
    #     x, y = random(), random()

    #     doc.add_next_tick_callback(partial(update, x=x, y=y))

# p = figure(x_range=[0, 1], y_range=[0, 1])
p = figure(sizing_mode='stretch_both')
l = p.line(x='x', y='y', source=source)

doc.add_root(p)

thread = Thread(target=blocking_task)
thread.start()

session.show(p)
session.loop_until_closed()
