#!/usr/bin/python2
import ocperf as ocp
from os import path
import json
from flask import Flask, Response, request, send_from_directory, render_template
import sys
from bokeh.plotting import figure
from bokeh.embed import components
from ocperf_utils import *

RULE_LEN = 80 # just for debug output

# main entry point
def scratch(workload, events, interval):
    # emulating ocperf.py call from cmd line
    print(workload)
    # print(CL_PIXEL_CMD)
    perf_cmd = build_perf_cmd(workload, events_list=events, interval=interval)

    # activating ocperf's mapping of symbolic to msr codes for event arguments
    emap = ocp.find_emap()
    cmd = ocp.process_args(emap, perf_cmd)

    # actually running perf with storing return value
    raw_perf_output = ocp.get_perf_output(cmd)

    # returned value is raw string, parse it
    parsed_perf_output = parse_output(raw_perf_output)

    return parsed_perf_output

# backend part
app = Flask("ocperf server", static_url_path='')

# TODO set http response header content type to application/json
@app.route("/api/v1/emap", methods=['GET'])
def rest_emap_endpoint():
    emap = ocp.find_emap()
    return Response(serialize_emap(emap), mimetype="application/json")

@app.route("/api/v1/run", methods=['POST'])
def rest_run_endpoint():
    # extract data from request
    d = request.get_json()

    workload = d['workload']
    workload = workload.split(' ')

    events = d['events']
    interval = d['interval']

    # run analysis
    parsed_output = scratch(workload, events, interval)

    k = parsed_output.keys()[0]
    samples = parsed_output[k]

    # create plot
    x = [sample[0] for sample in samples]
    y = [sample[1] for sample in samples]

    p = figure()
    p.line(x, y)

    script, div = components(p, wrap_script=False)

    with file("tmp/plot.html", "w") as f:
        print("writing plot")
        f.write(div)

    with file("tmp/script.js", "w") as f:
        print("writing script")
        f.write(script)

    return Response(json.dumps(parsed_output, indent=2), mimetype="application/json")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/js/<path:path>")
def static_js(path):
    return send_from_directory('static/js', path)

@app.route("/plot/plot.html")
def get_plot():
    r = None
    with file("tmp/plot.html") as f:
        r = f.read()

    return Response(r)

@app.route("/plot/script.js")
def get_script():
    r = None
    with file("tmp/script.js") as f:
        r = f.read()

    return Response(r)

@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    # response.headers['Cache-Control'] = 'public, max-age=0'
    response.headers['Cache-Control'] = 'no-cache, no-store'
    return response

# TODO server
def runserver():
    app.run(debug=True)


if __name__ == "__main__":
    if "--serve" in sys.argv:
        runserver()
    else:
        print("-"*RULE_LEN)
        scratch()
