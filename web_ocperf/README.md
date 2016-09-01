# Web_ocperf, a web frontend for Linux Perf

## How to use

0. install python libs (`pip install -r requirements.txt`)
1. start the `web_ocperf_server.sh`
2. open the http://localhost:5000
3. create and open a session
4. choose events, enter workload string, choose perf tool
5. run the benchmark
6. in the benchmark history widget choose old benchmarks, share plot links, download raw files
7. Stop the server by killing the `web_ocperf_server.sh` script (ctrl-c)

If you are running the server on a remote machine,
use ssh to forward ports 5000 and 5006.

```bash
$ ssh -L5000:127.0.0.1:5000 -L5006:127.0.0.1:5006 you@remotehost
```

Metadata will be stored in a SQlite database. SQlite database
resides in a single file. The default database filename is: `web_ocperf.sqlt`
This can be changed in the config.py.

By default, both flask and bokeh servers will reject requests which don't
originate from the localhost. This can be changed in the config.py.

To change a value in config, uncoment the value and change it.
Default are always available in the `defconfig.py` file.

To remove all stored sessions delete the `logs/` directory and the database file.
They will be regenerated next time web\_ocperf is started.

## Technical details

There are 4 main components for this web application:

1. flask backend - `backend.py`, `defconfig.py`, `config.py`
2. set of utitlity libraries - `ocperf_utils.py`, `plot_utils.py`, `streaming.py` 
3. AngularJS frontend - `static/js/index.js`, `templates/*.html`
4. bokeh server - this is a standalone app

Note that models and orm classes are still not extracted and are currently in the `backend.py`.

### backend

Implements handlers for serving static files and API calls.
All API endpoints are prefixed with `/api/v1/`.

Database access is also implemented in this module. Models are defined here, too.

On each request a new connection to the database is created and destroyed.
Source of each request is checked if it is in the `IP_WHITELIST` defined in the `config.py`.

Creating new benchmark is implemented in the `run_benchmark()`

#### API Calls:

*sessions*
function: rest_sessions_endpoint()
get: get list of all sessions as JSON
post: create a new session


*session/<uuid>*
function: rest_single_session_endpoint()
get: get list of benchmarks in session with provided <uuid>
post: create and run a new benchmark

*benchmark/<uuid>.<format>*
function: reg_get_benchmark_script()
get: depending on the value of <format>, returns benchmark with the <uuid> as
     a html page with only plot,
     the raw perf data file
     JSON object with description and HTML tag for plot widget
post: /

*emap*
function: rest_emap_endpoint()
get: JSON list of supported events with their descriptions
post: /
     

#### Static files handlers:

*www root, /*
get: return index.html

*/js/<path>*
get: return a JS file from `/static/js/`

*templates/<path>*
get: return a HTML template for AngularJS from `templates/`

#### Database access

Database access is based on the peewee ORM.
There are two models defined: the SessionModel and BenchmarkModel
They are serialized to JSON by the marshmallow library. 
Serialization format is specified in: SessionSchema and BenchmarkSchema

## Utility libraries

1. ocperf_utils.py
2. plot_utils.py
3. streaming.py

### ocperf_utils.py
most important functions:
- get_combined_emap()
- run_ocperf()

#### get_combined_emap()
It will call ocperf to get extended list of events specific for the machine.
It will call `perf list` and parse it.
Then it will return a union of those two lists.

#### run_ocperf()
It receives a list of arguments like which perf tool to run,
what is the workload, list of events, interval, uuid...

It will then create string which resembles the command that would be
entered in shell as we would run the ocperf.

After that, it will rewrite events with raw event codes if necessary (using ocperf.py).
And finally, it will run the benchmark and wait for it to finish.
At the end of execution, it will either return data parsed into a pandas DataFrame.
Parsing is different for perf script and perf record, but it is delegated to pandas.
Only define correct number of columns and provide their names in parse_perf_stat_output and
parse_perf_record_output.


### plot_utils.py
implements a single function which will return a bokeh Figure() object.
Input can be the pandas DataFrame or ColumnDataSource. Depending on which one is provided,
it will create static or streaming plot.

The returned value can be later transformed into HTML tag with script for loading the
plot widget. See run_benchmark() in backend.py.

### streaming.py
By calling the blocking_task() function, a new thread will be spawned.
Output printed to stdout by the process running in the thread will be read line by line.
Each line is parsed and a callback is registered to run on next tick of the update cycle of
the plot widget in the frontend.

Also, each streaming plot has to have a running loop in backend. See session_task().

## AngularJS frontend
All Angular (JavaScript) code for frontend is implemented in `index.js`.

There are two routes defined, root and /session/<uuid>.
They are tied to their controllers, homepageCtrl and benchmarkCtrl.

The homepageCtrl will just fetch lst of sessions and save them into $scope.sessions_list.
On the new session button click the new_session() function will be called. It will send a
POST request to the backend to create a new session and refetch the session list.

The benchmarkCtrl will fetch the list of benchmarks for the given session upon page load.
When the run button is clicked, the run() function is called. It will send a POST requst to create
and run new benchmark. The response contains description of the newly created benchmark and
a HTML tag for the plot widget. Because that tag contains JavaScript, a new DOM elemnt has to be
created using the jQuery. That way, the JavaScript will be parsed and executed by the browser.

Because that plot autoload script loads css stylesheets each time, we are clearing all stylesheets
in the <body> in the clearPlot() function.

Reloading old benchmark works the same way. Fetch JSON with description and HTML tag. Load the plot widget.

With each benchmark run the state of the frontend (selected events, workload command, environment variables)
are also saved so they can be reloaded when benchmark plot is reloaded.

There are only three relevant HTML templates:
index.html
benchmark.html (benchmark screen)
session.html (session screen)

They are located inside the templates directory.
