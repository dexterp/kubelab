#!/usr/bin/env python3
import base64
import ctypes
import getpass
import os
import secrets
import string
import sys

def generate_linux_hash(password):
    # Load the system's crypt library
    libcrypt = ctypes.CDLL("libcrypt.so.1")
    
    # Define return type as a character pointer (string)
    libcrypt.crypt.restype = ctypes.c_char_p
    
    # Generate a random 16-character salt for SHA-512
    # Shadow salts use the [./0-9A-Za-Z] alphabet
    raw_salt = os.urandom(16)
    salt_str = base64.b64encode(raw_salt, altchars=b"./").decode().rstrip("=")[:17]
    
    # Format the salt string for SHA-512 ($6$)
    full_salt = f"$6${salt_str}".encode('utf-8')
    
    # Generate the hash
    hashed = libcrypt.crypt(password.encode('utf-8'), full_salt)
    return hashed.decode('utf-8')

def generate_password(
    length: int = 20,
    groups: int = 4,
    separator: str = "-"
) -> str:
    """
    Generate a human-friendly secure password.

    Features:
    - Avoids visually confusing characters
      (0/O, 1/l/I, etc.)
    - Uses only easy-to-type ASCII characters
    - Includes lowercase, uppercase, and digits
    - Uses cryptographically secure randomness
    - Grouped format improves readability and typing

    Example:
        W7mk-X9ra-pQ4t-Z8vn
    """

    if groups < 1:
        raise ValueError("groups must be >= 1")

    # Easy-to-read characters
    lowercase = "abcdefghjkmnpqrstuvwxyz"
    uppercase = "ABCDEFGHJKMNPQRSTUVWXYZ"
    digits = "23456789"

    alphabet = lowercase + uppercase + digits

    # Ensure at least one character from each class
    password_chars = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
    ]

    # Fill remaining length
    while len(password_chars) < length:
        password_chars.append(secrets.choice(alphabet))

    # Shuffle securely
    secrets.SystemRandom().shuffle(password_chars)

    password = "".join(password_chars)

    # Add separators for readability
    if separator and groups > 1:
        chunk_size = max(1, len(password) // groups)
        chunks = [
            password[i:i + chunk_size]
            for i in range(0, len(password), chunk_size)
        ]
        password = separator.join(chunks)

    return password


p = os.environ.get("KUBELAB_PUBKEY", "")
print(p)
if p == "":
    ed25519 = os.path.join(os.environ.get("HOME", ""), ".ssh", "id_ed25519.pub")
    rsa = os.path.join(os.environ.get("HOME", ""), ".ssh", "id_rsa.pub")
    if os.path.exists(ed25519):
        p = ed25519
    else:
        p = rsa

f = open(p, 'r+')
pubkey=f.read().rstrip("\n")
f.close()

# Generate a random password
passwd = generate_password(8, 3, "-")
passcrypted = generate_linux_hash(passwd)

v = {
    "password": passwd,
    "passwordcrypt": passcrypted,
    "pubkey": pubkey,
    "user": getpass.getuser()
}

envfile=sys.argv.pop(1)
with open(envfile, "w+") as fstrm:
    fstrm.write("""
user='{user}'
password='{password}'
passwordcrypt='{passwordcrypt}'
pubkey='{pubkey}'
""".format(**v))
    fstrm.close()