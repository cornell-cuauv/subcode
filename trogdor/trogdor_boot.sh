#!/usr/bin/env zsh

if [[ "$(uname -m)" != "aarch64" ]]; then
    exit 0
fi

sleep 10

touch /tmp/tmux-1000/default
tmux new -d -s trogdor_services
tmux send-keys -t trogdor_services.0 "trogdor start" ENTER

# CONFIGURE REMOTE WEBSERVER CONFIGS
# VEHICLE_TYPE=$CUAUV_VEHICLE_TYPE
# tmux new -d -s ssh_connection

# if [ "$VEHICLE_TYPE" = "mainsub" ]; then 
#     tmux send-keys -t ssh_connection.0 "autossh -M 43034 -NR 43033:192.168.0.100:8081 cuauv@cuauv.org -p 2224" ENTER
# elif [ "$VEHICLE_TYPE" = "minisub" ]; then
#     tmux send-keys -t ssh_connection.0 "autossh -M 43032 -NR 43031:192.168.0.93:8081 cuauv@cuauv.org -p 2224" ENTER
# fi
# sleep 5
# tmux send-keys -t ssh_connection.0 "yes" ENTER

# Don't start the mission automatically (for now) uncomment for competition
screen -d -m auv-mission-runner

# tmux new -d -s trogdor_mission
# tmux send-keys -t trogdor_mission.0 "sleep 30; auv-mission-runner" ENTER

while :; do
    sleep 60
done
