#!/usr/bin/env bash

echo "RUNNING WITH DISPLAY ${DISPLAY} $@"
DISPLAY=$DISPLAY auv-visualizer-nodisplay "$@"
