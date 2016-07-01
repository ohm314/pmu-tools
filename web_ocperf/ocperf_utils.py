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

def serialize_emap(emap):
    d = []

    for k in emap.events.keys():
        d.append( {"sym":k, "desc":emap.desc[k]} )

    for k in emap.uncore_events.keys():
        d.append( {"sym":k, "desc":emap.uncored_events[k].desc} )

    return json.dumps(d, indent=2)
