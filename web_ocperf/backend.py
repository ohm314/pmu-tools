#!/usr/bin/python2
# standard python imports
from os import path
import sys
import json
from threading import Thread

import ocperf as ocp

# utils for web_ocperf
from plot_utils import plot_parsed_ocperf_output, store_plot_at
from ocperf_utils import *
from streaming import *

# flask related imports
from flask import (
    Flask,
    Response,
    request,
    send_from_directory,
    render_template,
)

# bokeh related imports
from bokeh.client import push_session, pull_session
from bokeh.models import ColumnDataSource
from bokeh.plotting import curdoc, figure, show
from bokeh.embed import autoload_server, components

app = Flask("ocperf server", static_url_path='')
source = ColumnDataSource(data=dict(x=[0], y=[0]))
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

        doc = curdoc()
        doc.add_root(p)
        session = push_session(doc)
        script = autoload_server(model=p, session_id=session.id)
        return Response(script)

    elif streaming:
        print("doing streaming branch")

        doc = curdoc()
        session = push_session(doc)

        print("[REGISTER] Source ID: " + str(id(source)))

        p = figure(title="streaming plot", toolbar_sticky=False)
        l = p.line(x='x', y='y', source=source)

        kwargs = {
            "doc": doc,
            "workload": workload,
            "events": events,
            "interval": interval,
            "source": source,
        }

        doc.add_root(p)

        thread = Thread(target=blocking_task, kwargs=kwargs)
        thread.start()

        session_thread = Thread(target=session_task, kwargs={"session":session})
        session_thread.start()


        script = autoload_server(model=p, session_id=session.id)

        return Response(script)

@app.route("/api/v1/emap", methods=['GET'])
def rest_emap_endpoint():
    combined_emap = get_combined_emap()
    json_emap = serialize_emap(combined_emap)

    return Response(json_emap, mimetype="application/json")

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")

@app.route("/js/<path:path>")
def static_js(path):
    return send_from_directory('static/js', path)

if __name__ == "__main__":
    app.run(debug=True)
