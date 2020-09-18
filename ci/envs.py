#!/usr/bin/env python
import crypt
import sys
import getpass
import os
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


userpass=crypt.crypt(userpass, crypt.mksalt(crypt.METHOD_SHA512))

v = {
    "password": passwd,
    "passwordcrypt": passwdcrypt,
    "pubkey": pubkey,
    "userpass": userpass
}

envfile=sys.argv.pop(1)
with open(envfile, "w+") as fstrm:
    fstrm.write("""# dotenv variables
password={password}
passwordcrypt={passwordcrypt}
pubkey={pubkey}
userpass={userpass}
""".format(**v))
    fstrm.close()