import pytest
from tracker.cli import *
from tracker.config import Config, Project
from tracker.timer import TimerFactory, TimerException
from pathlib import Path
import subprocess
import time
import re


def test_creation():
    CLI()


@pytest.fixture(scope="function")
def new_config():
    cfg = Config(base_path=Path("./.tracker_test"))
    yield cfg
    cfg.delete()


@pytest.fixture(scope="function")
def new_remote_config():
    cfg = Config(base_path=Path("./.tracker_test"))
    Project(
        "test", cfg, "remote", "http://127.0.0.1:5000", "tester_chester"
    ).create()
    cfg.current_project = Project("test", cfg, "remote")
    yield cfg
    cfg.current_project.delete()
    cfg.delete()


# @pytest.fixture(scope="function")
# def server():
#     proc = subprocess.Popen(["python",  "-m",  "tracker.server"])
#     yield proc
#     proc.kill()


def test_start(new_config):
    timer = TimerFactory.get_timer(new_config)
    cmd_class = StartCommand(new_config)

    cmd_class.run(["test"])

    assert "test" in timer.tasks()[0]


def test_start_no_args(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message_called
        help_message_called += 1
        return "test"

    help_message_called = 0
    monkeypatch.setattr(StartCommand, "help_message", mock_help_message)
    cmd_class = StartCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run([])
    captured = capsys.readouterr().out

    assert help_message_called == 1
    assert captured == "test\n"


def test_start_help(monkeypatch, new_config):
    cmd_class = StartCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "start", "help"])

    actual = cmd_class.help_message()

    assert actual == "Usage: tracker start <task>"


def test_stop(new_config):
    timer = TimerFactory.get_timer(new_config)
    StartCommand(new_config).run(["test"])
    cmd_class = StopCommand(new_config)

    cmd_class.run(["test"])

    assert "test" in timer.tasks()[1]


def test_stop_no_args(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message_called
        help_message_called += 1
        return "test"

    help_message_called = 0
    monkeypatch.setattr(StopCommand, "help_message", mock_help_message)
    cmd_class = StopCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run([])
    captured = capsys.readouterr().out

    assert help_message_called == 1
    assert captured == "test\n"


def test_stop_help(monkeypatch, new_config):
    cmd_class = StopCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "stop", "help"])

    actual = cmd_class.help_message()

    assert actual == "Usage: tracker stop <task>"


def test_tasks(new_config, capsys):
    start_cmd_class = StartCommand(new_config)
    start_cmd_class.run(["finishedTest"])
    start_cmd_class.run(["test"])
    start_cmd_class.run(["test2"])
    StopCommand(new_config).run(["finishedTest"])
    cmd_class = TasksCommand(new_config)
    _ = capsys.readouterr()

    cmd_class.run([])
    captured = capsys.readouterr().out

    assert (
        captured == "Started:\n  test\n  test2\nCompleted:\n  finishedTest\n"
    )


def test_tasks_extra_args(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message_called
        help_message_called += 1
        return "test"

    help_message_called = 0
    monkeypatch.setattr(TasksCommand, "help_message", mock_help_message)
    cmd_class = TasksCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run(["test-arg"])
    captured = capsys.readouterr().out

    assert help_message_called == 1
    assert captured == "test\n"


def test_tasks_help(monkeypatch, new_config):
    cmd_class = TasksCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "tasks", "help"])

    actual = cmd_class.help_message()

    assert actual == "Usage: tracker tasks"


def test_tasks_none(new_config, capsys):
    cmd_class = TasksCommand(new_config)

    cmd_class.run([])
    captured = capsys.readouterr().out

    assert captured == "Started:\n  <none>\nCompleted:\n  <none>\n"


def test_summary(new_config, capsys):
    start_cmd_class = StartCommand(new_config)
    start_cmd_class.run(["test"])
    start_cmd_class.run(["test2"])
    start_cmd_class.run(["something"])
    time.sleep(1)  # To prevent the total time from being 0
    StopCommand(new_config).run(["test"])
    StopCommand(new_config).run(["something"])
    cmd_class = SummaryCommand(new_config)
    _ = capsys.readouterr()

    cmd_class.run([])
    captured = capsys.readouterr().out

    assert (
        captured
        == "something:      00:00:01 (50.00%)\ntest:           00:00:01 (50.00%)\n"
    )


def test_summary_remote(new_config, capsys):
    remote_proj = Project("rem-test", new_config)
    if remote_proj.exists():
        remote_proj.delete()
    InitCommand(new_config).run(
        ["--remote=http://127.0.0.1:5000", "--user=chester_tester", "rem-test"]
    )
    remote_proj = Project("rem-test", new_config, "remote")
    StartCommand(new_config).run(["test"])
    time.sleep(1)
    StopCommand(new_config).run(["test"])
    remote_key = remote_proj.key
    remote_proj.origin = "local"
    remote_proj.delete()
    ConnectCommand(new_config).run(
        [
            "--remote=http://127.0.0.1:5000",
            "--user=person",
            f"--key={remote_key}",
        ]
    )
    new_config.current_project = Project("rem-test", new_config, "remote")
    StartCommand(new_config).run(["test"])
    time.sleep(1)
    StopCommand(new_config).run(["test"])
    cmd_class = SummaryCommand(new_config)
    _ = capsys.readouterr()

    cmd_class.run([])
    captured = capsys.readouterr().out

    assert re.match(
        r"test: {11}(\d{2}:){2}\d{2} \(\s?\d{2,3}\.\d{2}%\)\n", captured
    )


## To be addressed later
# def test_summary_zero_time(new_config, capsys):
#     start_cmd_class = StartCommand(new_config)
#     start_cmd_class.run(["test"])
#     start_cmd_class.run(["test2"])
#     StopCommand(new_config).run(["test"])
#     cmd_class = SummaryCommand(new_config)
#     _ = capsys.readouterr()

#     cmd_class.run([])
#     captured = capsys.readouterr().out

#     assert (
#         captured
#         == "test:             0 days,   0 hours,   0 minutes,   0 seconds (___.__%)\n"
#     )


def test_summary_extra_args(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message_called
        help_message_called += 1
        return "test"

    help_message_called = 0
    monkeypatch.setattr(SummaryCommand, "help_message", mock_help_message)
    cmd_class = SummaryCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run(["test-arg"])
    captured = capsys.readouterr().out

    assert help_message_called == 1
    assert captured == "test\n"


def test_summary_help(monkeypatch, new_config):
    cmd_class = SummaryCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "summary", "help"])

    actual = cmd_class.help_message()

    assert actual == "Usage: tracker summary"


def test_detail(new_config, capsys):
    InitCommand(new_config).run(["testing"])
    new_config.current_project
    StartCommand(new_config).run(["test"])
    time.sleep(1)
    StopCommand(new_config).run(["test"])
    StartCommand(new_config).run(["test"])
    time.sleep(1)
    StopCommand(new_config).run(["test"])
    cmd_class = DetailsCommand(new_config)
    _ = capsys.readouterr()

    cmd_class.run([])
    captured = capsys.readouterr().out

    assert captured == "test:    00:00:02  (100%)\n    00:00:02\n"


def test_detail_remote(new_config, capsys):
    InitCommand(new_config).run(
        ["--remote=http://127.0.0.1:5000", "--user=chester_tester", "rem-test"]
    )
    remote_proj = Project("rem-test", new_config, "remote")
    StartCommand(new_config).run(["test"])
    StopCommand(new_config).run(["test"])
    remote_key = remote_proj.key
    remote_proj.origin = "local"
    remote_proj.delete()
    ConnectCommand(new_config).run(
        [
            "--remote=http://127.0.0.1:5000",
            "--user=person",
            f"--key={remote_key}",
        ]
    )
    new_config.current_project = Project("rem-test", new_config, "remote")
    StartCommand(new_config).run(["test"])
    StopCommand(new_config).run(["test"])
    cmd_class = DetailsCommand(new_config)
    _ = capsys.readouterr().out

    cmd_class.run([])
    captured = capsys.readouterr().out

    assert re.match(
        r"test: {13}(\d{2}:){2}\d{2}  \(\s?\d{2,3}%\)\n  chester_tester  (\d{2}:){2}\d{2}\n  person {10}(\d{2}:){2}\d{2}",
        captured,
    )


def test_detail_help(monkeypatch, new_config):
    cmd_class = DetailsCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "detail", "help"])

    actual = cmd_class.help_message()

    assert actual == "Usage: tracker details"


def test_init(new_config):
    cmd_class = InitCommand(new_config)

    cmd_class.run(["test"])
    projects = new_config.get_project_names()

    assert "test" in projects


def test_init_remote(new_config):
    cmd_class = InitCommand(new_config)

    cmd_class.run(
        ["--remote=http://127.0.0.1:5000", "--user=testUsername", "test"]
    )
    projects = new_config.get_project_names()

    assert "test" in projects


def test_init_remote_no_name(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message_called
        help_message_called += 1
        return "test"

    help_message_called = 0
    monkeypatch.setattr(InitCommand, "help_message", mock_help_message)
    cmd_class = InitCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run(
            ["--remote=http://127.0.0.1:5000", "--user=testUsername"]
        )
    captured = capsys.readouterr().out

    assert captured == "test\n"
    assert help_message_called == 1


def test_init_already_exists(new_config, monkeypatch, capsys):
    last_prompt = ""

    def mock_input(prompt):
        nonlocal last_prompt
        last_prompt = prompt
        return "y"

    monkeypatch.setattr("builtins.input", mock_input)
    cmd_class = InitCommand(new_config)
    cmd_class.run(["test"])
    _ = capsys.readouterr()

    cmd_class.run(["test"])
    captured = capsys.readouterr().out

    assert last_prompt == 'Overwrite "test" (y/n)? '
    assert captured == '"test" initialized.\n'
    assert "test" in new_config.get_project_names()


def test_init_already_exists_abort(new_config, monkeypatch, capsys):
    def mock_input(prompt):
        nonlocal last_prompt
        last_prompt = prompt
        return "n"

    last_prompt = ""
    monkeypatch.setattr("builtins.input", mock_input)
    cmd_class = InitCommand(new_config)
    cmd_class.run(["test"])

    cmd_class.run(["test"])

    assert last_prompt == 'Overwrite "test" (y/n)? '
    assert "test" in new_config.get_project_names()


def test_init_extra_args(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message_called
        help_message_called += 1
        return "test"

    help_message_called = 0
    monkeypatch.setattr(InitCommand, "help_message", mock_help_message)
    cmd_class = InitCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run(["test-proj", "extra-arg"])
    captured = capsys.readouterr().out

    assert help_message_called == 1
    assert captured == "test\n"


def test_init_help(monkeypatch, new_config):
    cmd_class = InitCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "init", "help"])

    actual = cmd_class.help_message()

    assert (
        actual
        == 'Usage: tracker init [[--remote=<url> --user=<username> <project_name>] | <project_name>]\nIf <project_name> is excluded, it will be inferred as "default"'
    )


def test_switch(new_config, capsys):
    cmd_class = InitCommand(new_config)
    cmd_class.run(["test"])
    cmd_class.run(["test2"])
    cmd_class = SwitchCommand(new_config)
    _ = capsys.readouterr()

    cmd_class.run(["test"])
    captured = capsys.readouterr().out

    assert new_config.current_project.name == "test"
    assert captured == 'Switched to "test".\n'


def test_switch_nonexistent(new_config, monkeypatch):
    def mock_input(prompt):
        nonlocal last_prompt
        last_prompt = prompt
        return "y"

    last_prompt = ""
    monkeypatch.setattr("builtins.input", mock_input)
    cmd_class = SwitchCommand(new_config)

    cmd_class.run(["test"])
    projects = new_config.get_project_names()

    assert last_prompt == "Do you wish to create this project (y/n)? "
    assert "test" in projects
    assert new_config.current_project.name == "test"


def test_switch_nonexistent_abort(new_config, capsys, monkeypatch):
    def mock_input(prompt):
        nonlocal last_prompt
        last_prompt = prompt
        return "n"

    last_prompt = ""
    expected_project = new_config.current_project.name
    monkeypatch.setattr("builtins.input", mock_input)
    cmd_class = SwitchCommand(new_config)

    cmd_class.run(["test"])
    projects = new_config.get_project_names()
    captured = capsys.readouterr().out

    assert last_prompt == "Do you wish to create this project (y/n)? "
    assert "test" not in projects
    assert new_config.current_project.name == expected_project
    assert captured == 'No such project "test".\nAborting switch...\n'


def test_switch_no_args(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message_called
        help_message_called += 1
        return "test"

    help_message_called = 0
    monkeypatch.setattr(SwitchCommand, "help_message", mock_help_message)
    cmd_class = SwitchCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run([])
    captured = capsys.readouterr().out

    assert help_message_called == 1
    assert captured == "test\n"


def test_switch_help(monkeypatch, new_config):
    cmd_class = SwitchCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "switch", "help"])

    actual = cmd_class.help_message()

    assert actual == "Usage: tracker switch <project_name>"


def test_projects(new_config, capsys):
    InitCommand(new_config).run(["test"])
    InitCommand(new_config).run(
        ["--remote=http://127.0.0.1:5000", "--user=chester_tester", "short"]
    )
    InitCommand(new_config).run(
        [
            "--remote=http://127.0.0.1:5000",
            "--user=chester_tester",
            "testremote",
        ]
    )
    time.sleep(1)
    cmd_class = ProjectsCommand(new_config)
    _ = capsys.readouterr()

    cmd_class.run([])
    captured = capsys.readouterr().out

    assert (
        captured
        == "default\nshort          (remote)\ntest\n* testremote   (remote)\n"
    )


def test_projects_extra_args(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message_called
        help_message_called += 1
        return "test"

    help_message_called = 0
    monkeypatch.setattr(ProjectsCommand, "help_message", mock_help_message)
    cmd_class = ProjectsCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run(["test-arg"])
    captured = capsys.readouterr().out

    assert help_message_called == 1
    assert captured == "test\n"


def test_projects_help(monkeypatch, new_config):
    cmd_class = ProjectsCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "projects", "help"])

    actual = cmd_class.help_message()

    assert actual == "Usage: tracker projects"


def test_delete(new_config, capsys):
    InitCommand(new_config).run(["test"])
    cmd_class = DeleteCommand(new_config)
    _ = capsys.readouterr()

    cmd_class.run(["test"])
    captured = capsys.readouterr().out
    projects = new_config.get_project_names()

    assert captured == 'Deleted.\nSetting current project to "default".\n'
    assert "test" not in projects


def test_delete_no_args(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message_called
        help_message_called += 1
        return "test"

    help_message_called = 0
    monkeypatch.setattr(DeleteCommand, "help_message", mock_help_message)
    cmd_class = DeleteCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run([])
    captured = capsys.readouterr().out

    assert help_message_called == 1
    assert captured == "test\n"


def test_delete_help(monkeypatch, new_config):
    cmd_class = DeleteCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "delete", "help"])

    actual = cmd_class.help_message()

    assert actual == "Usage: tracker delete <project_name>"


def test_delete_nonexistent(new_config, capsys):
    cmd_class = DeleteCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run(["test"])
    captured = capsys.readouterr().out

    assert captured == 'Cannot delete. No such project "test".\n'


def test_delete_default(new_config, capsys):
    InitCommand(new_config).run(["test"])
    cmd_class = DeleteCommand(new_config)
    _ = capsys.readouterr()

    cmd_class.run(["default"])
    captured = capsys.readouterr().out.split("\n")
    projects = new_config.get_project_names()

    assert captured[0] == "Deleted."
    assert captured[1] == 'Re-creating "default".'
    assert "default" in projects


def test_cli_run(monkeypatch, new_config):
    def mock_run(self, args):
        nonlocal run_args, run_called
        run_args = args
        run_called += 1

    run_args = []
    run_called = 0
    cli = CLI()
    cli.config = new_config  # Should be unnecessary
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "init", "test"])
    monkeypatch.setattr(InitCommand, "run", mock_run)

    cli.run()

    assert run_args == ["test"]
    assert run_called == 1


def test_cli_run_command_exception(monkeypatch, new_config, capsys):
    def mock_run(self, args):
        raise CommandException("test")

    cli = CLI()
    cli.config = new_config  # Should be unnecessary
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "init", "test"])
    monkeypatch.setattr(InitCommand, "run", mock_run)

    cli.run()
    captured = capsys.readouterr().out.split("\n")

    assert captured[0] == "ERROR: test"
    assert captured[2] == "Usage: tracker <subcommand>"


def test_cli_run_timer_exception(monkeypatch, new_config, capsys):
    def mock_run(self, args):
        raise TimerException("test")

    cli = CLI()
    cli.config = new_config  # Should be unnecessary
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "init", "test"])
    monkeypatch.setattr(InitCommand, "run", mock_run)

    cli.run()
    captured = capsys.readouterr().out

    assert captured == "ERROR: test\n"


def test_cli_run_help(monkeypatch, new_config):
    def mock_print_usage(self):
        nonlocal print_usage_called
        print_usage_called += 1

    print_usage_called = 0
    cli = CLI()
    cli.config = new_config  # Should be unnecessary
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "help"])
    monkeypatch.setattr(CLI, "print_usage", mock_print_usage)

    cli.run()

    assert print_usage_called == 1


def test_cli_run_help_subcommand(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message
        help_message += 1
        return "test"

    help_message = 0
    cli = CLI()
    cli.config = new_config  # Should be unnecessary_config
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "help", "init"])
    monkeypatch.setattr(InitCommand, "help_message", mock_help_message)

    cli.run()
    captured = capsys.readouterr().out

    assert help_message == 1
    assert captured == "test\n"


def test_cli_run_no_args(monkeypatch, new_config):
    def mock_print_usage(self):
        nonlocal print_usage_called
        print_usage_called += 1

    print_usage_called = 0
    cli = CLI()
    cli.config = new_config
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker"])
    monkeypatch.setattr(CLI, "print_usage", mock_print_usage)

    cli.run()

    assert print_usage_called == 1


def test_show_local(new_config, capsys):
    cmd_class = ShowCommand(new_config)
    _ = capsys.readouterr()

    cmd_class.run([])
    captured = capsys.readouterr().out

    assert captured == "default\n"


def test_show_remote(new_remote_config, capsys):
    cmd_class = ShowCommand(new_remote_config)
    _ = capsys.readouterr()

    cmd_class.run([])
    captured = capsys.readouterr().out

    assert (
        captured
        == "test\nKey:  eyJwcm9qZWN0IjoidGVzdCIsInVzZXJuYW1lIjoidGVzdGVyX2NoZXN0ZXIifQ.QmXNs5J8NvOUpt7dNVx9ZSO_2bQ\nUser: tester_chester\n"
    )


def test_show_extra_args(monkeypatch, new_config, capsys):
    def mock_help_message(self):
        nonlocal help_message_called
        help_message_called += 1
        return "test"

    help_message_called = 0
    monkeypatch.setattr(ShowCommand, "help_message", mock_help_message)
    cmd_class = ShowCommand(new_config)

    with pytest.raises(SystemExit):
        cmd_class.run(["test-arg"])
    captured = capsys.readouterr().out

    assert help_message_called == 1
    assert captured == "test\n"


def test_show_help(monkeypatch, new_config):
    cmd_class = ShowCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "show", "help"])

    actual = cmd_class.help_message()

    assert actual == "Usage: tracker show"


def test_connect(new_config):
    InitCommand(new_config).run(
        ["--remote=http://127.0.0.1:5000", "--user=chester_tester", "rem-test"]
    )
    remote_proj = Project("rem-test", new_config, "remote")
    remote_key = remote_proj.key
    remote_proj.origin = "local"
    remote_proj.delete()
    cmd_class = ConnectCommand(new_config)

    cmd_class.run(
        [
            "--remote=http://127.0.0.1:5000",
            "--user=person",
            f"--key={remote_key}",
        ]
    )
    connected_proj = Project("rem-test", new_config, "remote")

    assert connected_proj.name == "rem-test"
    assert connected_proj.exists()
    assert connected_proj.key == remote_key
    assert connected_proj.user == "person"


def test_connect_help(monkeypatch, new_config):
    cmd_class = ConnectCommand(new_config)
    # Mock tracker.cli.argv instead of sys.argv because argv has been imported
    monkeypatch.setattr("tracker.cli.argv", ["tracker", "connect", "help"])

    actual = cmd_class.help_message()

    assert (
        actual
        == "Usage: tracker connect --remote=<url> --user=<username> --key=<key>"
    )


def test_backup(new_config):
    backup_command = BackupCommand(new_config)
    StartCommand(new_config).run(["test1"])
    time.sleep(1)
    StopCommand(new_config).run(["test1"])

    currTime = time.strftime("%Y%m%d%H%M")
    backup_command.run([])
    expectedFileName = (
        new_config.base_path / "backup" / f"tracker-{currTime}.zip"
    )
    exists = expectedFileName.exists()

    assert exists


def test_double_backup(new_config):
    backup_command = BackupCommand(new_config)
    StartCommand(new_config).run(["test1"])
    time.sleep(1)
    StopCommand(new_config).run(["test1"])

    currTime = time.strftime("%Y%m%d%H%M")
    backup_command.run([])
    backup_command.run([])
    expectedFileName0 = (
        new_config.base_path / "backup" / f"tracker-{currTime}.zip"
    )
    exists0 = expectedFileName0.exists()
    expectedFileName1 = (
        new_config.base_path / "backup" / f"tracker-{currTime}-1.zip"
    )
    exists1 = expectedFileName1.exists()

    assert exists0
    assert exists1


def test_restore(new_config):
    backup_command = BackupCommand(new_config)
    restore_command = RestoreCommand(new_config)
    StartCommand(new_config).run(["test1"])
    time.sleep(1)
    StopCommand(new_config).run(["test1"])
    backup_command.run([])
    StartCommand(new_config).run(["test2"])

    restore_command.run([])
    timer = TimerFactory.get_timer(new_config)
    tasks = timer.tasks()[0]

    assert "test2" not in tasks
