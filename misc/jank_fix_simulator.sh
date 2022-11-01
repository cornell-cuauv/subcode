#!/bin/bash
echo "Note that this file should be sourced for it to work"
echo "----------------------------------------------------"
i=0
while read line; do
    i=$((i+1))
    if [[ $i -gt 3 ]]; then
        shm kalman $line 0
    fi
done < <(shm kalman |  awk '{print $1}')
i=0
while read line; do
    i=$((i+1))
    if [[ $i -gt 3 ]]; then
        shm navigation_desires $line 0
    fi
done < <(shm navigation_desires |  awk '{print $1}')
unset $i
echo "we are done:"

