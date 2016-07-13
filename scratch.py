#!/usr/bin/python
import ocperf as ocp
import web_ocperf as wocp


workload = "/home/nhardi/code/cl_forward/bin/x86_64/Release/clpixel -serial -bin -file /home/nhardi/code/cl_forward/bin/x86_64/Release/test.medium.arg".split(' ')
# workload = "/usr/bin/yes"
events = ['instructions']
cmd = wocp.ocperf_utils.build_ocperf_cmd(workload, events, interval=100)


pipe = ocp.get_perf_output_pipe(cmd)

while True:
    err = pipe.stderr.readline()
    print(err)

    if err == '':
        break
