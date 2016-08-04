import ocperf as ocp
from os import path
import json
import sys


def build_ocperf_cmd(workload, events_list=None, interval=None):
    cmd = ["perf", "stat", "-x", ","]

    if events_list:
        cmd += ["-e", ",".join(events_list)]

    if interval:
        cmd += ["-I", str(interval)]

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
