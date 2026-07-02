#!/usr/bin/env python3

"""
Install a qcow2 image into a libvirt storage pool using virsh.

Usage:
  install-qcow2.py --name=<name> --src-file=<path> [--pool=<pool>]
  install-qcow2.py (-h | --help)

Options:
  -h --help               Show this help.
  --pool=<pool>           Libvirt storage pool name [default: default]
  --name=<name>           Name of the new volume (mandatory).
  --src-file=<path>       Source qcow2 image file.
"""

import os
import subprocess
import sys
import tempfile

from docopt import docopt

# =================================================================================
# CACHE
# =================================================================================

import hashlib
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


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

    # Handles:
    #   file:///tmp/file.iso
    #   file://./relative/path
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
        copy_file_uri(uri, cached_file)

    else:
        raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")

    print(f"Cached at: {cached_file}")

    return cached_file


def main():
    args = docopt(__doc__)

    uri = args["<uri>"]
    cache_dir = Path(args["--cache-dir"])

    try:
        cached_path = fetch(uri, cache_dir)
        print(f"Ready: {cached_path}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


# =================================================================================
# END CACHE
# =================================================================================

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
        fail(result.stderr.strip())

    return result.stdout.strip()


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


def main():
    args = docopt(__doc__)

    pool = args["--pool"]
    name = args["--name"]
    src_file = args["--src-file"]

    if not os.path.isfile(src_file):
        fail(f"Source file does not exist: {src_file}")

    if not os.access(src_file, os.R_OK):
        fail(f"Source file is not readable: {src_file}")

    volume_name = f"{name}.qcow2"

    ensure_pool_started(pool)

    if volume_exists(pool, volume_name):
        fail(f"Volume '{volume_name}' already exists in pool '{pool}'")

    capacity = get_file_size(src_file)

    print(f"Allocating volume size: {capacity} bytes")

    volume_xml = create_volume_xml(
        volume_name=volume_name,
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
        print(f"Creating volume '{volume_name}' in pool '{pool}'...")

        run_command(
            [ "virsh", "vol-create", "--pool", pool, xml_path ]
        )

        print(f"Uploading qcow2 image from '{src_file}'...")

        run_command(
            [ "virsh", "vol-upload", "--pool", pool, volume_name, src_file ]
        )

        print("Volume successfully installed.")
        print(f"Pool   : {pool}")
        print(f"Volume : {volume_name}")

    finally:
        if os.path.exists(xml_path):
            os.unlink(xml_path)


if __name__ == "__main__":
    main()