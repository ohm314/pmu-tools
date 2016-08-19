import ocperf as ocp
from os import path
import json
import sys
import subprocess
import re
import pandas as pd
from StringIO import StringIO

def build_ocperf_cmd(tool, workload, events_list=None, interval=None):
    cmd = None

    if tool == "stat":
        cmd = ["perf", "stat", "-x", ","]

        if events_list:
            cmd += ["-e", ",".join(events_list)]

        if interval:
            cmd += ["-I", str(interval)]

    elif tool == "record":
        cmd = ["perf", "record", "-o", "perf.data"]

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

def parse_perf_stat_output(raw_output):
    COL_NAMES = ['timestamp', 'value', 'null', 'event_name', 'raw_value', 'mux']

    df = pd.read_csv(StringIO(raw_output), names=COL_NAMES)

    output = {}
    for event in df.event_name.unique():
        d = df[df.event_name == event][['timestamp', 'value']]
        output[event] = d.as_matrix()

    return output


def parse_perf_record_output(raw_output):

    COL_NAMES = [
        'process',
        'PID',
        'timestamp',
        'value',
        'event_name',
        'location',
        'null',
        'symbol',
    ]

    df = pd.read_csv(StringIO(raw_output), names=COL_NAMES,
                     sep=':?\s+', engine='python')

    output = {}
    for event in df.event_name.unique():
        d = df[df.event_name == event][['timestamp', 'value']]
        output[event] = d.as_matrix()

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

    try:
        for k in emap.uncore_events.keys():
            d.append( {"sym":k, "desc":emap.uncored_events[k].desc} )
    except:
        pass

    return d

def parse_raw_perf_list():
    import re
    from subprocess import Popen, PIPE

    workload = ["perf", "list"]
    matcher = r"\s+(\S+)\s+.*\[([Hardware|Software|Kernel].*event)\]"
    p = re.compile(matcher)

    (out, err) = Popen(workload, stdout=PIPE).communicate()

    events_list = []

    for line in out.split('\n'):
        m = p.search(line)

        if m:
            events_list.append(m.groups()[0])

    return events_list

def get_perf_emap():
    import subprocess
    args = ["perf", "list", "--raw-dump"]
    l = []
    NO_DESC = "(no decsription)"

    p = subprocess.Popen(args, stdout=subprocess.PIPE)
    p.wait()
    events_list_str = p.stdout.read()
    ret = p.poll()

    if ret == 0:
        for event in events_list_str.split(' '):
            l.append({"sym": event, "desc": NO_DESC})
    else:
        events_list = parse_raw_perf_list()

        for event in events_list:
            l.append({"sym": event, "desc": NO_DESC})

    return l

def get_combined_emap():
    ocperf_emap = get_ocperf_emap()
    perf_emap = get_perf_emap()

    combined_emap = perf_emap + ocperf_emap

    return combined_emap

def serialize_emap(emap):
    return json.dumps(emap)

def run_ocperf(tool, workload, events, interval, doc=None, source=None, env=None, **kwargs):
    """
    workload - command to profile represented as list of strings like .split(' ')
    events - list of symbolic names of events to count
    interval - sampling interval
    """
    ocperf_cmd = build_ocperf_cmd(tool, workload, events_list=events, interval=interval)
    emap = ocp.find_emap()
    perf_cmd = ocp.process_args(emap, ocperf_cmd)
    perf_cmd = " ".join(perf_cmd)

    if env:
        perf_cmd = str(env) + " " + perf_cmd

    # raw_perf_output = None
    raw_perf_output = ocp.get_perf_output(perf_cmd)
    parsed_perf_output = ""

    if tool == "stat":
        # raw_perf_output = ocp.get_perf_output(perf_cmd)
        parsed_perf_output = parse_perf_stat_output(raw_perf_output)

        with open("logs/" + str(kwargs['uuid']) + ".perflog", "w+") as f:
            f.write(raw_perf_output)

    elif tool == "record":
        # raw_perf_output = ocp.get_perf_output(perf_cmd)

        p = subprocess.Popen(["perf", "script"], stdout=subprocess.PIPE)
        (out, err) = p.communicate()
        parsed_perf_output = parse_perf_record_output(out)

    return parsed_perf_output
