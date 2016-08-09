#!/usr/bin/python2
from threading import Thread

# flask related imports
from flask import (
    Flask,
    Response,
    request,
    send_from_directory,
)

# bokeh related imports
from bokeh.client import push_session
from bokeh.models import ColumnDataSource
from bokeh.plotting import curdoc, figure
from bokeh.embed import autoload_server

# utils for web_ocperf
import ocperf as ocp
from plot_utils import plot_parsed_ocperf_output
from ocperf_utils import *
from streaming import *

# globals
app = Flask("ocperf server", static_url_path='')
source = ColumnDataSource(data=dict(x=[0], y=[0]))

@app.route("/api/v1/run", methods=['POST'])
def rest_run_endpoint():
    doc = curdoc()
    session = push_session(doc)
    p = None

    d = request.get_json()
    workload = d['workload'].split(' ')
    events = d['events']
    interval = d['interval']
    streaming = d['streaming']

    kwargs = {
        "doc": doc,
        "workload": workload,
        "events": events,
        "interval": interval,
        "source": source,
    }

    if not streaming:
        parsed_output = run_ocperf(**kwargs)
        p = plot_parsed_ocperf_output(parsed_output=parsed_output)

    elif streaming:
        thread = Thread(target=blocking_task, kwargs=kwargs)
        thread.start()

        session_thread = Thread(target=session_task, kwargs={"session":session})
        session_thread.start()

        p = plot_parsed_ocperf_output(source=source)

    doc.add_root(p)
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
