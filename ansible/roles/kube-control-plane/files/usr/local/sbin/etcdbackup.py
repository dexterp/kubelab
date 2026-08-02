#!/usr/bin/env python3

""" Take and restore etcd snapshots.

Usage:
    etcdbackup backup [--key=<key>] [--cacert=<cacert>] [--cert=<cert>] [--endpoints=<url>] [--backupdir=<backupdir>] [--keep=<n>] [--age=<days>]
    etcdbackup restore [--datadir=<datadir>] <snapshot>

Options:
    -h --help                  Show this help message.
    --key=<key>                Path to client key [default: /etc/kubernetes/pki/etcd/server.key].
    --cacert=<cacert>          Path to CA certificate [default: /etc/kubernetes/pki/etcd/ca.crt].
    --cert=<cert>              Path to client certificate [default: /etc/kubernetes/pki/etcd/server.crt].
    --endpoints=<endpoints>    etcd endpoint [default: https://localhost:2379].
    --backupdir=<backupdir>    Directory to store snapshots [default: /var/backups].
    --keep=<n>                 Number of snapshots to retain [default: 7].
    --age=<days>               Delete snapshots older than this many days [default: 7].
    --datadir=<datadir>        Path to etcd data. [default: /var/lib/etcd]
    <snapshot>                 Name of snapshot.
"""

import os
import subprocess
import sys
import syslog
import time
from datetime import datetime, timedelta

import yaml
from docopt import docopt

def env_vars():
    """Return the environment required for etcdctl/etcdutl."""
    env = os.environ.copy()
    env["ETCDCTL_API"] = "3"
    return env


class Config:
    """Load YAML settings, CLI settings, and produce the merged runtime config."""

    def __init__(self, yaml_path: str | None = None, cli: dict | None = None):
        self._data: dict = {}
        self._cli = cli or {}
        if yaml_path:
            try:
                with open(yaml_path, "r", encoding="utf-8") as handle:
                    loaded = yaml.safe_load(handle) or {}
                    if isinstance(loaded, dict):
                        self._data = loaded
            except (FileNotFoundError, PermissionError, yaml.YAMLError):
                self._data = {}

        self.backup: bool = bool(self._cli.get("backup", False))
        self.restore: bool = bool(self._cli.get("restore", False))
        self.keep: int | None = self._get_value("keep", self._cli.get("--keep"))
        self.age: int | None = self._get_value("age", self._cli.get("--age"))
        self.endpoints: str | None = self._get_value("endpoints", self._cli.get("--endpoints"))
        self.key: str | None = self._get_value("key", self._cli.get("--key"))
        self.cacert: str | None = self._get_value("cacert", self._cli.get("--cacert"))
        self.cert: str | None = self._get_value("cert", self._cli.get("--cert"))
        self.backup_dir: str | None = self._get_value("backup_dir", self._cli.get("--backupdir"))
        self.snapshot: str | None = self._get_value("snapshot", self._cli.get("<snapshot>"))
        self.datadir: str | None = self._get_value("datadir", self._cli.get("--datadir"))

        if self.keep is not None and not isinstance(self.keep, int):
            self.keep = int(self.keep)
        if self.age is not None and not isinstance(self.age, int):
            self.age = int(self.age)

    def _get_value(self, key: str, cli_value):
        if key in self._data and self._data[key] is not None:
            value = self._data[key]
            if isinstance(value, str):
                value = value.strip()
                if value == "":
                    return None
            if key in {"keep", "age"} and isinstance(value, str):
                return int(value)
            return value
        if cli_value is None:
            return None
        if isinstance(cli_value, str):
            cli_value = cli_value.strip()
            if cli_value == "":
                return None
        return cli_value


class Crictl:
    """Inspect container runtime state for Kubernetes static pods."""

    def _pod_states(self) -> list[str]:
        completed = subprocess.run(
            ["crictl", "pods", "--namespace", "kube-system"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return []
        lines = []
        for line in completed.stdout.splitlines():
            if "NAME" in line:
                continue
            lines.append(line.strip())
        return lines

    def has_started_static_pods(self) -> bool:
        sched_ready = False
        controller_ready = False
        api_ready = False
        etcd_ready = False
        for entry in self._pod_states():
            if "Ready" in entry and "kube-scheduler" in entry:
                sched_ready = True
            elif "Ready" in entry and "kube-controller-manager" in entry:
                controller_ready = True
            elif "Ready" in entry and "kube-apiserver" in entry:
                api_ready = True
            elif "Ready" in entry and "etcd" in entry:
                etcd_ready = True

        if sched_ready and controller_ready and api_ready and etcd_ready:
            return True
        else:
            return False


    def has_stopped_static_pods(self) -> bool:
        for entry in self._pod_states():
            if "kube-scheduler" in entry or "kube-controller-manager" in entry or "kube-apiserver" in entry or "etcd" in entry:
                return False
        return True

    def wait_for_static_pods_to_stop(self, timeout: int = 300) -> bool:
        deadline = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < deadline:
            if self.has_stopped_static_pods():
                return True
            time.sleep(2)
        return False

    def wait_for_static_pods_to_start(self, timeout: int = 300) -> bool:
        deadline = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < deadline:
            if self.has_started_static_pods():
                return True
            time.sleep(2)
        return False


class StaticPods:
    """Temporarily move static-pod manifest files out of the way during restore."""

    MANIFEST_DIR = "/etc/kubernetes/manifests"
    STOPPED_DIR = "/etc/kubernetes/manifests/stopped"

    def __init__(self, crictl: Crictl):
        self._crictl = crictl

    def disable(self) -> None:
        log_info("Stopping static pods")
        os.makedirs(self.STOPPED_DIR, exist_ok=True)
        readme_path = os.path.join(self.STOPPED_DIR, "README.txt")
        if not os.path.exists(readme_path):
            with open(readme_path, "w", encoding="utf-8") as handle:
                handle.write(
                    "This directory is managed by etcbackup. Do not edit or move the files here.\n"
                )
        for manifest in sorted(os.listdir(self.MANIFEST_DIR)):
            src = os.path.join(self.MANIFEST_DIR, manifest)
            if not manifest.endswith(".yaml"):
                continue
            dst = os.path.join(self.STOPPED_DIR, manifest)
            os.rename(src, dst)
        if not self._crictl.wait_for_static_pods_to_stop():
            raise RuntimeError("Timed out waiting for static pods to stop")

    def enable(self) -> None:
        log_info("Starting static pods")
        for manifest in sorted(os.listdir(self.STOPPED_DIR)):
            src = os.path.join(self.STOPPED_DIR, manifest)
            if not manifest.endswith(".yaml"):
                continue
            dst = os.path.join(self.MANIFEST_DIR, manifest)
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
        if not self._crictl.wait_for_static_pods_to_start():
            raise RuntimeError("Timed out waiting for static pods to be created")


class Snapshot:
    """Manage snapshot creation and restoration"""
    def __init__(self, args: Config, env_vars: dict, static_pods: StaticPods | None = None):
        self._args = args
        self._env_vars: dict = env_vars
        self._static_pods = static_pods
        syslog.openlog("etcdbackup", syslog.LOG_PID | syslog.LOG_CONS, syslog.LOG_DAEMON)

    def _run_command(self, cmd: list[str], env: dict) -> subprocess.CompletedProcess:
        completed = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if completed.returncode != 0:
            output = "\n".join(filter(None, [completed.stdout, completed.stderr])).strip()
            if output:
                self._log_error(f"{cmd[0]} failed: {output}")
            else:
                self._log_error(f"{cmd[0]} failed with exit code {completed.returncode}")
            raise subprocess.CalledProcessError(
                completed.returncode,
                cmd,
                output=completed.stdout,
                stderr=completed.stderr,
            )
        return completed

    def save_snapshot(self) -> str:
        """Take an etcd snapshot and move it into the backup directory."""

        timestamp = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
        hostname = os.uname().nodename
        prefix = "kubernetes-etcd"
        filename = f"{prefix}-{hostname}-{timestamp}.db"

        tmp_path = os.path.join("/tmp", filename)
        backup_path = os.path.join(self._args.backup_dir, filename)

        cmd = [
            "etcdctl", "--endpoints", self._args.endpoints, "--key", self._args.key, "--cacert", self._args.cacert, "--cert", self._args.cert,
            "snapshot", "save", tmp_path,
        ]

        try:
            self._run_command(cmd, self._env_vars)
        except subprocess.CalledProcessError:
            raise

        os.makedirs(self._args.backup_dir, exist_ok=True)
        os.replace(tmp_path, backup_path)

        log_info(f"Snapshot saved to {backup_path}")

        return backup_path

    def prune_backups(self) -> None:
        """Delete snapshots older than the configured age, while always keeping the newest snapshots."""

        entries = [
            os.path.join(self._args.backup_dir, filename)
            for filename in os.listdir(self._args.backup_dir)
            if filename.startswith("kubernetes-etcd") and filename.endswith(".db")
        ]

        entries.sort(key=os.path.getmtime, reverse=True)

        cutoff = datetime.now() - timedelta(days=self._args.age)

        for snapshot in entries[self._args.keep:]:
            snapshot_time = datetime.fromtimestamp(os.path.getmtime(snapshot))
            if snapshot_time < cutoff:
                log_info(f"Removing old snapshot: {snapshot}")
                os.remove(snapshot)

    def restore_snapshot(self) -> None:
        """Restore an etcd snapshot into a new data directory."""

        if not os.path.isfile(self._args.snapshot):
            sys.exit(f"Snapshot file not found: {self._args.snapshot}")

        cmd = [ "etcdutl", "snapshot", "restore", self._args.snapshot, "--data-dir", self._args.datadir ]

        log_info(f"Restoring {self._args.snapshot} into {self._args.datadir}")
        self._static_pods.disable()

        if os.path.exists(self._args.datadir):
            timestamp = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
            old_path = f"{self._args.datadir}.old.{timestamp}"
            os.rename(self._args.datadir, old_path)
        try:
            self._run_command(cmd, env_vars())
        except subprocess.CalledProcessError:
            raise
        finally:
            if self._static_pods is not None:
                self._static_pods.enable()
        log_info("Restore complete.")


class RunCmd:
    """Runs the commands"""
    def __init__(self, args: Config, snapshot: Snapshot):
        self._snapshot: Snapshot = snapshot
        self._args = args

    def run(self) -> None:
        if self._args.backup:
            self.cmd_backup()
        elif self._args.restore:
            self.cmd_restore()

    def cmd_backup(self) -> None:
        try:
            self._snapshot.save_snapshot()
        except subprocess.CalledProcessError as exc:
            sys.exit(f"Snapshot failed: {exc}")

        self._snapshot.prune_backups()


    def cmd_restore(self) -> None:
        try:
            self._snapshot.restore_snapshot()
        except subprocess.CalledProcessError as exc:
            sys.exit(f"Restore failed: {exc}")


class DI():
    """Manage Dependency Injection"""
    _cli: dict = {}
    _env_vars: dict = {}
    _args: Config = None
    _config: Config = None
    _crictl: Crictl = None
    _static_pods: StaticPods = None
    _snapshot: Snapshot = None
    _run_cmd: RunCmd = None

    def __init__(self, cli: dict, env_vars):
        self._cli = cli
        self._env_vars = env_vars

    def make_config(self) -> Config:
        if self._config is None:
            config_path = self._cli.get("--config")
            self._config = Config(yaml_path=config_path, cli=self._cli)
        return self._config

    def make_run_config(self) -> Config:
        return self.make_config()

    def make_crictl(self) -> Crictl:
        if self._crictl is None:
            self._crictl = Crictl()
        return self._crictl

    def make_static_pods(self) -> StaticPods:
        if self._static_pods is None:
            self._static_pods = StaticPods(self.make_crictl())
        return self._static_pods

    def make_snapshot(self) -> Snapshot:
        if self._snapshot is None:
            self._snapshot = Snapshot(self.make_run_config(), self._env_vars, self.make_static_pods())
        return self._snapshot

    def make_run_cmd(self) -> RunCmd:
        if self._run_cmd is None:
            self._run_cmd = RunCmd(self.make_run_config(), self.make_snapshot())
        return self._run_cmd

def log_info(message: str) -> None:
    print(message)
    syslog.syslog(syslog.LOG_INFO, message)

def log_error(message: str) -> None:
    print(message)
    syslog.syslog(syslog.LOG_ERR, message)


def main():
    inject = DI(docopt(__doc__), env_vars())
    cmd_run = inject.make_run_cmd()
    cmd_run.run()


if __name__ == "__main__":
    main()