#!/usr/bin/env python3

# Docopts document
"""
Usage:
    createimage.py [--url=<url>] [-i --image-dir=<dir>] <vm_name>

Options:
    -h --help               Show this screen.
    -u --url=<url>             URL to download base image from [default: https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img]
"""

from lib.inject import Inject
from scripts.lib.install_vm import InstallVM

import docopt
import os
import sys
from pathlib import Path
from urllib.parse import urlparse


def main():
    args = docopt.docopt(
        __doc__,
        argv=sys.argv[1:],
    )

    vm_name = args["<vm_name>"]
    image_url = args["--url"]

    inject = Inject()

    createImage: InstallVM = inject.InstallVM()
    createImage.install(vm_name, image_url, user=os.environ["USER"], home=os.environ["HOME"], network="default")


if __name__ == "__main__":
    main()
