#!/usr/bin/env python3

"""
Libvirt configuration generator.

Usage:
  libvirtsetup.py net [-q] --config=<path> --net-template=<path> --output=<path>
  libvirtsetup.py domain [-q] --config=<path> --dom-template=<path> --dir=<path>
  libvirtsetup.py installdisk [-q] [--cache-dir=<path>] --config=<path>
  libvirtsetup.py start [-q] --config=<path> --net-template=<path> --dom-template=<path>
  libvirtsetup.py shutdown [-q] --config=<path>
  libvirtsetup.py remove [-q] --config=<path>

Options:
  -h --help                 Show this screen.
  -q --quiet                Suppress output.

  -c --config=<path>        Path to YAML configuration file.

  -t --net-template=<path>  Path to Jinja2 network template.
  -x --dom-template=<path>  Path to Jinja2 domain template.

  -o --output=<path>        Output path for generated network XML.
  -d --dir=<path>           Directory to write generated domain XML files.

     --cache-dir=<path>     Path to cache directory. [default: /var/cache/libvirt-gen-conf]
"""

from pathlib import Path
from lib.install_vm import InstallVM
from lib.inject import Inject

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import yaml
from docopt import docopt
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

#
# Globals
#
quiet = False


#
# Config loading
#
    
def load_yaml_config(config_path: Path) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

#
# Downloading images
#
def cache_key(uri: str) -> str:
    """
    Create a stable filename from the URI.
    """
    return hashlib.sha256(uri.encode("utf-8")).hexdigest()

def get_cached_path(cache_dir: Path, uri: str) -> Path:
    parsed = urlparse(uri)

    # Preserve original extension if possible
    ext = Path(parsed.path).suffix

    return cache_dir / f"{cache_key(uri)}{ext}"


def download_http(uri: str, dest: Path):
    with urlopen(uri) as response:
        with open(dest, "wb") as f:
            shutil.copyfileobj(response, f)


def copy_file_uri(uri: str, dest: Path):
    parsed = urlparse(uri)

    path = parsed.path

    if not path:
        raise ValueError(f"Invalid file URI: {uri}")

    src = Path(path)

    if not src.exists():
        raise FileNotFoundError(src)

    shutil.copy2(src, dest)


def fetch(uri: str, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)

    cached_file = get_cached_path(cache_dir, uri)

    if cached_file.exists():
        print(f"Using cached file: {cached_file}")
        return cached_file

    print(f"Downloading: {uri}")

    parsed = urlparse(uri)

    if parsed.scheme in ("http", "https"):
        download_http(uri, cached_file)

    elif parsed.scheme == "file":
        return Path(parsed.path)

    else:
        raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")

    print(f"Cached at: {cached_file}")

    return cached_file


#
# Disk installation
#


def volume_exists(pool, name):
    """Check whether a volume exists in the pool."""
    result = subprocess.run(
        ["virsh", "vol-info", "--pool", pool, name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return result.returncode == 0


def get_pool_state(pool):
    output = run_command(["virsh", "pool-info", pool])

    for line in output.splitlines():
        if line.strip().startswith("State:"):
            return line.split(":", 1)[1].strip()

    return None


def ensure_pool_started(pool):
    state = get_pool_state(pool)

    if state != "running":
        print(f"Starting pool '{pool}'...")
        run_command(["virsh", "pool-start", pool])


def get_file_size(src_file):
    """
    Return the actual qcow2 file size in bytes using native file stat.
    """
    return os.stat(src_file).st_size


def create_volume_xml(volume_name, capacity):
    return f"""<volume>
  <name>{volume_name}</name>
  <capacity unit='bytes'>{capacity}</capacity>
  <allocation>0</allocation>
  <target>
    <format type='qcow2'/>
  </target>
</volume>
"""


#
# Template rendering
#

def create_template_environment(template_path: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template(
    template_path: Path,
    context: dict,
) -> str:
    env = create_template_environment(template_path)

    template = env.get_template(template_path.name)

    return template.render(context)


#
# Network XML generation
#

def generate_network(
    config_path: Path,
    template_path: Path,
    output_path: Path,
):
    config = load_yaml_config(config_path)

    network = config["network"]
    hosts = config["hosts"]

    xml_output = render_template(
        template_path=template_path,
        context={
            "name": network["name"],
            "domain_name": network["domain"],

            "forward_mode": network["forward"]["mode"],

            "bridge_name": network["bridge"]["name"],
            "bridge_stp": network["bridge"]["stp"],
            "bridge_delay": network["bridge"]["delay"],

            "mac_address": network["mac"],

            "ip_address": network["ip"]["address"],
            "netmask": network["ip"]["netmask"],

            "dhcp_range_start": network["dhcp"]["range"]["start"],
            "dhcp_range_end": network["dhcp"]["range"]["end"],

            "hosts": hosts,
        },
    )

    output_path.write_text(xml_output)

    if not quiet:
        print(f"Generated network XML: {output_path}")


#
# Domain XML generation
#

def generate_domains(
    config_path: Path,
    template_path: Path,
    output_dir: Path,
):
    config = load_yaml_config(config_path)

    network = config["network"]
    hosts = config["hosts"]

    output_dir.mkdir(parents=True, exist_ok=True)

    for host in hosts:
        xml_output = render_template(
            template_path=template_path,
            context={
                "name": host["name"],
                "ip": host["ip"],
                "mac": host["mac"],
                "mem_size": host["mem_size"],
                "mem_cur_size": host["mem_cur_size"],
                "vcpu_count": host["vcpu_count"],
                "os_id": host["os_id"],
                "network": network,
                "host": host,
                "vol_pool": host["vol_pool"],
                "vol_name": host["vol_name"],
            },
        )

        output_file = output_dir / f"{host['name']}.xml"

        output_file.write_text(xml_output)

        if not quiet:
            print(f"Generated domain XML: {output_file}")


#
# Disk installation
#

def install_disk(
    config_path: Path,
    cache_dir: Path,
):
    config = load_yaml_config(config_path)

    for host in config["hosts"]:
        src_file = fetch(host["src_image"], cache_dir)

        # check if path exists and is a file print an error otherwise and skip
        if not src_file.is_file():
            print(f"Source image does not exist: {src_file}")
            continue

        # print error if the extension is not .qcow2 or .img
        if src_file.suffix != ".qcow2" and src_file.suffix != ".img":
            print(f"Source image must be a .qcow2 or .img file: {src_file}")
            continue

        # print error if the file is not readable
        if not os.access(src_file, os.R_OK): 
            print(f"Source image is not readable: {src_file}")
            continue

        # print error if the file is not writable
        if not os.access(src_file, os.W_OK):
            print(f"Source image is not writable: {src_file}")
            continue

        ensure_pool_started(host["vol_pool"])

        if volume_exists(host["vol_pool"], host['vol_name']):
            print(f"Volume '{host['vol_name']}' already exists in pool '{host['vol_pool']}'")
            continue

        capacity = get_file_size(src_file)

        print(f"Allocating volume size: {capacity} bytes")

        volume_xml = create_volume_xml(
            volume_name=host['vol_name'],
            capacity=capacity,
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".xml",
            delete=False,
        ) as f:
            f.write(volume_xml)
            xml_path = f.name

        try:
            print(f"Creating volume '{host['vol_name']}' in pool '{host['vol_pool']}'...")
    
            run_command(
                [ "virsh", "vol-create", "--pool", host['vol_pool'], xml_path ]
            )
    
            print(f"Uploading qcow2 image from '{src_file}'...")
    
            run_command(
                [ "virsh", "vol-upload", "--pool", host['vol_pool'], host['vol_name'], src_file ]
            )
    
            print("Volume successfully installed.")
            print(f"Pool   : {host['vol_pool']}")
            print(f"Volume : {host['vol_name']}")
    
        finally:
            if os.path.exists(xml_path):
                os.unlink(xml_path)


#
# Start
#
def start(
    config_path: Path,
    dom_template_path: Path,
    net_template_path: Path,
):
    config = load_yaml_config(config_path)

    # start network
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".xml",
        delete=False
    ) as f:
        generate_network(
            config_path=config_path,
            template_path=net_template_path,
            output_path=Path(f.name),
        )
        f.flush()

        # check if network exists
        if not network_exists(config["network"]["name"]):
            try:
                run_command(["virsh", "net-define", f.name])
                print(f"Network '{config['network']['name']}' created")
            except subprocess.CalledProcessError:
                print("Failed to create network from {f.name}")
                sys.exit(-1)
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)

    # check if network has started
    if not network_started(config["network"]["name"]):
        try:
            run_command(["virsh", "net-start", config["network"]["name"]])
            print("Network started")
        except subprocess.CalledProcessError:
            print("Failed to start network")
            sys.exit(1)

    virt_install(config)

    for host in config["hosts"]:
        # check if domain has started
        if domain_started(host["name"]):
            print(f"Domain '{host['name']}' already started")
        else:
            try:
                run_command(["virsh", "start", host["name"]])
                print(f"Domain '{host['name']}' started")
            except subprocess.CalledProcessError:
                print(f"Failed to start domain '{host['name']}'")
                sys.exit(1)
 
def virt_install(
    config: dict,
):
    network = config["network"]["name"]
    for host in config["hosts"]:
        name = host["name"]
        mac_address = host["mac"]
        mem_size = host["mem_size"]
        vcpu_count = host["vcpu_count"]
        os_id = host["os_id"]
        src_image = host["src_image"]

        inject = Inject()
        create_image = inject.InstallVM()
        create_image.install(name, src_image, mac_address=mac_address, mem_size=mem_size, vcpu_count=vcpu_count, os_id=os_id, user=os.environ["USER"], home=f"/home/{os.environ['USER']}", network=network)

def domain_exists(name: str) -> bool:
    try:
        # capture the output of "virsh list --all" to see if domain exists and is started
        output = run_command(["virsh", "list", "--all"])

        for line in output.splitlines():
            if name in line:
                return True

        return False

    except subprocess.CalledProcessError:
        print("Failed to list domains")


def domain_started(name: str) -> bool:
    try:
        output = run_command(["virsh", "list", "--all"])

        for line in output.splitlines():
            if name in line and "running" in line:
                return True

    except subprocess.CalledProcessError:
        print("Failed to get domain info")
        sys.exit(-1)

    return False

def network_exists(name: str) -> bool:
    output = run_command(["virsh", "net-info", name])
    if "failed to get network" in output:
        return False

    return True


def network_started(name):
    output = run_command_shell("virsh net-info " + name + " | egrep 'Active:'")
    if "yes" in output[1]:
        return True
    return False

#
# Stop
#
def shutdown(config_path: Path):
    config = load_yaml_config(config_path)
    for host in config["hosts"]:
        if domain_started(host["name"]):
            run_command(["virsh", "destroy", host["name"]])
            print("Domain " + host["name"] + " shutdown")
        else:
            print("Domain " + host["name"] + " not running")

#
# Remove
#
def remove(config_path: Path):
    config = load_yaml_config(config_path)
    for host in config["hosts"]:
        # remove domain if it exists
        if domain_exists(host["name"]):
            run_command(["virsh", "destroy", host["name"]])
            run_command(["virsh", "undefine", host["name"], "--remove-all-storage"])
            print("Domain " + host["name"] + " removed")
        else:
            print("Domain " + host["name"] + " does not exist")
        
        # remove ssh keys
        fqdn = host["fqdn"]
        run_command(["ssh-keygen", "-R", fqdn])
    
    # remove network
    if network_exists(config["network"]["name"]):
        run_command(["virsh", "net-destroy", config["network"]["name"]])
        run_command(["virsh", "net-undefine", config["network"]["name"]])
        print("Network " + config["network"]["name"] + " removed")

#
# Main
#

def main():
    args = docopt(__doc__)

    global quiet
    quiet = args["--quiet"]

    if args["net"]:
        generate_network(
            config_path=Path(args["--config"]),
            template_path=Path(args["--net-template"]),
            output_path=Path(args["--output"]),
        )

    elif args["domain"]:
        generate_domains(
            config_path=Path(args["--config"]),
            template_path=Path(args["--dom-template"]),
            output_dir=Path(args["--dir"]),
        )

    elif args["installdisk"]:
        install_disk(
            config_path=Path(args["--config"]),
            cache_dir=Path(args["--cache-dir"]),
        )
    
    elif args["start"]:
        start(
            config_path=Path(args["--config"]),
            dom_template_path=Path(args["--dom-template"]),
            net_template_path=Path(args["--net-template"]),
        )
    elif args["shutdown"]:
        shutdown(config_path=Path(args["--config"]))
    elif args["remove"]:
        confirm = input("Are you sure you want to remove all domains and network? (y/n): ")
        if confirm.lower() == "y":
            remove(config_path=Path(args["--config"]))

def fail(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)

def run_command(cmd):
    """Run a command and return stdout."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        return result.stderr.strip()

    return result.stdout.strip()

def run_command_shell(cmd) -> tuple[bool, str]:
    """Run a command and return stdout."""
    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        return fail(result.stderr.strip())

    return result.stdout

if __name__ == "__main__":
    main()