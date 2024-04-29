import pytest
from pathlib import Path
from tracker.config import Config, ConfigException, Project

test_url = "http://localhost:5000"


@pytest.fixture(scope="function")
def new_config():
    cfg = Config(base_path=Path("./.tracker_test"))
    yield cfg
    cfg.delete()


def test_create_and_delete(new_config):
    cfg = new_config

    default_project = cfg.current_project
    assert default_project.name == "default"
    assert default_project.origin == "local"
    assert default_project.active_timers_path.exists()
    assert default_project.finished_timers_path.exists()

    proj1 = Project("new_project", config=cfg)
    assert proj1.exists() == False
    proj1.create()
    assert proj1.exists() == True

    default_and_new_project = cfg.get_project_names()
    assert "default" in default_and_new_project
    assert "new_project" in default_and_new_project

    proj1again = Project("new_project", config=cfg)
    assert proj1again.exists() == True

    assert proj1.name == proj1again.name
    assert proj1.active_timers_path == proj1again.active_timers_path
    assert proj1.finished_timers_path == proj1again.finished_timers_path

    proj1.delete()
    assert proj1.exists() == False
    assert proj1again.exists() == False

    default_only = cfg.get_project_names()
    assert "default" in default_only
    assert "new_project" not in default_only


"""

    remote_proj = cfg.create_project_named('remote_project', test_url)
    assert cfg.has_project_named('remote_project')
    assert remote_proj.origin == 'remote'
    assert remote_proj.remote_key is not None and remote_proj.remote_key != ''

    cfg.wipe_project(remote_proj)
    assert not cfg.has_project_named('remote_project')

    assert cfg.current_project.name == default_project.name

"""


def test_switch_projects(new_config):
    cfg = new_config

    proj1 = Project("project1", config=cfg)
    cfg.set_project(proj1)
    assert cfg.current_project.name == "project1"

    proj2 = Project("project2", config=cfg)
    cfg.set_project(proj2)
    assert cfg.current_project.name == "project2"


def test_fail_delete_notexist(new_config):
    cfg = new_config
    assert "new_project" not in cfg.get_project_names()
    with pytest.raises(ConfigException):
        Project("new_project", config=cfg).delete()


def test_load_delete_remote_project(new_config):
    Project(
        "test",
        new_config,
        origin="remote",
        url="http://localhost:5000",
        user="chester_tester",
    ).create()

    proj = Project("test", new_config, origin="local")
    proj.delete()

    assert not proj.exists()
