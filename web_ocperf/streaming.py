import logging
import traceback
from tornado import gen
import ocperf as ocp
import ocperf_utils


@gen.coroutine
def update(line, sources):
    fields = line.split(',')

    timestamp = None
    value = 0
    event = None

    logging.info(line)
    try:
        timestamp = float(fields[0])
        event = fields[3]
        value = int(fields[1])
    except:
        logging.warning('Could not parse line:\n%s' % line)
        logging.warning(traceback.format_exc())
        return

    logging.info(timestamp, value, event)
    try:
        logging.info("[UPDATE] Source ID: " + str(id(sources[event])))
        sources[event].stream({'timestamp': [timestamp], event: [value]})
    except KeyError:
        logging.error("update of event %s failed. Could not find " % (event) +
                      "suitable ColumnDataSource")
        return


def session_task(session):
    logging.info("Spawning background session task")
    session.loop_until_closed()
    logging.info("closed!")


def blocking_task(tool, doc, workload, events, interval, sources, **kwargs):
    # dirty fix for py2 incompatibility between @wraps and partial from
    # functools this should be just: from functools import partial
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

    logging.info("inside streaming thread")

    ocperf_cmd = ocperf_utils.build_ocperf_cmd(tool, workload,
                                               events_list=events,
                                               interval=interval)
    emap = ocp.find_emap()
    perf_cmd = ocp.process_args(emap, ocperf_cmd)
    perf_cmd = ' '.join(perf_cmd)

    if 'env' in kwargs:
        perf_cmd = kwargs['env'] + " " + perf_cmd

    logging.info("FINAL COMMAND: " + perf_cmd)

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
    with open(log_output_path, "w") as logfile:
        logfile.write(log)
