#!/usr/bin/python2
import ocperf as ocp
from os import path
import json
from flask import Flask, Response, request
import sys

RULE_LEN = 80 # just for debug output

# for building workload string (it's list of string args to perf actually)
CL_PIXEL_PATH = "/home/nhardi/code/cl_forward/bin/x86_64/Release/"
CL_PIXEL_EXEC = path.join(CL_PIXEL_PATH, "clpixel")
RESULTS_FILE = path.join(CL_PIXEL_PATH, "test.small.arg")
CL_PIXEL_CMD = [CL_PIXEL_EXEC, "-serial", "-bin", "-file", RESULTS_FILE]

# utils
def build_perf_cmd(workload, events_list=None, interval=None):
    """
    if event list is empty
    then run perf stat without -e arguments

    else if event list is NOT empty
    insert -e args as needed

    if interval is given,
    add an -I flag

    at last, append workload arguments
    """
    cmd = ["perf", "stat", "-x", ","]

    if events_list:
        cmd += ["-e", ",".join(events_list)]

    if interval:
        cmd += ["-I", str(interval)]

    cmd += workload
    return cmd

# TODO use pandas
def parse_output(raw_output):
    print(raw_output)
    # column description
    # ------------------
    # 0 - timestamp
    # 1 - value
    # 2 - TODO empty
    # 3 - event type
    # 4 - TODO (unknown)
    # 5 - TODO (unknown)

    TIMESTAMP = 0
    VALUE = 1
    EVENT_TYPE = 3

    output = {}

    for line in raw_output.split('\n')[:-1]:
        splitted = line.split(',')

        timestamp = float(splitted[TIMESTAMP])
        value = int(splitted[VALUE])
        ev_type = splitted[EVENT_TYPE]

        if ev_type not in output.keys():
            output[ev_type] = []

        output[ev_type].append( [timestamp, value] )

    return output
    # return [l.split(',') for l in raw_output.split('\n')[:-1]]

def print_parsed(parsed_output):
    print("="*RULE_LEN)

    for ev_type in sorted(parsed_output.keys()):
        print(ev_type)
        for sample in parsed_output[ev_type]:
            print(sample[0], sample[1])

    print("="*RULE_LEN)


# TODO serializers
def serialize_results(parsed_output):
    return json.dumps(parsed_output)

def serialize_emap(emap):
    d = {}

    for k in emap.events.keys():
        d[k] = emap.desc[k]

    for k in emap.uncore_events.keys():
        d[k] = emap.uncored_events[k].desc

    return json.dumps(d, indent=2)



# main entry point
def scratch(workload, events, interval):
    # emulating ocperf.py call from cmd line
    print(workload)
    print(CL_PIXEL_CMD)
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
app = Flask("ocperf server")

# TODO set http response header content type to application/json
@app.route("/api/v1/emap", methods=['GET'])
def rest_emap_endpoint():
    emap = ocp.find_emap()
    return Response(serialize_emap(emap), mimetype="application/json")

@app.route("/api/v1/run", methods=['POST'])
def rest_run_endpoin():
    print(request.mimetype)
    d = request.get_json()

    workload = d['workload']
    workload = workload.split(' ')

    events = d['events']
    interval = d['interval']

    parsed_output = scratch(workload, events, interval)
    return Response(json.dumps(parsed_output, indent=2), mimetype="application/json")

# TODO server
def runserver():
    app.run(debug=True)


if __name__ == "__main__":
    if "--serve" in sys.argv:
        runserver()
    else:
        print("-"*RULE_LEN)
        scratch()
