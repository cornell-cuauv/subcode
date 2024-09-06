#!/usr/bin/env bash

if [[ -z $(uname -a | grep "tegra") ]]; then
    echo "Skipping Jetson install because arch is $(uname -a)"
    exit 0
fi

echo "DETECTED JETSON. CONTINUING INSTALLATION"
. $@
