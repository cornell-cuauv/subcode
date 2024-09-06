#!/bin/bash

PORT_DIRECTORY="/dev/serial/by-id/"

if [[ ! -d $PORT_DIRECTORY ]]; then
    echo "directory $PORT_DIRECTORY dne. Check if serial is connected via USB to the Jetson"
    exit -1
fi

return_val=0
dvl_attempt() {
    TMP_FILE="/tmp/find_dvl_$1.txt"
    ERROR_MSG="no data received"
    SLEEP_TIME=8

    echo "=== Checking DVL on port $2 ==="
    (stdbuf -oL -eL auv-dvld $2 &> $TMP_FILE) & x=$!
    sleep $SLEEP_TIME
    kill $x 
    wait $! 2>/dev/null
    if [[ -z $(cat $TMP_FILE | grep "$ERROR_MSG") ]]; then
        echo "found DVL!!!"
        return_val=1
        return
    fi
    return_val=0
}



gx_attempt() {
    TMP_FILE="/tmp/find_gx_$1.txt"
    ERROR_MSG="No such file"
    SLEEP_TIME=2

    echo "=== Checking DVL on port $2 ==="
    (stdbuf -oL -eL auv-3dmgx4d $2 &> $TMP_FILE) & x=$!
    sleep $SLEEP_TIME
    kill $x
    if [[ -z $(cat $TMP_FILE | grep "$ERROR_MSG") ]]; then
        echo "found gx!!!"
        return_val=1
        return
    fi
    return_val=0
}

i=0
dvl_result=0
gx_result=0
while read line; do
    i=$((i+1))
    # if [[ $dvl_result == 0 ]]; then 
    #     dvl_attempt $i $line
    #     dvl_result=$return_val
    # fi

    if [[ $gx_result == 0 ]]; then 
        gx_attempt $i $line
        gx_result=$return_val
    fi
done < <(ls $PORT_DIRECTORY*)
