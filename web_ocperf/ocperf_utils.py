from os import path
import json
import subprocess
import re
from StringIO import StringIO
import pandas as pd
import ocperf as ocp
import cpuinfo
import logging
from config import config


PERF_STAT_CSV_HDR = ['timestamp',
                     'value',
                     'unit',
                     'event_name',
                     'run_time',
                     'mux',
                     'var',
                     'metric_val',
                     'metric_unit',
                    ]
PERF_RECORD_CSV_HDR = ['process',
                       'PID',
                       'timestamp',
                       'value',
                       'event_name',
                       'location',
                       #'null',
                       'symbol',
                       ]


def build_ocperf_cmd(tool, workload, events_list=None, interval=None, **kwargs):
    cmd = None

    if tool == "stat":
        cmd = ["perf", "stat", "-x", ","]

        if events_list:
            cmd += ["-e", ",".join(events_list)]

        if interval:
            cmd += ["-I", str(interval)]

    elif tool == "record":
        adv_freq = cpuinfo.get_cpu_info()['hz_advertised_raw'][0]
        freq = cpuinfo.get_cpu_info()['hz_actual_raw'][0]
        if freq / adv_freq < 0.95 or freq / adv_freq > 1.05:
            logging.warning('Frequency mismatch:')
            logging.warning('%s expected but got %s' %
                            (cpuinfo.get_cpu_info()['hz_advertised'],
                            cpuinfo.get_cpu_info()['hz_actual']))
            logging.warning('Frequency scaling and Turbo boost should be disabled')
        sample_period = freq*(float(interval)/1000.) + 3
        filename = "logs/" + str(kwargs['uuid']) + ".perf.data"
        cmd = ["perf", "record", "-c", str(int(sample_period)), "-o", filename]

        if events_list:
            events = "'{cycles," + ",".join(events_list) + "}:S'"
            cmd += ["-e", events]

        # TODO: add support for setting frequency with -F flag

    cmd += workload
    return cmd


def async_stdout_handler(cmd, callback):
    import subprocess
    import sys
    from os import O_NONBLOCK, read
    from fcntl import fcntl, F_GETFL, F_SETFL

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            universal_newlines=True)
    flags = fcntl(proc.stdout, F_GETFL)

    buff = []
    reading = False
    while True:
        output = proc.stdout.readline()

        if output != '' and not reading:
            fcntl(proc.stdout, F_SETFL, flags | O_NONBLOCK)
            reading = True
            buff.append(output)

        if output != '' and reading:
            buff.append(output)

        if output == '' and proc.poll() is None and reading:
            fcntl(proc.stdout, F_SETFL, flags & ~O_NONBLOCK)
            reading = False

        if output == '' and len(buff) != 0:
            callback(buff)
            buff = []

        if output == '' and proc.poll() is not None:
            break


def parse_perf_stat_output(raw_output):
    df = pd.read_csv(StringIO(raw_output), index_col=False, header=None,
                              names=PERF_STAT_CSV_HDR)
    df['timestamp'] = df['timestamp'].sub(df['timestamp'][0])

    return df


def parse_perf_record_output(raw_output):
    df = pd.read_csv(StringIO(raw_output), names=PERF_RECORD_CSV_HDR,
                     sep=';', engine='python')
    df['timestamp'] = df['timestamp'].sub(df['timestamp'][0])

    return df


def get_ocperf_emap():
    emap = ocp.find_emap()

    d = []

    for k in emap.events.keys():
        if not k == '':
            d.append({"sym": k, "desc": emap.desc[k]})

    try:
        for k in emap.uncore_events.keys():
            if not k == '':
                d.append({"sym": k, "desc": emap.uncored_events[k].desc})
    except:
        pass

    return d


def parse_raw_perf_list():

    workload = ["perf", "list"]
    matcher = r"\s+(\S+)\s+.*\[([Hardware|Software|Kernel].*event)\]"
    p = re.compile(matcher)

    (out, err) = subprocess.Popen(workload, stdout=subprocess.PIPE).communicate()

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
        for event in events_list_str.strip().split(' '):
            l.append({"sym": event, "desc": NO_DESC})
    else:
        events_list = parse_raw_perf_list()

        for event in events_list:
            l.append({"sym": event, "desc": NO_DESC})

    return l


def read_perfdata(filename):
    p = subprocess.Popen(["perf", "script", "-s", "perf-script.py", "-i", filename], stdout=subprocess.PIPE)
    (out, err) = p.communicate()
    return out


def get_combined_emap():
    ocperf_emap = get_ocperf_emap()
    perf_emap = get_perf_emap()

    combined_emap = perf_emap + ocperf_emap

    return combined_emap

def serialize_emap(emap):
    return json.dumps(emap)


def run_ocperf(tool, workload, events, interval, doc=None, source=None, env=None, **kwargs):
    """
    workload - command to profile represented as list of strings
    events - list of symbolic names of events to count
    interval - sampling interval
    """

    # first get modifiers for events as defined in config.yaml
    event_strs = []
    for event in events:
        if event in config.event and 'modifier' in config.event[event]:
            event += config.event[event]['modifier']
        event_strs.append(event)

    ocperf_cmd = build_ocperf_cmd(tool, workload, events_list=event_strs,
                                  interval=interval, **kwargs)
    emap = ocp.find_emap()
    perf_cmd = ocp.process_args(emap, ocperf_cmd)
    perf_cmd = " ".join(perf_cmd)

    if env:
        perf_cmd = str(env) + " " + perf_cmd

    raw_perf_output = ocp.get_perf_output(perf_cmd)
    parsed_perf_output = None

    uuid = str(kwargs['uuid'])

    if tool == "stat":
        with open("logs/" + uuid + ".perflog", "w+") as f:
            f.write(raw_perf_output)

        parsed_perf_output = parse_perf_stat_output(raw_perf_output)

    elif tool == "record":
        filename = "logs/" + uuid + ".perf.data"
        raw_perf_script_output = read_perfdata(filename)
        parsed_perf_output = parse_perf_record_output(raw_perf_script_output)

    return parsed_perf_output
