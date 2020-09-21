#!/usr/bin/env python

"""# VM Sets virtual machine static IP

Usage:
    setstaticip.py <domain> <network> <ip>

"""

import codecs
import ipaddress
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import xml.etree.ElementTree as ET

from docopt import docopt
from xml.dom import minidom
from subprocess import Popen, PIPE
from typing import List, Union


def getmac(domain: str) -> str:
    """
    Gets returns the mac adress of a supplied domain
    """
    pipe = _popenwrap(['virsh', 'dumpxml', domain])
    xml = pipe.stdout.read()
    xdoc = minidom.parseString(xml)
    ifaces = xdoc.getElementsByTagName('interface')

    mac_addr = None
    for iface in ifaces:
        if iface.getAttribute("type") != "network":
            continue


        for mac in iface.getElementsByTagName("mac"):
            mac_addr = mac.getAttribute("address")
            break
    
    return mac_addr


def setstatic(network: str, mac: str, name: str, ip: str) -> bool:
    """
    Set static IP network. Returns false if ip is not in a network range.
    """
    ipv4 = ipaddress.IPv4Address(ip)
    pipe = _popenwrap(['virsh', 'net-dumpxml', network])
    xdoc = pipe.stdout.read()
    etroot = ET.fromstring(xdoc)
    etips = etroot.findall('ip')
    etdhcp = None
    found = False
    for etip in etips:
        address = etip.attrib.get('address')
        netmask = etip.attrib.get('netmask')
        if len(address) == 0 or len(netmask) == 0:
            continue

        netaddr = "{}/{}".format(address, netmask)
        if ipv4 not in ipaddress.IPv4Interface(netaddr).network:
            continue

        etdhcp = etip.find('dhcp')

        found = True
        break

    if not found:
        return False

    replaced = False
    same = False
    for ethost in etdhcp.findall('host'):
        curmac = ethost.attrib.get('mac')
        curname = ethost.attrib.get('name')
        curip = ethost.attrib.get('ip')

        if curmac == mac and curname == name and curip == ip:
            replaced = True
            break

        if curmac == mac or curname == name:
            same = True
            ethost.attrib['mac'] = mac
            ethost.attrib['name'] = name
            ethost.attrib['ip'] = ip
            break

    if same:
        return True
     
    if replaced:
        save_net(etroot)
        return True

    ehost = ET.SubElement(etdhcp, 'host')
    ehost.attrib = {
        "mac": mac,
        "name": name,
        "ip": ip
    }
    save_net(etroot)

    return True


def save_net(et:ET):
        tfile = _writetmp(et)
        virsh_net_define(tfile)


def virsh_net_define(file:str):
    pipe = _popenwrap(['virsh', 'net-define', file])
    pipe.wait()


def _writetmp(et:ET) -> str:
    """
    Save XML document to a temporary file

    Returns path to the temporary file
    """
    etfmt = _et_pretty(et)
    xdoc = ET.tostring(etfmt).decode("utf-8")
    tstrm = tempfile.NamedTemporaryFile(mode='w', delete=False)
    tstrm.write(xdoc)
    tstrm.close()
    return tstrm.name


def _et_pretty(et:ET, level=0) -> ET:
    """
    Hack to fix broken pretty printing
    """
    instr = ET.tostring(et).decode('utf-8')
    dom = minidom.parseString(instr)
    outstr = dom.toprettyxml(indent='  ')
    newoutstr = ''
    for l in outstr.splitlines():
        if re.match(r"^\s*$", l):
            continue
        newoutstr += l + "\n"
    return ET.fromstring(newoutstr)


def _popenwrap(cmd: List[str]) -> Popen:
    pipe = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    if pipe.returncode is not None and pipe.returncode > 0:
        err_out = "ERROR: executing command\n\n"
        cmd_out = textwrap.indent(" ".join(cmd), 2*' ')
        stderr_out = textwrap.indent(pipe.stderr.read() + "\n", 4*' ')
        sys.stderr.write(err_out)
        sys.stderr.write(cmd_out)
        sys.stderr.write(stderr_out)
        sys.exit(pipe.returncode)
    
    return pipe


if __name__ == "__main__":
    opts = docopt(__doc__)
    domain = opts["<domain>"]
    ip = opts["<ip>"]
    network = opts["<network>"]
    mac = getmac(domain)

    setstatic(network, mac, domain, ip)