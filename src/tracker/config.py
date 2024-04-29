"""Configuration module. Configures the configuration of a project that has been configured"""

from __future__ import annotations
from pathlib import Path
import shutil
import requests
import os
from requests.auth import HTTPBasicAuth

default_tracker_path = Path.home() / ".tracker"


class ConfigException(Exception):
    """Config Exception Class"""


class Config:
    """Tracks which project is active, and maybe some identity stuff."""

    def __init__(self, base_path: Path = default_tracker_path):
        self.base_path = base_path
        self.project_name = self._determine_project(base_path)
        self.current_project = Project(self.project_name, self)

        if not self.current_project.exists():
            self.current_project.create()

    def _determine_project(self, base_path: Path) -> str:
        """Determines the project"""
        if not base_path.exists():
            base_path.mkdir()

        config_file_path = base_path / "config"
        try:
            with open(config_file_path, encoding="utf-8") as rfile:
                return rfile.read().split(":")[1]
        except FileNotFoundError:
            default_project = Project("default", self)
            if not default_project.exists():
                default_project.create()
            self._update_config(default_project)
            return "default"

    def _update_config(self, project: Project) -> None:
        """Updates the project config"""
        config_file_path = self.base_path / "config"
        with open(config_file_path, "w", encoding="utf-8") as wfile:
            wfile.write(f"project_name:{project.name}")

    def set_project(self, project: Project) -> None:
        """Sets the current running project"""
        self.current_project = project
        if not self.current_project.exists():
            self.current_project.create()

        self._update_config(self.current_project)

    def get_project_names(self) -> list[str]:
        """Get's the current project"""
        projects_path = self.base_path / "projects"
        return sorted([pdir.name for pdir in projects_path.iterdir()])

    def get_remote_project_names(self) -> list[str]:
        """Gets names of remote projects"""
        projects_path = self.base_path / "projects"
        remote_projs = []
        for proj in projects_path.iterdir():
            if (proj / "remote").is_file():
                remote_projs.append(proj.name)
        return remote_projs

    def delete(self) -> None:
        """Deletes"""
        shutil.rmtree(self.base_path)


class Project:
    """Models a project and the directory structure needed
    for its timer tasks.  May be local or remote.
    Creating a Project object does not automatically create
    the project on disk.  Programmers can use the create()
    and exists() methods accordingly.
    """

    def __init__(
        self,
        name: str,
        config: Config,
        origin="local",
        url: str | None = None,
        user: str | None = None,
    ) -> None:
        self.name = name
        self.path = config.base_path / "projects" / self.name
        self.active_timers_path = self.path / "active-timers"
        self.finished_timers_path = self.path / "finished-timers"
        self.origin = origin
        self.url = url
        self.user = user
        if self.origin == "local" and (self.path / "remote").exists():
            self.origin = "remote"
        if self.origin == "remote" and (url is None or user is None):
            with open(self.path / "remote", "r", encoding="utf-8") as fptr:
                self.url = fptr.readline()[4:].strip()
                self.key = fptr.readline()[4:].strip()
                self.user = fptr.readline()[9:].strip()

    def exists(self) -> bool:
        """Am I real?"""
        return self.path.exists()

    def create(self) -> None:
        """I am made in his image"""
        if self.exists():
            return
        if self.origin == "remote":
            if self.url is None or self.user is None:
                raise ValueError(
                    "Both url and user must be provided for remote projects."
                )

            try:
                result = requests.post(
                    (self.url or "") + "/api/init",
                    data={"project": self.name, "username": self.user},
                    timeout=3,
                )
            except requests.exceptions.ConnectionError:
                raise ConfigException("Could not connect to remote server.")
            if not result.ok:
                raise ConfigException("A request to the remote server failed.")
            key = result.json()["key"]
            self.path.mkdir(parents=True)
            with open(self.path / "remote", "w", encoding="utf-8") as remote:
                remote.write(
                    f"url:{self.url}\nkey:{key}\nusername:{self.user}"
                )
            return
        self.path.mkdir(parents=True)
        self.active_timers_path.mkdir()
        self.finished_timers_path.mkdir()

    def delete(self) -> None:
        """Destroy me"""
        if self.exists():
            if self.origin == "remote":
                try:
                    result = requests.delete(
                        (self.url or "") + "/api/delete",
                        auth=HTTPBasicAuth(self.key, ""),
                        timeout=3,
                    )
                except requests.exceptions.ConnectionError:
                    raise ConfigException(
                        "Could not connect to remote server."
                    )
                if not result.ok:
                    raise ConfigException(
                        "A request to the remote server failed."
                    )
            shutil.rmtree(self.path)
        else:
            raise ConfigException(
                f'Cannot delete project "{self.name}". '
                + "Project does not exist."
            )

    @staticmethod
    def connect(config: Config, url: str, user: str, key: str) -> "Project":
        """Connects to an existing remote project, returning a Project object."""
        try:
            result = requests.get(
                (url or "") + "/api/project",
                data={"username": user},
                auth=HTTPBasicAuth(key, ""),
                timeout=3,
            )
        except requests.exceptions.ConnectionError:
            raise ConfigException("Could not connect to remote server.")
        if not result.ok:
            raise ConfigException("A request to the remote server failed.")
        name = result.json()["name"]
        path = config.base_path / "projects" / name
        if (path).exists():
            raise FileExistsError(name)
        path.mkdir(parents=True)
        path /= "remote"
        with open(path, "w", encoding="utf-8") as fptr:
            fptr.write(f"url:{url}\nkey:{key}\nusername:{user}")
        return Project(name, config, "remote", url, user)
