from tornado import gen
from ocperf_utils import *


@gen.coroutine
def update(line, sources):
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
        print "Problem with event name: " + s[2]

    try:
        value = int(s[1])
    except:
        value = 0
        print "problem with value parsing: " + s[1]

    print(timestamp, value, event)
    try:
        print("[UPDATE] Source ID: " + str(id(sources[event])))
        sources[event].stream({'timestamp': [timestamp], event: [value]})
    except KeyError:
        print("[ERROR] update of event %s failed. Could not find " % (event) +
              "suitable ColumnDataSource")


def session_task(session):
    print("Spawning background session task")
    session.loop_until_closed()
    print("closed!")

def blocking_task(tool, doc, workload, events, interval, sources, **kwargs):
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

    ocperf_cmd = build_ocperf_cmd(tool, workload, events_list=events, interval=interval)
    emap = ocp.find_emap()
    perf_cmd = ocp.process_args(emap, ocperf_cmd)
    perf_cmd = ' '.join(perf_cmd)


    if 'env' in kwargs:
        perf_cmd = kwargs['env'] + " " + perf_cmd

    print("FINAL COMMAND: " + perf_cmd)

    pipe = ocp.get_perf_output_pipe(perf_cmd)

    log = ""

    while True:
        out = pipe.stderr.readline()
        log += out

        if out == '':
            break
        else:
            doc.add_next_tick_callback(partial(update, line=out,
                sources=sources))

    # it's safe to store this benchmark
    log_output_path = "logs/" + str(kwargs['uuid']) + ".perflog"
    with open(log_output_path, "w") as f:
        f.write(log)
