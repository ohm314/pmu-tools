#!/bin/bash
PYTHONPATH=".." python2 backend.py &

bokeh serve \
      --allow-websocket-origin 127.0.0.1:5000 \
      --allow-websocket-origin localhost:5000 &

# this will kill whole process group (including spawned processes)
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

wait
