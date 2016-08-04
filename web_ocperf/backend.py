#!/usr/bin/python2
# standard python imports
from os import path
import sys
import json
from threading import Thread
from functools import partial

import ocperf as ocp

# utils for web_ocperf
from plot_utils import plot_parsed_ocperf_output, store_plot_at
from ocperf_utils import *

# flask related imports
from flask import (
    Flask,
    Response,
    request,
    send_from_directory,
    render_template,
)

# bokeh related imports
from bokeh.client import push_session
from bokeh.models import ColumnDataSource
from bokeh.plotting import curdoc, figure, show
from bokeh.embed import autoload_server, components
from tornado import gen

def run_ocperf(workload, events, interval):
    """
    workload - command to profile represented as list of strings like .split(' ')
    events - list of symbolic names of events to count
    interval - sampling interval
    """
    ocperf_cmd = build_ocperf_cmd(workload, events_list=events, interval=interval)
    emap = ocp.find_emap()
    emap = get_combined_emap()
    perf_cmd = ocp.process_args(emap, ocperf_cmd)
    raw_perf_output = ocp.get_perf_output(perf_cmd)
    parsed_perf_output = parse_output(raw_perf_output)
    return parsed_perf_output

app = Flask("ocperf server", static_url_path='')

@app.route("/api/v1/emap", methods=['GET'])
def rest_emap_endpoint():
    combined_emap = get_combined_emap()
    print(combined_emap)
    json_emap = serialize_emap(combined_emap)

    return Response(json_emap, mimetype="application/json")

@gen.coroutine
def update(line):
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

    print("doing update")
    print(timestamp, value, event)
    source.stream(dict(x=[timestamp], y=[value]))

# TODO: this can't stay like this
source = ColumnDataSource(data=dict(x=[0], y=[0]))

def blocking_task(doc, workload, events, interval):
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

    print(id(doc))

    while True:
        # print("in tha loop")
        out = pipe.stderr.readline()

        if out == '':
            break
        else:
            # print(out)
            doc.add_next_tick_callback(partial(update, line=out))

    print("long running thread is dead")


doc = None

@app.route("/api/v1/run", methods=['POST'])
def rest_run_endpoint():

    d = request.get_json()

    workload = d['workload'].split(' ')
    events = d['events']
    interval = d['interval']
    streaming = d['streaming']

    if not streaming:
        parsed_output = run_ocperf(workload, events, interval)
        p = plot_parsed_ocperf_output(parsed_output)
        store_plot_at(p, "tmp")
        return Response(json.dumps(parsed_output, indent=2), mimetype="application/json")
    elif streaming:
        print("doing streaming branch")
        source = ColumnDataSource(data=dict(x=[0], y=[0]))

        doc = curdoc()
        print(id(doc))
        session = push_session(doc)

        p = figure(toolbar_location=None)
        l = p.line(x='x', y='y', source=source)

        kwargs = {
            "doc": doc,
            "workload": workload,
            "events": events,
            "interval": interval,
        }

        doc.add_root(p)

        thread = Thread(target=blocking_task, kwargs=kwargs)
        thread.start()

        script = autoload_server(p, session_id=session.id)

        # store_plot_at(doc, "tmp")
        with open("./tmp/autoload_script.js", "w") as f:
            f.write(script)

        return Response("ok")

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")

@app.route("/js/<path:path>")
def static_js(path):
    return send_from_directory('static/js', path)

@app.route("/plot/plot.html")
def get_plot():
    return send_from_directory('tmp', 'plot.html')

@app.route("/plot/script.js")
def get_script():
    return send_from_directory('tmp', 'script.js')

@app.route("/plot/autoload_script.js")
def get_autoload_script():
    return send_from_directory('tmp', 'autoload_script.js')

if __name__ == "__main__":
    app.run(debug=True)
