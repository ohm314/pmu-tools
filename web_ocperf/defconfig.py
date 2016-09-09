DATABASE = './web_ocperf.sqlt'
IP_WHITELIST = ["localhost", "127.0.0.1"]
PERF_STAT_CSV_HDR = ['timestamp',
    'value',
    'unit',
    'event_name',
    'run_time',
    'mux',
    'var','metric_val','metric_unit',
]
PERF_RECORD_CSV_HDR = [
    'process',
    'PID',
    'timestamp',
    'value',
    'event_name',
    'location',
    #'null',
    'symbol',
]
