#!/usr/bin/python2
from threading import Thread
import json
import uuid
from datetime import datetime
import os

import peewee as pw
# from playhouse.flask_utils import FlaskDB
from marshmallow import Schema, fields

# flask related imports
from flask import (
    Flask,
    Response,
    request,
    send_from_directory,
    g,
    jsonify,
    abort,
)

# bokeh related imports
from bokeh.client import push_session
from bokeh.models import ColumnDataSource
from bokeh.plotting import curdoc, figure
from bokeh.embed import autoload_server

# utils for web_ocperf
import ocperf as ocp
from plot_utils import plot_parsed_ocperf_output
from ocperf_utils import *
from streaming import *

from defconfig import *
from config import *

# globals
app = Flask("ocperf server", static_url_path='')
app.config.from_object(__name__)
source = ColumnDataSource(data=dict(x=[0], y=[0]))
db = pw.SqliteDatabase(DATABASE)

def init():
    """initialization code"""
    if not os.path.exists('logs/'):
        os.makedirs('logs/')

#--------- HELPERS ------------
@app.before_request
def before_request():
    if request.remote_addr not in IP_WHITELIST:
        abort(403)
    else:
        g.db = db
        g.db.connect()

@app.after_request
def after_request(response):
    if response.status_code < 400:
        g.db.close()

    return response

#--------- MODELS -------------
class BaseModel(pw.Model):
    class Meta:
        database = db

class SessionModel(BaseModel):
    title = pw.CharField(default="no title")
    uuid = pw.UUIDField(default=uuid.uuid4)
    date_created = pw.DateTimeField(default=datetime.utcnow)
    # date_updated = pw.DateTimeField()

class BenchmarkModel(BaseModel):
    session = pw.ForeignKeyField(SessionModel, related_name='benchmarks')
    date_created = pw.DateTimeField(default=datetime.utcnow)
    uuid = pw.UUIDField(default=uuid.uuid4)
    frontend_state = pw.TextField()

def create_tables():
    db.connect()

    for table in [SessionModel, BenchmarkModel]:
        # table.drop_table()
        table.create_table(True)

#---------- SCHEMAS -----------
class SessionSchema(Schema):
    title = fields.Str()
    uuid = fields.UUID()
    date_created = fields.DateTime()
    # TODO date_updated = fields.Date(dump_only=True)

class BenchmarkSchema(Schema):
    session = fields.Nested(SessionSchema, only=['uuid'])
    date_created = fields.DateTime()
    uuid = fields.UUID()
    frontend_state = fields.String()

# util
def run_benchmark(d, uuid=None):
    doc = curdoc()
    session = push_session(doc)
    p = None

    # d = request.get_json()
    workload = d['workload'].split(' ')
    events = d['events']
    interval = d['interval']
    streaming = d['streaming']
    tool = d['tool']
    env = d['env']

    source = ColumnDataSource(data=dict(x=[0], y=[0]))
    kwargs = {
        "tool": tool,
        "doc": doc,
        "workload": workload,
        "events": events,
        "interval": interval,
        "source": source,
        "uuid": uuid,
        "env": str(env),
    }

    if tool == "record":
        parsed_output = run_ocperf(**kwargs)
        p = plot_parsed_ocperf_output(parsed_output=parsed_output)

    elif tool == "stat":
        if not streaming:
            parsed_output = run_ocperf(**kwargs)
            p = plot_parsed_ocperf_output(parsed_output=parsed_output)

        elif streaming:
            thread = Thread(target=blocking_task, kwargs=kwargs)
            session_thread = Thread(target=session_task,
                                    kwargs={"session":session})

            thread.start()
            session_thread.start()

            p = plot_parsed_ocperf_output(source=source)

    if p:
        doc.add_root(p)

    script = autoload_server(model=p, session_id=session.id)
    return script

@app.route("/api/v1/session/", methods=['GET', 'POST'])
def rest_sessions_endpoint():
    if request.method == 'GET':
        sessions = SessionModel.select()
        result = SessionSchema(many=True).dumps(sessions, many=True)
        return result.data

    elif request.method == 'POST':
        title = request.get_json()['session_title']

        s = SessionModel.create(title=title)
        json_s, err = SessionSchema().dumps(s)

        return Response(json_s, mimetype="application/json")

@app.route("/api/v1/session/<uuid:session_uuid>", methods=['GET', 'POST'])
def rest_single_session_endpoint(session_uuid):
    if request.method == 'GET':
        session = SessionModel.get(SessionModel.uuid==session_uuid)
        result = BenchmarkSchema().dumps(session.benchmarks, many=True)
        return result.data

    elif request.method == 'POST':
        state = json.dumps(request.get_json())

        session = SessionModel.get(SessionModel.uuid==session_uuid)
        benchmark = BenchmarkModel.create(session=session, frontend_state=state)
        result = BenchmarkSchema().dumps(benchmark)

        script = run_benchmark(request.get_json(), benchmark.uuid)
        # return script, state
        ret = jsonify({'script':script, 'state':request.get_json()})
        return ret

@app.route("/api/v1/benchmark/<uuid:benchmark_uuid>.<out_format>", methods=['GET', 'POST'])
def rest_get_benchmark_script(benchmark_uuid, out_format="script"):
    SUPPORTED_FORMATS = ['js', 'perflog', 'html', 'data']
    TEMPLATE = """
    <html>
    <body> <div class="bk-root">{} </div></body>
    </html>
    """
    filename = None
    raw_output = None

    if out_format not in SUPPORTED_FORMATS:
        abort()

    benchmark = BenchmarkModel.get(BenchmarkModel.uuid == benchmark_uuid)
    state = json.loads(benchmark.frontend_state)

    if state['tool'] == "record":
        filename = "logs/" + str(benchmark_uuid) + ".perf.data"

        if os.path.isfile(filename):
            raw_perf_script_output = read_perfdata(filename)
            parsed_output = parse_perf_record_output(raw_perf_script_output)
        else:
            abort(404)

    elif state['tool'] == 'stat':
        filename = "logs/" + str(benchmark_uuid) + ".perflog"

        if os.path.isfile(filename):
            with open(filename) as f:
                raw_output = f.read()

            parsed_output = parse_perf_stat_output(raw_output)
        else:
            abort(404)


    p = plot_parsed_ocperf_output(parsed_output=parsed_output)


    doc = curdoc()
    session = push_session(doc)

    doc.add_root(p)
    script = autoload_server(model=p, session_id=session.id)

    if out_format == "js":
        # return Response(script)
        return jsonify({'script': script, 'state':state})
    elif out_format == "perflog":
        send_from_directory("logs", filename)
    elif out_format == "html":
        out = TEMPLATE.format(script)
        return Response(out)
    else:
        abort()

# @app.route("/api/v1/run", methods=['POST'])
# def rest_run_endpoint():
#     d = request.get_json()
#     script = run_benchmark(d)
#     # return Response(script)

#     return jsonify({script:script, state:state})

@app.route("/api/v1/emap", methods=['GET'])
def rest_emap_endpoint():
    combined_emap = get_combined_emap()
    json_emap = serialize_emap(combined_emap)

    return Response(json_emap, mimetype="application/json")

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")

@app.route("/js/<path:path>")
def static_js(path):
    return send_from_directory('static/js', path)

@app.route("/templates/<path:path>")
def static_html(path):
    return send_from_directory('templates', path)

@app.route("/api/v1/benchmark/<uuid:uuid>.perflog")
def get_raw_data(uuid):
    try:
        filename = str(uuid) + ".perflog"
        return send_from_directory('logs', filename)
    except Exception as e:
        return Response(status=404)

if __name__ == "__main__":
    init()
    create_tables()
    app.run(debug=True, host="0.0.0.0")
