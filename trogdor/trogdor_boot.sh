#!/usr/bin/env bash

if [[ "$(uname -m)" != "aarch64" ]]; then
    exit 0
fi

trogdor start

sleep 30

# Don't start the mission automatically (for now) uncomment for competition
# screen -d -m auv-mission-runner
