import pytest
import requests
from requests.auth import HTTPBasicAuth

# This test requires a server to be running locally on port 5000.
# Start the server before running the tests using './run-server.sh'.
# Note that it would be really cool to automate this, too, in the
# future, to where this test script would check port 5000 to see
# if anything is listening, and then if not, manually start the server
# and then kill the server at this script's completion.
# Maybe some day!
base_url = "http://localhost:5000"


@pytest.fixture(scope="function")
def project_key():
    result = requests.post(
        "{}/api/init".format(base_url),
        data={
            "project": "new_project",
            "username": "test_user",
        },
    )
    r = result.json()

    yield r["key"]

    result = requests.delete(
        "{}/api/delete".format(base_url),
        auth=HTTPBasicAuth(r["key"], ""),
        data={},
    )


def test_startstop(project_key):
    result = requests.post(
        "{}/api/start".format(base_url),
        auth=HTTPBasicAuth(project_key, ""),
        data={
            "label": "bugfix",
        },
    )
    r = result.json()
    assert r.get("result") == "ok"

    result = requests.post(
        "{}/api/stop".format(base_url),
        auth=HTTPBasicAuth(project_key, ""),
        data={
            "label": "bugfix",
        },
    )
    r = result.json()
    assert r.get("result") == "ok"


def test_tasks(project_key):
    result = requests.post(
        "{}/api/start".format(base_url),
        auth=HTTPBasicAuth(project_key, ""),
        data={
            "label": "completed1",
        },
    )
    r = result.json()
    assert r.get("result") == "ok"

    result = requests.post(
        "{}/api/stop".format(base_url),
        auth=HTTPBasicAuth(project_key, ""),
        data={
            "label": "completed1",
        },
    )
    r = result.json()
    assert r.get("result") == "ok"

    result = requests.post(
        "{}/api/start".format(base_url),
        auth=HTTPBasicAuth(project_key, ""),
        data={
            "label": "completed2",
        },
    )
    r = result.json()
    assert r.get("result") == "ok"

    result = requests.post(
        "{}/api/stop".format(base_url),
        auth=HTTPBasicAuth(project_key, ""),
        data={
            "label": "completed2",
        },
    )
    r = result.json()
    assert r.get("result") == "ok"

    result = requests.post(
        "{}/api/start".format(base_url),
        auth=HTTPBasicAuth(project_key, ""),
        data={
            "label": "running1",
        },
    )
    r = result.json()
    assert r.get("result") == "ok"

    result = requests.get(
        "{}/api/tasks".format(base_url), auth=HTTPBasicAuth(project_key, "")
    )
    r = result.json()
    assert r.get("result") == "ok"
    assert r.get("active") == ["running1"]
    assert r.get("finished") == ["completed1", "completed2"]


def test_fail_stopnostart(project_key):
    result = requests.post(
        "{}/api/stop".format(base_url),
        auth=HTTPBasicAuth(project_key, ""),
        data={
            "label": "bugfix",
        },
    )
    r = result.json()
    assert r["result"] == "error" and r["type"] == "no_start"


def test_fail_dupstart(project_key):
    result = requests.post(
        "{}/api/start".format(base_url),
        auth=HTTPBasicAuth(project_key, ""),
        data={
            "label": "bugfix",
        },
    )
    r = result.json()
    assert r["result"] == "ok"

    result = requests.post(
        "{}/api/start".format(base_url),
        auth=HTTPBasicAuth(project_key, ""),
        data={
            "label": "bugfix",
        },
    )
    r = result.json()
    assert r["result"] == "error" and r["type"] == "dup_start"


def test_fail_start_nokey():
    result = requests.post(
        "{}/api/start".format(base_url),
        # auth=HTTPBasicAuth('NO_AUTH_GIVEN', ''),
        data={
            "label": "bugfix",
        },
    )
    assert result.status_code == 400
