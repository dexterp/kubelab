from .cache import Cache

import os
import subprocess
import sys
import tempfile

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from urllib.parse import urlparse

class InstallVM(object):
    def __init__(self, cache: Cache, image_dir: Path):
        self._cache = cache
        self._image_dir = image_dir

    def run(self, cmd):
        subprocess.run(cmd, check=True)


    def check_kernel_permissions(self):
        vmlinuz = os.path.realpath("/boot/vmlinuz")

        if not os.access(vmlinuz, os.R_OK):
            print(
                f"virt-customize needs read permissions to {vmlinuz}",
                file=sys.stderr,
            )
            print(
                "See "
                "https://askubuntu.com/questions/1046828/"
                "how-to-run-libguestfs-tools-tools-such-as-virt-make-fs-without-sudo",
                file=sys.stderr,
            )


    def _download_image(self, image_url: str, image: Path):
        self._cache.fetch(uri=image_url, dest=image)


    def install(
        self,
        vm_name,
        image_url,
        ip: str,
        dnsserver: str,
        gateway: str,
        mac_address: str = None,
        mem_size: str = "2GiB",
        vcpu_count: str = "2",
        os_id: str = "ubuntu26.04",
        user: str="ubuntu",
        home: str="/home/ubuntu",
        network: str="default",
        password: any=None,
        ):

        self.check_kernel_permissions()

        vm_image = os.path.join(self._image_dir, f"{vm_name}.qcow2")
        vm_image_tmp = os.path.join(tempfile.gettempdir(), f".{vm_name}.qcow2")
        if os.path.exists(vm_image):
            #print(f"VM image {vm_image} already exists")
            return

        print(f"Generating VM image {vm_image_tmp} from {image_url}")
        self._download_image(image_url=image_url, image=Path(vm_image_tmp))
        self.run([ "qemu-img", "resize", "-f", "qcow2", vm_image_tmp, "20G" ])

        auth_keys_file = self.gen_authorized_keys()

        netplan_config = self.gen_netplan_config(ip=ip, dnsserver=dnsserver, gateway=gateway)
        tempdir = os.path.join("tmp", vm_name)
        os.makedirs(tempdir, exist_ok=True)
        netplan_config_file = os.path.join(tempdir, "01-netcfg.yaml")
        with open(netplan_config_file, "w") as f:
            f.write(netplan_config)

        virt_customize_cmd = [
            "virt-customize",
            "-a", vm_image_tmp,
            "--hostname", vm_name,
            "--network",
        ]

        if password is not None:
            virt_customize_cmd.extend(["--root-password", f"file:{password}"])

        virt_customize_cmd.extend([
            "--run-command", f"useradd -m {user} -s /bin/bash",
            "--run-command", f"usermod -aG sudo {user}",
            "--run-command", f"touch {home}/.zshrc",
            "--run-command", f"chown {user}:{user} {home}/.zshrc",
            "--run-command", f"mkdir -p {home}/.ssh",
            "--run-command", "mkdir -p /root/.ssh",
            "--run-command", "perl -pi -e 's/^#?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config",
            "--run-command", "perl -pi -e 's/^#?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config",
            "--chmod", f"0700:{home}/.ssh",
            "--chmod", "0700:/root/.ssh",
            "--copy-in", f"{auth_keys_file}:/{home}/.ssh",
            "--copy-in", f"{auth_keys_file}:/root/.ssh",
            "--copy-in", "guestfiles/first-boot-script.service:/etc/systemd/system/",
            "--copy-in", "guestfiles/first-boot-script:/usr/local/sbin/",
            "--copy-in", "guestfiles/sudoers:/etc/",
            "--copy-in", f"{netplan_config_file}:/etc/netplan/",
            "--run-command", "chown root:root /etc/netplan/01-netcfg.yaml",
            "--run-command", "chown root:root /etc/sudoers",
            "--run-command", "chown root:root /etc/systemd/system/first-boot-script.service",
            "--run-command", "chown root:root /usr/local/sbin/first-boot-script",
            "--run-command", f"chown {user}:{user} {home}/.ssh",
            "--run-command", f"chown {user}:{user} {home}/.ssh/authorized_keys",
            "--run-command", "chown root:root /root/.ssh",
            "--run-command", "chown root:root /root/.ssh/authorized_keys",
            "--chmod", f"0600:{home}/.ssh/authorized_keys",
            "--chmod", "0600:/root/.ssh/authorized_keys",
            "--chmod", "0600:/etc/netplan/01-netcfg.yaml",
            "--chmod", "0440:/etc/sudoers",
            "--chmod", "0744:/usr/local/sbin/first-boot-script",
            "--chmod", "0644:/etc/systemd/system/first-boot-script.service",
            "--run-command", "systemctl daemon-reload",
            "--run-command", "systemctl enable first-boot-script.service",
            "--run-command", "rm /etc/ssh/sshd_config.d/60-cloudimg-settings.conf",
        ])

        self.run(virt_customize_cmd)

        src = Path(vm_image_tmp)

        if src.exists():
            src.rename(vm_image)

        virt_install_cmd = [
            "virt-install",
            "--name", f"{vm_name}",
            "--memory", f"{mem_size}",
            "--vcpus", f"{vcpu_count}",
            "--osinfo", f"{os_id}",
            "--disk", f"bus=virtio,path={vm_image}",
            "--graphics", "none",
            "--console", "pty,target_type=serial",
            "--import",
            "--noautoconsole",
        ]

        if mac_address is not None:
            virt_install_cmd.extend(["--network", f"network={network},mac={mac_address}"])
        else:
            virt_install_cmd.extend(["--network", f"network={network}"])

        self.run(virt_install_cmd)


    def gen_netplan_config(self, ip: str, dnsserver: str, gateway: str) -> str:
        """
        Generate a netplan configuration file for the VM.

        Args:
            ip: The IP address of the VM.
            dnsserver: The DNS server to use.
            gateway: The gateway to use.
        """
        env = Environment(loader=FileSystemLoader("libvirt/template"))
        template = env.get_template("01-netcfg.yaml.j2")
        return template.render(ip=ip, dnsserver=dnsserver, gateway=gateway)

    def gen_authorized_keys(self):
        """
        Generate a temporary authorized_keys file from the user's SSH public keys.

        Preference order:
          1. ed25519
          2. rsa

        Returns:
            Path to the generated authorized_keys file.
        """

        home = Path(os.environ["HOME"])
        ssh_dir = home / ".ssh"

        preferred_keys = [
            ssh_dir / "id_ed25519.pub",
            ssh_dir / "id_rsa.pub",
        ]

        selected_key = None

        for key_path in preferred_keys:
            if key_path.exists() and key_path.is_file():
                selected_key = key_path
                break

        if selected_key is None:
            raise FileNotFoundError(
                "No suitable SSH public key found "
                "(looked for id_ed25519.pub and id_rsa.pub)"
            )

        tempdir = tempfile.mkdtemp(prefix="authorized_keys_")
        authorized_keys_path = Path(os.path.join(tempdir, "authorized_keys"))
        key_contents = selected_key.read_text().strip()
        authorized_keys_path.write_text(key_contents + "\n")

        # Match typical SSH permissions
        authorized_keys_path.chmod(0o600)
        return authorized_keys_path