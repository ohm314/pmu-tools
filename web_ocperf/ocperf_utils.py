import ocperf as ocp
from os import path
import json
import sys
import subprocess
import re


def build_ocperf_cmd(tool, workload, events_list=None, interval=None):
    cmd = None

    if tool == "stat":
        cmd = ["perf", "stat", "-x", ","]

        if events_list:
            cmd += ["-e", ",".join(events_list)]

        if interval:
            cmd += ["-I", str(interval)]

    elif tool == "record":
        cmd = ["perf", "record", "-o", "_perf.data"]

        if events_list:
            cmd += ["-e", ",".join(events_list)]

        # TODO: add support for setting frequency with -F flag


    cmd += workload
    return cmd

def async_stdout_handler(cmd, callback):
    import subprocess
    import sys
    from os import O_NONBLOCK, read
    from fcntl import fcntl, F_GETFL, F_SETFL

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    flags = fcntl(p.stdout, F_GETFL)

    buff = []
    reading = False
    while True:
        output = p.stdout.readline()

        if output != '' and not reading:
            fcntl(p.stdout, F_SETFL, flags | O_NONBLOCK)
            reading = True
            buff.append(output)

        if output != '' and reading:
            buff.append(output)

        if output == '' and p.poll() is None and reading:
            fcntl(p.stdout, F_SETFL, flags & ~O_NONBLOCK)
            reading = False

        if output == '' and len(buff) != 0:
            callback(buff)
            buff = []

        if output == '' and p.poll() is not None:
            break;

# TODO use pandas
def parse_output(raw_output):
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

def parse_perf_record_output(raw_output):
    output = {}

    for line in raw_output.split('\n')[:-1]:
        line = re.sub(r"\s+", " ", line)
        cols = line.strip(' ').split(' ')

        timestamp = float(cols[2].strip(':'))
        value = int(cols[3])
        event_name = cols[4].strip(':')

        if event_name not in output.keys():
            output[event_name] = []

        output[event_name].append( [timestamp, value] )

    return output

def print_parsed(parsed_output):
    print("="*RULE_LEN)

    for ev_type in sorted(parsed_output.keys()):
        print(ev_type)
        for sample in parsed_output[ev_type]:
            print(sample[0], sample[1])

    print("="*RULE_LEN)


def serialize_results(parsed_output):
    return json.dumps(parsed_output)

def get_ocperf_emap():
    emap = ocp.find_emap()

    d = []

    for k in emap.events.keys():
        d.append( {"sym":k, "desc":emap.desc[k]} )

    for k in emap.uncore_events.keys():
        d.append( {"sym":k, "desc":emap.uncored_events[k].desc} )

    return d

def get_perf_emap():
    import subprocess
    args = ["perf", "list", "--raw-dump"]
    l = []
    NO_DESC = "(no decsription)"

    p = subprocess.Popen(args, stdout=subprocess.PIPE)
    p.wait()
    events_list_str = p.stdout.read()
    ret = p.poll()

    if ret != 0:
        raise Exception("Something went wrong with perf list!")

    for event in events_list_str.split(' '):
        l.append({"sym": event, "desc": NO_DESC})


    return l

def get_combined_emap():
    ocperf_emap = get_ocperf_emap()
    perf_emap = get_perf_emap()

    return ocperf_emap + perf_emap

def serialize_emap(emap):
    return json.dumps(emap)

def run_ocperf(tool, workload, events, interval, doc=None, source=None):
    """
    workload - command to profile represented as list of strings like .split(' ')
    events - list of symbolic names of events to count
    interval - sampling interval
    """
    ocperf_cmd = build_ocperf_cmd(tool, workload, events_list=events, interval=interval)
    emap = ocp.find_emap()
    perf_cmd = ocp.process_args(emap, ocperf_cmd)

    raw_perf_output = None
    parsed_perf_output = ""

    if tool == "stat":
        raw_perf_output = ocp.get_perf_output(perf_cmd)
        parsed_perf_output = parse_output(raw_perf_output)

    elif tool == "record":
        raw_perf_output = ocp.get_perf_output(perf_cmd)

        p = subprocess.Popen(["perf", "script"], stdout=subprocess.PIPE)
        (out, err) = p.communicate()
        parsed_perf_output = parse_perf_record_output(out)

    return parsed_perf_output
