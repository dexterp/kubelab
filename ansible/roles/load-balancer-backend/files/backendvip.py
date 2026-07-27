#!/usr/bin/env python3

""" Enable disable backend vips

Usage:
    backendvip.py enable [--config=<config>] (<vip>|--all-vips)
    backendvip.py disable [--config=<config>] (<vip>|--all-vips)
    backendvip.py list [--config=<config>] [<vip>]

Options:
    -h --help             Print help
    enable                Enable virtual ip 
    disable               Disable virtual ip
    list                  List vips
    <vip>                 IP address of VIP. Must be just the IP not the CIDR.
    -c --config=<config>  Path to configuration file. [default: /etc/backendvip/backendvip.yaml]
    -a --all-vips         Process all vips in the config file

"""

from docopt import docopt
from pathlib import Path

import os
import subprocess
import yaml

default_dev = "lo"

def main():
    args = docopt(__doc__)

    di = DI(args["--config"],args["<vip>"])

    check = di.make_check()
    check.check_run_as_root()
    check.check_arp_ignore()
    check.check_vip_in_conf()

    ip = di.make_ip()

    if args["enable"]:
        ip.enable()
    elif args["disable"]:
        ip.disable()
    elif args["list"]:
        ip.list()


class Config:
    dev: str
    vips: list
    def __init__(self, config_file=Path):
        with open(config_file) as file:
            config_data: dict = yaml.safe_load(file)
            self.dev = config_data.get("dev", default_dev)
            self.vips = config_data.get("vips", [])

    def has_vip(self, vip: str) -> bool:
        return vip in self.vips


class Check:
    _vip: str = None
    _config_vips: list[str] = []
    def __init__(self, vip: str = None, config_vips: list[str]=[]):
        self._vip = vip
        self._config_vips = config_vips

    def check_arp_ignore(self) -> None:
        required_values = {
            "/proc/sys/net/ipv4/conf/all/arp_ignore": "1",
            "/proc/sys/net/ipv4/conf/all/arp_announce": "2",
            "/proc/sys/net/ipv4/conf/default/arp_ignore": "1",
            "/proc/sys/net/ipv4/conf/default/arp_announce": "2",
        }
        issues = []

        for procfs_path, expected in required_values.items():
            try:
                with open(procfs_path) as proc_file:
                    current_value = proc_file.read().strip()
            except OSError:
                issues.append(f"{procfs_path}: unavailable")
                continue

            if current_value != expected:
                issues.append(f"{procfs_path}: expected {expected}, got {current_value}")

        if issues:
            print("ARP-related kernel settings are not configured correctly:")
            for issue in issues:
                print(f"  - {issue}")
            raise SystemExit(1)

    def check_run_as_root(self) -> None:
        if os.geteuid() != 0:
            print("This script must be run as root.")
            raise SystemExit(1)

    def check_vip_in_conf(self) -> None:
        if self._vip and self._vip not in self._config_vips:
            print(f"VIP {self._vip} is not defined in the configuration.")
            raise SystemExit(1)


class Ip:
    _dev: str
    _vips: list
    def __init__(self, dev: str, vips: list):
        self._dev = dev
        self._vips = vips

    def enable(self):
        for vip in self._vips:
            if check_ip_on_dev(vip, self._dev):
                continue

            subprocess.check_call(
                ["ip", "addr", "add", f"{vip}/32", "dev", self._dev]
            )

    def disable(self):
        for vip in self._vips:
            if not check_ip_on_dev(vip, self._dev):
                continue

            subprocess.check_call(
                ["ip", "addr", "del", f"{vip}/32", "dev", self._dev]
            )

    def list(self):
        print(f"{'VIP':<16} {'STATUS':<8}")
        for vip in self._vips:
            status = "enabled" if check_ip_on_dev(vip, self._dev) else "disabled"
            print(f"{vip:<16} {status:<8}")


class DI:
    """Manage Dependency Injection"""
    _config_file: Path = None
    _config: Config = None
    _check: Check = None
    _ip: Ip = None
    _vip: str = None
    def __init__(self, config_file: Path, vip: str = None):
        self._config_file = config_file
        self._vip = vip

    def make_check(self) -> Check:
        if self._check is None:
            self._check = Check(self._vip, self.make_config().vips)
        return self._check

    def make_config(self) -> Config:
        if self._config is None:
            self._config = Config(self._config_file)
        return self._config

    def make_ip(self) -> Ip:
        if self._ip is None:
            if self._vip is not None:
                self._ip = Ip(self.make_config().dev, [self._vip])
            else:
                self._ip = Ip(self.make_config().dev, self.make_config().vips)
        return self._ip


def check_ip_on_dev(ip: str, interface: str) -> bool:
    result = subprocess.run(
        ["ip", "addr", "show", "dev", interface], capture_output=True, text=True, check=True)
        
    for line in result.stdout.splitlines():
        if f"inet {ip}/32" in line:
            return True
    return False

def check_interface_exists(interface: str) -> bool:
    p = subprocess.run(
        ["ip", "link", "show", interface],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return p.returncode == 0

main()

