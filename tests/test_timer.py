import pytest
from pathlib import Path
from tracker.timer import LocalTimer, RemoteTimer, TimerException
from tracker.config import Config, Project


@pytest.fixture(scope="function")
def new_project():
    cfg = Config(base_path=Path("./.tracker_test"))
    yield cfg.current_project
    cfg.delete()


@pytest.fixture(scope="function")
def new_remote_project():
    cfg = Config(base_path=Path("./.tracker_test"))
    Project(
        "test", cfg, "remote", "http://127.0.0.1:5000", "tester_chester"
    ).create()
    cfg.current_project = Project("test", cfg, "remote")
    yield cfg.current_project
    cfg.current_project.delete()
    cfg.delete()


def test_startstop_base(new_project):
    t = LocalTimer(new_project)
    t.start("task1")
    t.stop("task1")


def test_fail_dup_start(new_project):
    t = LocalTimer(new_project)
    t.start("task1")
    with pytest.raises(TimerException):
        t.start("task1")


def test_fail_nostart_on_stop(new_project):
    t = LocalTimer(new_project)
    t.start("task1")
    with pytest.raises(TimerException):
        t.stop("task2")


def test_fail_start_illegal_task(new_project):
    t = LocalTimer(new_project)
    with pytest.raises(TimerException):
        t.start("bogus/task")


def test_fail_stop_illegal_task(new_project):
    t = LocalTimer(new_project)
    with pytest.raises(TimerException):
        t.stop("bogus/task")


def test_tasks(new_project):
    t = LocalTimer(new_project)
    started_only = ["d"]
    finished_tasks = ["a", "b", "c"]
    for task in finished_tasks:
        t.start(task)
        t.stop(task)
    for task in started_only:
        t.start(task)
    started, finished = t.tasks()
    assert finished == finished_tasks
    assert started == started_only


def test_remote_startstop(new_remote_project):
    t = RemoteTimer(new_remote_project)
    t.start("task1")
    t.stop("task1")


def test_remote_fail_dup_start(new_remote_project):
    t = RemoteTimer(new_remote_project)
    t.start("task1")
    with pytest.raises(TimerException):
        t.start("task1")


def test_remote_nostart_on_stop(new_remote_project):
    t = RemoteTimer(new_remote_project)
    with pytest.raises(TimerException):
        t.stop("task1")


def test_remote_start_illegal_task(new_remote_project):
    t = RemoteTimer(new_remote_project)
    with pytest.raises(TimerException):
        t.start("bogus/task")


def test_remote_stop_illegal_task(new_remote_project):
    t = RemoteTimer(new_remote_project)
    with pytest.raises(TimerException):
        t.stop("bogus/task")


def test_remote_tasks(new_remote_project):
    t = RemoteTimer(new_remote_project)
    started_only = ["d"]
    finished_tasks = ["a", "b", "c"]
    for task in finished_tasks:
        t.start(task)
        t.stop(task)
    for task in started_only:
        t.start(task)
    started, finished = t.tasks()
    assert finished == finished_tasks
    assert started == started_only
