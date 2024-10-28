#!/bin/bash

# This script checks for active apt locks on an Ubuntu system.
# It verifies if the following lock files are held:
# - /var/lib/apt/lists
# - /var/lib/dpkg/lock
# - /var/lib/dpkg/lock-frontend
# If any locks are found, it outputs a message and exits with a status of 1.
# If no locks are held, it outputs a confirmation message and exits with a status of 0.


# Check if /var/lib/apt/lists lock is held
if fuser /var/lib/apt/lists >/dev/null 2>&1; then
  echo "/var/lib/apt/lists is locked"
  exit 1
fi

# Check if /var/lib/dpkg/lock is held
if fuser /var/lib/dpkg/lock >/dev/null 2>&1; then
  echo "/var/lib/dpkg/lock is locked"
  exit 1
fi

# Check if /var/lib/dpkg/lock-frontend is held
if fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; then
  echo "/var/lib/dpkg/lock-frontend is locked"
  exit 1
fi

# If no lock is held
echo "No APT locks are held"
exit 0
