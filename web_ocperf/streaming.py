from tornado import gen
from ocperf_utils import *

@gen.coroutine
def update(line, source):
    s = line.split(',')

    timestamp = None
    value = None
    event = None

    print("[UPDATE] Source ID: " + str(id(source)))

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

    print("doing update")
    print(timestamp, value, event)
    source.stream(dict(x=[timestamp], y=[value]))

def session_task(session):
    print("Spawning background session task")
    session.loop_until_closed()
    print("closed!")

def blocking_task(doc, workload, events, interval, source):
    # dirty fix for py2 incompatibility between @wraps and partial from functools
    # this should be just: from functools import partial
    # more info: http://bit.ly/29xoM9p
    def partial(func, *args, **keywords):
        def newfunc(*fargs, **fkeywords):
            newkeywords = keywords.copy()
            newkeywords.update(fkeywords)
            return func(*(args + fargs), **newkeywords)
        newfunc.func = func
        newfunc.args = args
        newfunc.keywords = keywords
        return newfunc

    print("inside streaming thread")

    ocperf_cmd = build_ocperf_cmd(workload, events_list=events, interval=interval)
    emap = ocp.find_emap()
    perf_cmd = ocp.process_args(emap, ocperf_cmd)
    pipe = ocp.get_perf_output_pipe(perf_cmd)

    while True:
        # print("in tha loop")
        out = pipe.stderr.readline()

        if out == '':
            break
        else:
            print(out)
            doc.add_next_tick_callback(partial(update, line=out, source=source))

    print("long running thread is dead")
