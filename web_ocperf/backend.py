#!/usr/bin/python2
from threading import Thread
import json
import uuid
from datetime import datetime
import os

from random import random
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


# globals
DATABASE = './web_ocperf.sqlt'

app = Flask("ocperf server", static_url_path='')
app.config.from_object(__name__)
source = ColumnDataSource(data=dict(x=[0], y=[0]))
db = pw.SqliteDatabase(DATABASE)

#--------- HELPERS ------------
@app.before_request
def before_request():
    g.db = db
    g.db.connect()

@app.after_request
def after_request(response):
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

def create_tables():
    db.connect()

    for table in [SessionModel, BenchmarkModel]:
        table.drop_table()
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

    source = ColumnDataSource(data=dict(x=[0], y=[0]))
    kwargs = {
        "tool": tool,
        "doc": doc,
        "workload": workload,
        "events": events,
        "interval": interval,
        "source": source,
        "uuid": uuid,
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
        print("Create me this session, please: " + title)

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
        print(session_uuid)
        session = SessionModel.get(SessionModel.uuid==session_uuid)
        benchmark = BenchmarkModel.create(session=session)
        result = BenchmarkSchema().dumps(benchmark)

        script = run_benchmark(request.get_json(), benchmark.uuid)
        return script

@app.route("/api/v1/benchmark/<uuid:benchmark_uuid>", methods=['GET', 'POST'])
def rest_get_benchmark_script(benchmark_uuid):
    p = "logs/" + str(benchmark_uuid) + ".perflog"

    if os.path.isfile(p):
        print("yes")

        raw_output = None

        with open(p) as f:
            raw_output = f.read()

        parsed_output = parse_perf_stat_output(raw_output)
        p = plot_parsed_ocperf_output(parsed_output=parsed_output)

        doc = curdoc()
        session = push_session(doc)

        doc.add_root(p)
        script = autoload_server(model=p, session_id=session.id)

        return Response(script)
    else:
        return Response("err", status=400)

@app.route("/api/v1/run", methods=['POST'])
def rest_run_endpoint():
    d = request.get_json()
    script = run_benchmark(d)
    return Response(script)

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


if __name__ == "__main__":
    create_tables()
    app.run(debug=True, host="0.0.0.0")
