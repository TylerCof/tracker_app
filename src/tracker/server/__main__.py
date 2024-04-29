import os
from pathlib import Path
from flask import Flask, abort, request, jsonify
from itsdangerous import URLSafeSerializer
from tracker.config import Config, Project
from tracker.timer import (
    LocalTimer,
    TimerException,
    BadLabelException,
    NoStartException,
    DupStartException,
)

app = Flask(__name__)

SERVER_CONFIG_ROOT = Path("./.tracker-server")
AUTH_KEY = "username"


def generate_key(project, username):
    auth_s = URLSafeSerializer(os.environ["SECRET_KEY"], "auth")
    # Combine the project name and the "founding" username to create a special unique project key.
    project_key = auth_s.dumps({"project": project, "username": username})
    return project_key


def get_project_from_key(project_key):
    auth_s = URLSafeSerializer(os.environ["SECRET_KEY"], "auth")
    # Extract the project name and username from the special unique project key and return the project name.
    data = auth_s.loads(project_key)
    return data["project"]


@app.route("/api/init", methods=["POST"])
def init_project():
    f = request.form
    if not f.get("username") or not f.get("project"):
        abort(400)

    project_key = generate_key(f["project"], f["username"])

    config = Config(SERVER_CONFIG_ROOT)
    Project(project_key, config=config).create()

    return jsonify({"key": project_key})


@app.route("/api/delete", methods=["DELETE"])
def delete_project():
    key = ""
    if request.authorization:
        key = request.authorization.get(AUTH_KEY)

    config = Config(SERVER_CONFIG_ROOT)
    proj = Project(key, config=config)
    proj.delete()

    return jsonify({})


@app.route("/api/start", methods=["POST"])
def start():
    """
    The client must provide a project key via
    BasicAuth and a label via the POST form.
    Failure to do so will result in a 400 error.

    If both are provided, the server will return either
        { "result": "ok" }
    or
        { "result": "error", "type": ERROR_STR }
    where ERROR_STR is currently one of
        "dup_start" -- indicates this label was already
                       previously started
        "bad_label" -- indicates the label contains
                       illegal characters
        "internal"  -- unknown internal error; this should
                       never happen
    """
    key = ""
    if request.authorization:
        key = request.authorization.get(AUTH_KEY)

    f = request.form
    user = f.get("user")
    if not key or not f.get("label") or not user:
        abort(400)

    config = Config(SERVER_CONFIG_ROOT)
    proj = Project(key, config=config, user=user)
    config.set_project(proj)
    timer = LocalTimer(proj)

    try:
        timer.start(f["label"])

    except BadLabelException:
        return jsonify({"result": "error", "type": "bad_label"})

    except DupStartException:
        return jsonify({"result": "error", "type": "dup_start"})

    except TimerException:
        return jsonify({"result": "error", "type": "internal"})

    return jsonify({"result": "ok"})


@app.route("/api/stop", methods=["POST"])
def stop():
    """
    The client must provide a project key via
    BasicAuth and a label via the POST form.
    Failure to do so will result in a 400 error.

    If both are provided, the server will return either
        { "result": "ok" }
    or
        { "result": "error", "type": ERROR_STR }
    where ERROR_STR is currently one of
        "no_start"  -- indicates this label was not
                       previously started
        "bad_label" -- indicates the label contains
                       illegal characters
        "internal"  -- unknown internal error; this should
                       never happen
    """
    key = ""
    if request.authorization:
        key = request.authorization.get(AUTH_KEY)

    f = request.form
    user = f.get("user")
    if not key or not f.get("label") or not user:
        abort(400)

    config = Config(SERVER_CONFIG_ROOT)
    proj = Project(key, config=config, user=user)
    config.set_project(proj)
    timer = LocalTimer(proj)

    try:
        timer.stop(f["label"])

    except NoStartException:
        return jsonify({"result": "error", "type": "no_start"})

    except BadLabelException:
        return jsonify({"result": "error", "type": "bad_label"})
    except TimerException:
        return jsonify({"result": "error", "type": "internal"})

    return jsonify({"result": "ok"})


@app.route("/api/tasks", methods=["GET"])
def tasks():
    """
    The client must provide a project key via
    BasicAuth.
    Failure to do so will result in a 400 error.

    If both are provided, the server will return either
        { "result": "ok", "active": [...], "finished": [...] }
    where the arrays contain the task names as strings,
    or
        { "result": "error", "type": ERROR_STR }
    where ERROR_STR is currently one of
        "internal"  -- unknown internal error; could be undefined project
    """
    key = ""
    if request.authorization:
        key = request.authorization.get(AUTH_KEY)

    if not key:
        abort(400)

    config = Config(SERVER_CONFIG_ROOT)
    proj = Project(key, config=config)
    config.set_project(proj)
    timer = LocalTimer(proj)

    try:
        tuple_of_lists = timer.tasks()
    except TimerException:
        return jsonify({"result": "error", "type": "internal"})

    return jsonify(
        {
            "result": "ok",
            "active": tuple_of_lists[0],
            "finished": tuple_of_lists[1],
        }
    )


@app.route("/api/project", methods=["GET"])
def connect():
    key = ""
    username = ""
    if request.authorization:
        key = request.authorization.get(AUTH_KEY)
    f = request.form
    if not key or not f.get("username"):
        abort(400)
    # this should work, hypothetically. need to work on CLI next, then sort issues out.
    return jsonify({"result": "ok", "name": str(get_project_from_key(key))})


@app.route("/api/times", methods=["GET"])
def task_times():
    """
    The client must provide a project key via
    BasicAuth.
    Failure to do so will result in a 400 error.

    If both are provided, the server will return either
        { "result": "ok", "timings": {...} }
    where 'timings': { 'task_name1': [(duration:float,user:str), ...], ... }
    or
        { "result": "error", "type": ERROR_STR }
    where ERROR_STR is currently one of
        "internal"  -- unknown internal error; could be undefined project
    """
    key = ""
    if request.authorization:
        key = request.authorization.get(AUTH_KEY)
    if not key:
        abort(400)
    config = Config(SERVER_CONFIG_ROOT)
    proj = Project(key, config=config)
    config.set_project(proj)
    timer = LocalTimer(proj)
    try:
        timings = timer.details()
    except TimerException:
        return jsonify({"result": "error", "type": "internal"})

    return jsonify({"result": "ok", "timings": timings})


@app.route("/")
def index():
    return "Server running... brief documentation should go here"


app.run(host="0.0.0.0")
