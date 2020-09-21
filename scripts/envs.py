#!/usr/bin/env python
import crypt
import sys
import getpass
import os
import re
import urllib
import urllib.request
import string

from random import choice

letters=string.ascii_letters + string.digits

passwd = ''.join([choice(letters) for i in range(10)])
passwdcrypt = crypt.crypt(passwd, crypt.mksalt(crypt.METHOD_SHA512))

p = os.path.join(os.environ.get("HOME", ""), ".ssh", "id_rsa.pub")
f = open(p, 'r+')
pubkey=f.read().rstrip("\n")
f.close()

sys.stderr.write("User {USER} will be added to VM. Enter a password\n".format(**os.environ))

userpass=""
for i in range(1,4):
    p1=getpass.getpass(prompt='Password: ', stream=None)
    p2=getpass.getpass(prompt='Re-enter Password: ', stream=None)
    if p1 != p2:
        sys.stderr.write("\nPasswords do not match\n")
        continue
    userpass=p1
    break


if len(userpass) == 0:
    sys.stderr.write("ERROR: No password set")
    sys.exit(-1)


page = urllib.request.urlopen('http://mirrorlist.centos.org/?repo=os&arch=x86_64&release=7')

urlstr=''
urlobj=None
for u in page.readlines():
    url=u.decode('utf-8').rstrip("\n")
    urlobj=urllib.parse.urlparse(url)
    if urlobj is not None:
        p = re.compile(r'/[^/]+/os/x86_64/')
        newurl = p.sub('', url)
        chk = urllib.request.urlopen(newurl)
        if chk.code == 200:
            urlstr=newurl
            break

if urlstr == "":
    raise Exception("Can not find centos base url")

userpass=crypt.crypt(userpass, crypt.mksalt(crypt.METHOD_SHA512))

v = {
    "password": passwd,
    "passwordcrypt": passwdcrypt,
    "pubkey": pubkey,
    "userpass": userpass,
    "urlstr": urlstr
}

envfile=sys.argv.pop(1)
with open(envfile, "w+") as fstrm:
    fstrm.write("""# dotenv variables
password={password}
passwordcrypt={passwordcrypt}
pubkey={pubkey}
userpass={userpass}
urlstr={urlstr}
""".format(**v))
    fstrm.close()