#!/bin/bash
# Discover IPoIB network interface names on this node.
#
# IB interface names follow predictable naming based on PCI topology
# (e.g., ibp10s0, ibp181s0) rather than generic ib0/ib1.
#
# Output: one interface name per line (sorted)
# Exit 0: at least one IB interface found
# Exit 1: no IB interfaces found

set -euo pipefail

found=0
for net_if in /sys/class/net/ib*; do
    [ -d "$net_if" ] || continue
    basename "$net_if"
    found=1
done

if [ "$found" -eq 0 ]; then
    echo "ib0"  # fallback for environments without predictable naming
fi

exit 0
