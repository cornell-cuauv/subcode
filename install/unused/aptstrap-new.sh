#!/usr/bin/env bash
set -xeuo pipefail
export DEBIAN_FRONTEND=noninteractive
. $@
rm -rf  /tmp/* /var/tmp/* /root/.cache/
