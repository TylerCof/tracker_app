"""Timer module file, determines whether or not a project is to be run as remote or local"""

import time
from abc import abstractmethod, ABC
from datetime import timedelta
import requests
from tracker.config import Config, Project


def contains_invalid_char(task_name):
    """Determines whether a character is illegal"""
    for char in task_name:
        if not char.isalnum():
            return True
    return False


class TimerException(Exception):
    """General Timer Exception"""


class BadLabelException(TimerException):
    """You put in an illegal character"""


class NoStartException(TimerException):
    """Can't stop what ya didn't start"""


class DupStartException(TimerException):
    """You already started that...moron"""


# Can be local or remote
class AbstractTimer(ABC):
    """Abstract Base Timer Class"""

    def __init__(self, project: Project):
        self.project = project

    @abstractmethod
    def start(self, task: str):
        """Abstract Start"""

    @abstractmethod
    def stop(self, task: str):
        """Abstract stop"""

    @abstractmethod
    def tasks(self) -> tuple[list[str], list[str]]:
        """Abstract Tasks"""

    @abstractmethod
    def summary(self) -> dict[str, dict[str, float]]:
        """Abstract Summary"""

    @abstractmethod
    def details(self) -> dict[str, list[tuple[float, str]]]:
        """Gets the timings and associated user for each task"""


class LocalTimer(AbstractTimer):
    """Local yokel timer"""

    def start(self, task: str):
        """Local start"""
        if contains_invalid_char(task):
            raise BadLabelException("Illegal character in task name.")

        active_path = self.project.active_timers_path / (task + ".txt")
        if active_path.exists():
            if not self.project.user:
                raise DupStartException(f'"{task}" already started.')
            with open(active_path, "r") as fptr:
                users = (
                    line.strip().split(";")[1] for line in fptr.readlines()
                )
                if self.project.user in users:
                    raise DupStartException(
                        f'"{task}" already started by user "{self.project.user}".'
                    )
        user = "" if not self.project.user else ";" + self.project.user
        with open(active_path, "a", encoding="utf-8") as wfile:
            wfile.write(f"{time.time()}{user}\n")

    def stop(self, task: str):
        """Local stop"""
        if contains_invalid_char(task):
            raise BadLabelException("Illegal character in task name.")

        active_path = self.project.active_timers_path / (task + ".txt")
        if not active_path.exists():
            raise NoStartException(f'"{task}" was never started.')

        with open(active_path, "r", encoding="utf-8") as rfile:
            if self.project.user:  # self is a remote-hosted local timer
                for line in rfile.read().splitlines():
                    timestamp, user_name = line.split(";")
                    if user_name == self.project.user:
                        start_time = float(timestamp)
                        break
                if not start_time:
                    raise NoStartException(
                        f'"{task}" was never started by user "{self.project.user}".'
                    )
            else:  # self is a pure local timer
                start_time = float(rfile.read().rstrip())
        end_time = time.time()

        user = "" if not self.project.user else ";" + self.project.user
        finished_path = self.project.finished_timers_path / (task + ".txt")
        with open(finished_path, "a", encoding="utf-8") as wfile:
            wfile.write(
                f"{start_time}:{end_time}:{end_time - start_time}{user}\n"
            )

        active_path.unlink()

    def tasks(self) -> tuple[list[str], list[str]]:
        """Local tasks"""
        active_path = self.project.active_timers_path
        finished_path = self.project.finished_timers_path
        return (
            sorted([path.stem for path in active_path.iterdir()]),
            sorted([path.stem for path in finished_path.iterdir()]),
        )

    def summary(self) -> dict[str, dict[str, float]]:
        """Local summary"""
        summary_dict = {}
        finished_path = self.project.finished_timers_path
        for task_file in finished_path.iterdir():
            task_name = task_file.stem
            with open(task_file, encoding="utf-8") as fptr:
                task_total_secs = sum(
                    int(float(line.rstrip().split(";")[0].split(":")[2]))
                    for line in fptr
                )
            hrs, mins, secs = self._hrs_mins_secs(task_total_secs)

            summary_dict[task_name] = {
                "hours": hrs,
                "minutes": mins,
                "seconds": secs,
                "time": task_total_secs,
            }

        return summary_dict

    def _hrs_mins_secs(self, total_secs):
        """Easy time-formatting"""
        # timedelta format is either of the form '1 day, 0:02:00' or '1:00:00'
        # depending if there are enough seconds for whole days.
        output = str(timedelta(seconds=total_secs))
        days = 0
        if ", " in output:
            days = int(output[: output.find(" ")])
            output = output[output.find(", ") + 2 :]
        hrs, mins, secs = list(map(int, output.split(":")))
        hrs += days * 24
        return hrs, mins, secs

    def details(self) -> dict[str, list[tuple[float, str]]]:
        details_dict = {}
        finished_path = self.project.finished_timers_path
        for task_file in finished_path.iterdir():
            task_name = task_file.stem
            with open(task_file, encoding="utf-8") as fptr:
                task_details = []
                for line in fptr:
                    data = line.rstrip().split(";")
                    time_range, user = (
                        data[0],
                        data[1] if len(data) > 1 else "",
                    )
                    _, _, duration = time_range.split(":")
                    task_details.append((float(duration), user))
            details_dict[task_name] = task_details
        return details_dict


class RemoteTimer(AbstractTimer):
    """Server-based remote timer."""

    def start(self, task: str) -> None:
        """Remote start"""
        print(self.project.path)
        with open(
            str(self.project.path) + "/remote", "r", encoding="utf-8"
        ) as rfile:
            params = rfile.readlines()
            url = params[0][4:] + "/api/start"
            # username = params[1][9:]
            key = params[1][4:].strip()
            payload = {"label": task, "user": self.project.user}
            auth = requests.auth.HTTPBasicAuth(key, "")
        try:
            response = requests.post(url, auth=auth, data=payload, timeout=3)
        except requests.exceptions.ConnectionError:
            raise TimerException("Could not connect to remote server.")
        if not response.ok:
            raise TimerException("A request to the remote server failed.")
        if response.json()["result"] == "error":
            raise TimerException(response.json()["type"])

    def stop(self, task: str) -> None:
        """remote stop"""
        print(self.project.path)
        with open(
            str(self.project.path) + "/remote", "r", encoding="utf-8"
        ) as rfile:
            params = rfile.readlines()
            url = params[0][4:] + "/api/stop"
            key = params[1][4:].strip()
            payload = {"label": task, "user": self.project.user}
            auth = requests.auth.HTTPBasicAuth(key, "")
            try:
                response = requests.post(
                    url, auth=auth, data=payload, timeout=3
                )
            except requests.exceptions.ConnectionError:
                raise TimerException("Could not connect to remote server.")
        if not response.ok:
            raise TimerException("A request to the remote server failed.")
        if response.json()["result"] == "error":
            raise TimerException(response.json()["type"])

    def tasks(self) -> tuple[list[str], list[str]]:
        """Remote tasks"""
        with open(
            str(self.project.path) + "/remote", "r", encoding="utf-8"
        ) as rfile:
            params = rfile.readlines()
            url = params[0][4:].strip() + "/api/tasks"
            key = params[1][4:].strip()
            auth = requests.auth.HTTPBasicAuth(key, "")
        try:
            response = requests.get(url, auth=auth, timeout=3)
        except requests.exceptions.ConnectionError:
            raise TimerException("Could not connect to remote server.")
        if not response.ok:
            raise Exception("A request to the remote server failed.")
        json = response.json()
        if json["result"] == "error":
            raise Exception(
                f"A request to the remote server failed with error: {json['type']}"
            )
        return json["active"], json["finished"]

    def summary(self) -> dict[str, dict[str, float]]:
        timings = self.details()
        summary = {}
        for task in timings:
            total_time = sum(time for time, _ in timings[task])
            time_str = time.strftime("%H:%M:%S", time.gmtime(total_time))
            hrs, mins, secs = (int(x) for x in time_str.split(":"))
            summary[task] = {
                "hours": hrs,
                "minutes": mins,
                "seconds": secs,
                "time": total_time,
            }
        return summary

    def details(self) -> dict[str, list[tuple[float, str]]]:
        key = self.project.key
        remote = self.project.url
        auth = requests.auth.HTTPBasicAuth(key, "")

        try:
            response = requests.get(
                str(remote) + "/api/times", auth=auth, timeout=3
            )
        except requests.exceptions.ConnectionError:
            raise TimerException("Could not connect to remote server.")

        if not response.ok:
            raise TimerException("A request to the remote server failed.")
        json = response.json()
        if json["result"] == "error":
            raise TimerException(
                f"A request to the remote server failed with error: {json['type']}"
            )
        return json["timings"]


class TimerFactory:
    """Timer config set"""

    @staticmethod
    def get_timer(config: Config) -> AbstractTimer:
        """Get's the timer config"""
        if config.current_project.origin == "local":
            return LocalTimer(config.current_project)
        if config.current_project.origin == "remote":
            return RemoteTimer(config.current_project)
        raise TimerException("Invalid project origin.")

    def useless_method(self):
        """This method is needed for pylint conformation... for some reason"""
