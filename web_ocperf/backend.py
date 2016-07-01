#!/usr/bin/python2
from os import path
import sys
import json

import ocperf as ocp

from plot_utils import plot_parsed_ocperf_output, store_plot_at
from ocperf_utils import (
    build_ocperf_cmd,
    parse_output,
    serialize_results,
    serialize_emap,
)


from flask import (
    Flask,
    Response,
    request,
    send_from_directory,
    render_template,
)

def run_ocperf(workload, events, interval):
    """
    workload - command to profile represented as list of strings like .split(' ')
    events - list of symbolic names of events to count
    interval - sampling interval
    """
    ocperf_cmd = build_ocperf_cmd(workload, events_list=events, interval=interval)
    emap = ocp.find_emap()
    perf_cmd = ocp.process_args(emap, ocperf_cmd)
    raw_perf_output = ocp.get_perf_output(perf_cmd)
    parsed_perf_output = parse_output(raw_perf_output)
    return parsed_perf_output

app = Flask("ocperf server", static_url_path='')

@app.route("/api/v1/emap", methods=['GET'])
def rest_emap_endpoint():
    emap = ocp.find_emap()
    json_emap = serialize_emap(emap)
    return Response(json_emap, mimetype="application/json")

@app.route("/api/v1/run", methods=['POST'])
def rest_run_endpoint():
    d = request.get_json()

    workload = d['workload'].split(' ')
    events = d['events']
    interval = d['interval']

    parsed_output = run_ocperf(workload, events, interval)
    p = plot_parsed_ocperf_output(parsed_output)
    store_plot_at(p, "tmp")

    return Response(json.dumps(parsed_output, indent=2), mimetype="application/json")

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

if __name__ == "__main__":
    app.run(debug=True)
