""" Command Line Interface (CLI) module, handles 
    user commands.
"""

from sys import argv
import sys
import os
import time
import shutil
import pathlib
from zipfile import ZipFile
from abc import ABC, abstractmethod
from tracker.config import Config, Project, ConfigException
from tracker.timer import TimerException, TimerFactory


commands = [
    "delete",
    "help",
    "init",
    "projects",
    "start",
    "stop",
    "summary",
    "switch",
    "tasks",
    "show",
    "details",
    "connect",
    "restore",
    "backup",
]


class CommandException(Exception):
    """Basic Command Line Exception"""

    # pass


class Command(ABC):
    """Abstract Base Class all commands follow."""

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def run(self, args: list[str]) -> None:
        """The logic for running a command class"""
        # pass

    @abstractmethod
    def help_message(self) -> str:
        """A useful help message for each command class"""
        # pass


class StartCommand(Command):
    """Handles the running for 'start'"""

    def run(self, args: list[str]) -> None:
        if len(args) != 1:
            print(self.help_message())
            sys.exit(1)

        timer = TimerFactory.get_timer(self.config)
        task = args[0]
        timer.start(task)
        print(f'"{task}" started.')

    def help_message(self) -> str:
        return f"""Usage: {os.path.basename(argv[0])} start <task>"""


class StopCommand(Command):
    """Handles the running for 'stop'"""

    def run(self, args: list[str]) -> None:
        if len(args) != 1:
            print(self.help_message())
            sys.exit(1)

        timer = TimerFactory.get_timer(self.config)
        task = args[0]
        timer.stop(task)
        print(f'"{task}" stopped.')

    def help_message(self) -> str:
        return f"""Usage: {os.path.basename(argv[0])} stop <task>"""


class TasksCommand(Command):
    """Handles the running for 'tasks'"""

    def run(self, args: list[str]) -> None:
        if len(args) != 0:
            print(self.help_message())
            sys.exit(1)

        timer = TimerFactory.get_timer(self.config)
        running_tasks, completed_tasks = timer.tasks()
        print("Started:")
        if running_tasks:
            for task in running_tasks:
                print("  " + task)
        else:
            print("  <none>")
        print("Completed:")
        if completed_tasks:
            for task in completed_tasks:
                print("  " + task)
        else:
            print("  <none>")

    def help_message(self) -> str:
        return f"""Usage: {os.path.basename(argv[0])} tasks"""


class SummaryCommand(Command):
    """Handles the running for 'summary'"""

    def run(self, args: list[str]) -> None:
        if len(args) != 0:
            print(self.help_message())
            sys.exit(1)

        timer = TimerFactory.get_timer(self.config)
        summary = timer.summary()
        total_time = sum(summary[task]["time"] for task in summary)
        if not total_time:
            print("No time tracked yet.")
            return

        for task in summary:
            task_time = summary[task]["time"]
            print(
                f"{task+':':15} "
                f"{summary[task]['hours']:02}:"
                f"{summary[task]['minutes']:02}:"
                f"{summary[task]['seconds']:02} "
                f"({task_time*100.0/total_time:.2f}%)"
            )

    def help_message(self) -> str:
        return f"""Usage: {os.path.basename(argv[0])} summary"""


class ShowCommand(Command):
    """Handles the running for 'show'"""

    def run(self, args: list[str]) -> None:
        if len(args) > 0:
            print(self.help_message())
            sys.exit(1)
        # Get list of projects and display them with current project starred
        name = self.config.current_project.name
        print(name)
        if self.config.current_project.origin == "remote":
            print(f"Key:  {self.config.current_project.key}")
            print(f"User: {self.config.current_project.user}")

    def help_message(self) -> str:
        return f"""Usage: {os.path.basename(argv[0])} show"""


class InitCommand(Command):
    """init <project_name>
    project_name is optional (if no project_name, "default" is used)
    """

    def run(self, args: list[str]) -> None:
        if len(args) not in (0, 1, 3):
            print(self.help_message())
            sys.exit(1)
        if len(args) > 1 and (
            not args[0].startswith("--remote=")
            or not args[1].startswith("--user=")
            or len(args[0]) < 10
            or len(args[1]) < 8
        ):
            print(self.help_message())
            sys.exit(1)

        match (len(args)):
            case 0:
                project_name = "default"
            case 1:
                project_name = args[0]
            case 3:
                project_name = args[2]
        project = (
            Project(project_name, self.config)
            if len(args) != 3
            else Project(
                project_name,
                self.config,
                origin="remote",
                url=args[0][9:],
                user=args[1][7:],
            )
        )
        if project.exists():
            if "y" != input(f'Overwrite "{project_name}" (y/n)? ').lower():
                return
            del_proj = Project(project_name, self.config)
            del_proj.delete()

        project.create()
        self.config.set_project(project)

        print(f'"{project_name}" initialized.')

    def help_message(self) -> str:
        path = os.path.basename(argv[0])
        return (
            f"Usage: {path} init [[--remote=<url> --user=<username> <project_name>]"
            " | <project_name>]"
            '\nIf <project_name> is excluded, it will be inferred as "default"'
        )


class SwitchCommand(Command):
    """Handles the running for 'switch'"""

    def run(self, args: list[str]) -> None:
        if len(args) != 1:
            print(self.help_message())
            sys.exit(1)

        project_name = args[0]
        project = Project(project_name, self.config)
        if not project.exists():
            print(f'No such project "{project_name}".')
            if (
                "y"
                == input("Do you wish to create this project (y/n)? ").lower()
            ):
                project.create()
            else:
                print("Aborting switch...")
                return

        self.config.set_project(project)
        print(f'Switched to "{project_name}".')

    def help_message(self) -> str:
        return f"""Usage: {os.path.basename(argv[0])} switch <project_name>"""


class ProjectsCommand(Command):
    """Handles the running for 'projects'"""

    def run(self, args: list[str]) -> None:
        if len(args) > 0:
            print(self.help_message())
            sys.exit(1)

        # Stores length of longest project name, names of remote projects and creates new empty list
        length = max(len(name) for name in self.config.get_project_names()) + 2
        remotes = self.config.get_remote_project_names()
        proj_names = []

        # Get list of projs and display them with current project starred and remote projects marked
        for name in self.config.get_project_names():
            mod_name = name
            if name == self.config.current_project.name:
                mod_name = "* " + name
            if name in remotes:
                proj_names.append(
                    mod_name + (length - len(mod_name)) * " " + "   (remote)"
                )
            else:
                proj_names.append(mod_name)

        for name in proj_names:
            print(name)

    def help_message(self) -> str:
        return f"""Usage: {os.path.basename(argv[0])} projects"""


class DeleteCommand(Command):
    """Handles the running for 'delete'"""

    def run(self, args: list[str]) -> None:
        if len(args) != 1:
            print(self.help_message())
            sys.exit(1)

        project = Project(args[0], self.config)
        if not project.exists():
            print(f'Cannot delete. No such project "{project.name}".')
            sys.exit(1)
        else:
            deleting_current = project.name == self.config.current_project.name
            project.delete()
            print("Deleted.")

            # There must always be a default.
            if project.name == "default":
                print('Re-creating "default".')
                project.create()

            if deleting_current:
                self.config.set_project(Project("default", self.config))
                print('Setting current project to "default".')

    def help_message(self) -> str:
        return f"""Usage: {os.path.basename(argv[0])} delete <project_name>"""


class DetailsCommand(Command):
    """Handles the running for 'details'"""

    def run(self, args: list[str]) -> None:
        if len(args) != 0:
            print(self.help_message())
            sys.exit(1)

        details = TimerFactory.get_timer(self.config).details()
        total_time = sum(time for task in details for time, _ in details[task])
        col1_size = max(
            len(user) for task in details for _, user in details[task]
        )

        for task, timings in details.items():
            task_time = 0.0
            entries: dict[str, float] = {}
            for entry in timings:
                duration, user = entry
                entries[user] = entries.get(user, 0) + duration
                task_time += duration
            task_percent = task_time * 100.0 / total_time
            time_task = time.strftime("%H:%M:%S", time.gmtime(task_time))
            print(
                f"{task+':':{col1_size}}    {time_task}  ({task_percent:2.0f}%)"
            )
            for user, duration in entries.items():
                time_dur = time.strftime("%H:%M:%S", time.gmtime(duration))
                print(f"  {user:{col1_size}}  {time_dur}")

    def help_message(self) -> str:
        return f"""Usage: {os.path.basename(argv[0])} details"""


class ConnectCommand(Command):
    """Connects to an existing remote project"""

    def run(self, args: list[str]) -> None:
        if (
            len(args) != 3
            or not args[0].startswith("--remote=")
            or not args[1].startswith("--user=")
            or not args[2].startswith("--key=")
        ):
            print(self.help_message())
            sys.exit(1)
        url = args[0][9:]
        user = args[1][7:]
        key = args[2][6:]
        print(f"Connecting to remote project at {url}...")
        while True:
            try:
                project = Project.connect(self.config, url, user, key)
                break
            except FileExistsError as err:
                print(f'Project "{err.args[0]}" already exists.')
                if "y" != input(f'Overwrite "{err.args[0]}" (y/n)? ').lower():
                    return
                Project(err.args[0], self.config).delete()
        print(f"Connected to remote project {project.name}@{url} as {user}.")
        self.config.set_project(project)

    def help_message(self) -> str:
        path = os.path.basename(argv[0])
        return f"Usage: {path} connect --remote=<url> --user=<username> --key=<key>"


class RestoreCommand(Command):
    """Reads from a backup zip file and restores information"""

    def run(self, args: list[str]) -> None:
        backup_directory_path = self.config.base_path / "backup/"

        if not (backup_directory_path).exists():
            raise CommandException(
                "Backup directory does not exist. Please backup first before restoring."
            )

        print("Restoring...")
        backup_directory_file = os.listdir(backup_directory_path)

        if not backup_directory_file:
            print("There are currently no backup files")
            return

        extraction_path = self.config.base_path

        for direct in os.listdir(extraction_path):
            path = os.path.join(extraction_path, direct)

            if direct == "backup":
                pass
            elif direct == "config":
                os.remove(path)
            else:
                shutil.rmtree(path)

        restore_path = os.path.join(
            backup_directory_path, max(backup_directory_file)
        )

        ZipFile(restore_path, "r").extractall(extraction_path)

        print("Restore successful")

    def help_message(self) -> str:
        return "Usage: restore <There must be backup files present>"


class BackupCommand(Command):
    """Backup all local projects"""

    def run(self, args: list[str]) -> None:
        def add_files(zipf, path, root):
            for file in path.iterdir():
                zipf.write(file, arcname=file.relative_to(root))
                if file.is_dir():
                    add_files(zipf, file, root)

        if len(args) != 0:
            print(self.help_message())
            sys.exit(1)
        base_path = self.config.base_path
        backup_path = base_path / "backup"

        if not (backup_path).exists():
            backup_path.mkdir()
        filename = f"tracker-{time.strftime('%Y%m%d%H%M')}"
        version = 0
        version_suffix = ""
        while True:
            new_filename = filename + version_suffix + ".zip"
            if not (backup_path / new_filename).exists():
                filename = new_filename
                break
            version += 1
            version_suffix = f"-{version}"
        with ZipFile(backup_path / filename, "w") as zipf:
            add_files(zipf, base_path / "projects", base_path)
            zipf.write(base_path / "config", arcname="config")
        print(f"Backup created at {backup_path / filename}")

    def help_message(self) -> str:
        path = os.path.basename(argv[0])
        return f"Usage: {path} backup"


class CLI:
    """Command Line Interface class"""

    def __init__(self):
        self.config = Config()

    def print_usage(self):
        """Prints how a command is used"""
        print(f"Usage: {os.path.basename(argv[0])} <subcommand>")
        print("  where <subcommand> is one of:")
        for cmd in commands:
            print(f"\t{cmd}")

    def run(self):
        """Runs the command"""
        if len(argv) == 1 or argv[1] not in commands:
            self.print_usage()
        elif len(argv) == 2 and argv[1] == "help":
            self.print_usage()
        elif argv[1] == "help":
            subcommandclass = eval(argv[2].capitalize() + "Command")
            print(subcommandclass(self.config).help_message())
        else:
            command = argv[1]
            commandclass = eval(command.capitalize() + "Command")
            try:
                commandclass(self.config).run(argv[2:])
            except CommandException as comm:
                print(f"ERROR: {comm}")
                print()
                self.print_usage()
            except TimerException as tim:
                print(f"ERROR: {tim}")
            except ConfigException as conf:
                print(f"ERROR: {conf}")
            except:
                print("ERROR: Unknown error occurred.")
                print(
                    "We can only explain it to you, we can't understand it for you."
                )
                print()
                self.print_usage()
