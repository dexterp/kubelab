#!/usr/bin/env perl

use strict;
use warnings;
use feature 'say';

use Getopt::Long qw(GetOptions);

# -----------------------------------------------------------------------------
# Kubernetes IPVS DR Backend Configuration
#
# Uses:
#   - loopback interface (lo)
#   - VIP /32 address
#   - ARP suppression
#
# Intended for:
#   Keepalived + IPVS Direct Return mode
#
# Example:
#   sudo configure-k8s-dr-backend.pl \
#       --vip 192.168.1.50
#
# -----------------------------------------------------------------------------

my $vip;

GetOptions(
    'vip=s' => \$vip,
) or die usage();

validate();
ensure_root();

load_dummy_requirements();
create_netplan();
create_sysctl();
apply_configuration();

say "";
say "========================================";
say "Kubernetes DR backend configured";
say "========================================";
say "VIP       : $vip";
say "Interface : lo";
say "";

exit 0;

# -----------------------------------------------------------------------------

sub usage {

    return <<"EOF";
Usage:
  $0 --vip <ip>

Example:
  $0 --vip 192.168.1.50
EOF
}

sub validate {

    die usage() unless $vip;
}

sub ensure_root {

    if ($> != 0) {
        die "This script must be run as root\n";
    }
}

sub run_cmd {

    my ($cmd) = @_;

    say ">>> $cmd";

    system($cmd);

    if ($? != 0) {
        die "Command failed: $cmd\n";
    }
}

sub load_dummy_requirements {

    say "";
    say "Ensuring loopback interface exists...";

    run_cmd('ip link set lo up');
}

sub create_netplan {

    say "";
    say "Creating Netplan configuration...";

    my $netplan = <<"EOF";
network:
  version: 2
  renderer: networkd
  ethernets:
    lo:
      addresses:
        - $vip/24
EOF

    my $file = '/etc/netplan/99-k8s-dr-vip.yaml';

    open(my $fh, '>', $file)
        or die "Unable to write $file: $!\n";

    print $fh $netplan;

    close($fh);
    chmod (0600, $file);
}

sub create_sysctl {

    say "";
    say "Creating sysctl configuration...";

    my $sysctl = <<"EOF";
# Kubernetes IPVS DR backend configuration

# Prevent loopback VIP from replying to ARP
net.ipv4.conf.lo.arp_ignore = 1
net.ipv4.conf.lo.arp_announce = 2

# Global ARP suppression
net.ipv4.conf.all.arp_ignore = 1
net.ipv4.conf.all.arp_announce = 2

# Defaults for future interfaces
net.ipv4.conf.default.arp_ignore = 1
net.ipv4.conf.default.arp_announce = 2

# Allow binding non-local addresses
net.ipv4.ip_nonlocal_bind = 1

# Recommended for DR mode
net.ipv4.conf.all.rp_filter = 0
net.ipv4.conf.default.rp_filter = 0
EOF

    my $file = '/etc/sysctl.d/99-k8s-ipvs-dr.conf';

    open(my $fh, '>', $file)
        or die "Unable to write $file: $!\n";

    print $fh $sysctl;

    close($fh);
}

sub apply_configuration {

    say "";
    say "Applying Netplan...";

    run_cmd('netplan generate');
    run_cmd('netplan apply');

    say "";
    say "Applying sysctl settings...";

    run_cmd('sysctl --system');
}
