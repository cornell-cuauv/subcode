#!/usr/bin/env bash

# Hack to allow devices to appear in /dev when running on boot.
early=$(echo "$(cat /proc/uptime | cut -d' ' -f 1) < 10" | bc)

if [[ $early = "1" ]]; then
  sleep 10
fi

# CONFIGURATION

ROOT=$CUAUV_SOFTWARE
LOGS=$CUAUV_LOG/current # Should be set up by auv-pooltest
BIN=$ROOT/link-stage

mkdir -p $LOGS

# Very important variables
export PATH=$PATH:$ROOT/link-stage
export PYTHONPATH=$ROOT

# PORT MAPPINGS

VEHICLE_TYPE=$CUAUV_VEHICLE_TYPE
if [ "$VEHICLE_TYPE" = "minisub" ]; then
	GX_PORT=$(readlink -f /dev/serial/by-id/usb-CUAUV_Polaris_FTDI2_AUV-POLARIS2-if00-port0)
elif [ "$VEHICLE_TYPE" = "mainsub" ]; then # TODO: NEED NEW SERIAL.
	GX_PORT=$(readlink -f /dev/serial/by-id/usb-CUAUV_Sirius_FTDI3_AUV-SIRIUS3-if00-port0)
fi
DVL_PORT=/dev/serial/by-id/usb-CUAUV_Sirius_FTDI1_AUV-SIRIUS1-if01-port0

# CONFIGS

VISION_CONFIG=$ROOT/vision/configs/master.yaml

# SERVICES


if [ "$VEHICLE_TYPE" = "mainsub" ]; then
  SERVICES=(seriald gx4d kalmand navigated controld3 shmserver
  zed webgui modules pingerd dvld deadman log redis)
elif [ "$VEHICLE_TYPE" = "minisub" ]; then
  SERVICES=(seriald gx4d kalmand navigated controld3 shmserver
  webgui modules pingerd deadman log redis
  )
else
  echo "Unsupported CUAUV_VEHICLE_TYPE! Must be set to one of { mainsub, minisub }!"
fi

# COLORS

GRAY="\033[0;30m"
CYAN="\033[0;36m"
RED="\033[1;31m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
GREEN="\033[1;32m"
ENDCOLOR="\033[0m"

# FUNCTIONS

log () {
  STR="[$CYAN`date -u +"%Y/%m/%d %H:%M:%S UTC"`$ENDCOLOR] ($YELLOW""TROGDOR""$ENDCOLOR) $1"
  echo -e $STR
  echo $STR &>> $LOGS/trogdor.log
}

invoke () {
  log "Invoking \"$1\"."
  $1
}

fork () {
  log "Forking \"$1 &> $LOGS/$2.log\"."
  echo "Starting $1 at `date -u +"%Y/%m/%d %H:%M:%S UTC"`" >> $LOGS/$2.log
  # Handle optional filter command argument
  if [ $# -ge 3 ]; then
    stdbuf -oL -eL $1 | $3 &>> $LOGS/$2.log &
  else
    stdbuf -oL -eL $1 &>> $LOGS/$2.log &
  fi
}

set_priority() {
  sudo renice -n $2 $(pgrep -f $1)
}

pkill () {
  log "Killing \"$1\"."
  PIDS=`pids $1`
  if [ -z "$PIDS" ]; then
      log "No PIDs found for \"$1\"."
  else
      invoke "kill $PIDS"
  fi
}

ckill () {
  log "Killing \"$1\"."
  PIDS=`pids $1`
  if [ -z "$PIDS" ]; then
      log "No PIDs found for \"$1\"."
  else
      invoke "kill -SIGINT $PIDS"
  fi
}

pids () {
  pgrep -fl "$*" | grep -v "grep" | grep -v "vim" | grep -v "emacs" | cut -d' ' -f1
}

usage () {
  echo "Usage: {t / trogdor} {start | stop | restart | status} SERVICE"
}

servicestatus () {
  if [ -z "`pids $1`" ]; then
    log "$RED""$2""$ENDCOLOR"
  else
    log "$GREEN""$2""$ENDCOLOR"
  fi
}

assertservice () {
  if [ -z "`pids $2`" ]; then
    log "$1 seems to be ""$RED""DOWN""$ENDCOLOR""; restarting."
    trogdor hidden_start $1
  else
    log "$1 seems to be ""$GREEN""UP""$ENDCOLOR""."
  fi
}

COMMAND=$1
SERVICE=$2

# for auto complete
if [ "$COMMAND" == "list" ]; then
    printf "%s\n" "${SERVICES[@]}"
    exit 0
fi

if [ -z "$COMMAND" ]; then
    COMMAND="status"
fi

if [ -z "$SERVICE" ]; then
    log "No service specified; executing on all known."
    for SERVICE in ${SERVICES[@]}
    do
        trogdor $COMMAND $SERVICE
    done
    exit 0
fi

case $COMMAND in
    hidden_start)
        case $SERVICE in
            aslam|aslamd) fork "auv-aslamd" "aslamd" ;;
            linearizer|linearizerd) fork "auv-linearizerd" "linearizerd" ;;
            seriald|serial) fork "auv-seriald" "seriald" ;;
            gx4d|gx4) fork "auv-3dmgx4d $GX_PORT" "gx4d" "grep -v '^[0-9]\+$'" ;;
            gx1d|gx1) fork "auv-3dmgd $GX_PORT" "gx1d" ;;
            dvld|dvl) fork "auv-dvld $DVL_PORT" "dvld" ;;
            kalmand|kalman) fork "auv-kalman3d" "kalmand" && sleep 0.5 && set_priority "auv-kalman3d" "-19" ;;
            navigated|navigate) fork "auv-navigated" "navigated" ;;
            controld3|controld|control) fork "auv-controld3" "controld3" && sleep 0.5 && set_priority "auv-controld3" "-19" ;;
            shmserver) fork "auv-shm server" "shmserver" ;;
            log|logs|logger|logging) fork "auv-ld" "auv-ld" ;;
            led) fork "auv-led daemon" "led" ;;
            deadman) fork "auv-deadman" "deadman" ;;
            webgui) invoke "cd /home/software/cuauv/software/webserver" && fork "auv-webserver" "webserver" ;;
            # webgui-remote) invoke "cd /home/software/cuauv/software/webserver-remote" && fork "auv-webserver-remote" "webserver-remote" ;; 
            pinger|pingerd) fork "auv-pingerd" "pingerd" ;;
            zed) fork "auv-zed-camera" "zed";;
            modules) fork "auv-start-modules" "start-modules" ;;
            led|leds) fork "auv-led daemon" "led" ;;
            hardkill) fork "auv-kill" "hardkill";;
            redis) fork "redis-server" "redis" ;;
            *) log "Service \"$SERVICE\" not found; aborting." ;;
        esac
    ;;

    stop)
        case $SERVICE in
            aslam|aslamd) pkill "auv-aslamd" ;;
            linearizer|linearizerd) pkill "auv-linearizerd" ;;
            seriald|serial) pkill "auv-seriald" ;;
            gx4d|gx4) pkill "auv-3dmgx4d" ;;
            gx1d|gx1) pkill "auv-3dmgd" ;;
            dvld|dvl) pkill "auv-dvld" ;;
            kalmand|kalman) pkill "auv-kalman3d" ;;
            navigated|navigate) pkill "auv-navigated" ;;
            controld3|controld|control) pkill "auv-controld3" ;;
            shmserver) pkill "auv-shm server" ;;
            log|logs|logger|logging) pkill "auv-ld" ;;
            led) pkill "/home/software/misc/led.py" ;;
            deadman) pkill "auv-deadman" ;;
            webgui) ckill "auv-webserver" ;;
            # webgui-remote) pkill "auv-webserver-remote" ;;
            pinger|pingerd) pkill "auv-pingerd" ;;
            zed) pkill "auv-zed-camera" ;; 
            modules) pkill "auv-start-modules" ;;
            led|leds) pkill "auv-led" ;;
            hardkill) pkill "auv-kill" ;;
            redis) pkill "redis-server" ;;
            *) log "Service \"$SERVICE\" not found; aborting." ;;
        esac
    ;;

    restart)
        case $SERVICE in
          seriald|serial)
            trogdor stop $SERVICE
            sleep 3
            trogdor hidden_start $SERVICE
          ;;
          *)
            trogdor stop $SERVICE
            trogdor hidden_start $SERVICE
          ;;
        esac
    ;;

    status)
        case $SERVICE in
            aslamd|aslam) servicestatus "auv-aslamd" "aslamd" ;;
            linearizer|linearizerd) servicestatus "auv-linearizerd" "linearizerd" ;;
            seriald|serial) servicestatus "auv-seriald" "seriald" ;;
            gx4d|gx4) servicestatus "auv-3dmgx4d" "gx4d" ;;
            gx1d|gx1) servicestatus "auv-3dmgd" "gx1d" ;;
            dvld|dvl) servicestatus "auv-dvld" "dvld" ;;
            kalmand|kalman) servicestatus "auv-kalman3d" "kalmand" ;;
            navigated|navigate) servicestatus "auv-navigated" "navigated" ;;
            controld3|controld|control) servicestatus "auv-controld3" "controld3" ;;
            log|logs|logger|logging) servicestatus "auv-ld" "logging" ;;
            shmserver) servicestatus "auv-shm server" "shmserver" ;;
            # led) servicestatus "/home/software/trunk/misc/hydro_reset.py" "led" ;;
            deadman) servicestatus "auv-deadman" "deadman" ;;
            webgui) servicestatus "auv-webserver" "webgui" ;;
            # webgui-remote) servicestatus "auv-webserver-remote" "webgui-remote" ;;
            pinger|pingerd) servicestatus "auv-pingerd" "pingerd" ;;
            zed) servicestatus "auv-zed-camera" "zed" ;;
            modules) servicestatus "auv-start-modules" "modules" ;;
            # led|leds) servicestatus "auv-led" "led" ;;
            hardkill) servicestatus "auv-kill" "hardkill" ;;
            redis) servicestatus "redis-server" "redis" ;;
            *) log "Service \"$SERVICE\" not found; aborting." ;;
        esac
    ;;

    start)
        case $SERVICE in
            aslamd|aslam) assertservice "aslamd" "auv-aslamd" ;;
            linearizer|linearizerd) assertservice "linearizerd" "auv-linearizerd" ;;
            seriald|serial) assertservice "serial" "auv-seriald" ;;
            gx4d|gx4) assertservice "gx4d" "auv-3dmgx4d $GX4_PORT" ;;
            gx1d|gx1) assertservice "gx1d" "auv-3dmgd $GX1_PORT" ;;
            dvld|dvl) assertservice "dvld" "auv-dvld $DVL_PORT" ;;
            kalmand|kalman) assertservice "kalmand" "auv-kalman3d" ;;
            navigated|navigate) assertservice "navigated" "auv-navigated" ;;
            controld3|controld|control) assertservice "controld3" "auv-controld3" ;;
            log|logs|logger|logging) assertservice "logging" "auv-ld" ;;
            shmserver) assertservice "shmserver" "auv-shm server" ;;
            # led) assertservice "led" "auv-led daemon" ;;
            deadman) assertservice "deadman" "auv-deadman" ;;
            webgui) assertservice "webgui" "auv-webserver" ;;
            # webgui-remote) assertservice "webgui-remote" "auv-webserver-remote" ;;
            pinger|pingerd) assertservice "pingerd" "auv-pingerd" ;;
            zed) assertservice "zed" "auv-zed-camera" ;;
            modules) assertservice "modules" "auv-start-modules" ;;
            hardkill) assertservice "hardkill" "auv-kill" ;;
            led|leds) fork "auv-led daemon" "led";;
            redis) assertservice "redis" "redis-server" ;;
            *) log "Service \"$SERVICE\" not found; aborting." ;;
        esac
    ;;

    *)
        usage
    ;;
esac
