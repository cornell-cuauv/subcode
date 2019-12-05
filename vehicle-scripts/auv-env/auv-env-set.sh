#!/bin/zsh
if [[ $TERM = "dumb" ]]; then
    bash && exit
fi

# This script must be sourced, so these variables do leak into the env...
red=`tput setaf 1`
green=`tput setaf 2`
blue=`tput setaf 4`
yellow=`tput setaf 11`
reset=`tput sgr0`

log() {
    echo "[$1$2${reset}] $3"
}


host=$1
if [ -n "$1" ]; then
    host=$1
else
    if [[ -n "$SSH_CONNECTION" ]]; then
	    # This is not a SSH session, goodbye!
        host=$(echo $SSH_CONNECTION | cut -f 1 -d " ")

        # TODO verify that DNS lookup times out if it hangs
        alt_host=$(timeout 1s dig -x $host | grep ".in-addr.arpa" | tail -n 1 | cut -f 4 | rev | cut -c 2- | rev)
    else
        return
    fi
fi

if [ -z "$AUV_ENV_DIRECTORY" ]; then
    # No global env location, using default
    AUV_ENV_DIRECTORY=$CUAUV_SOFTWARE/vehicle-scripts/auv-env
fi

log $blue INFO "Found host IP: $host"
log $blue INFO "Found hostname: $alt_host"
log $blue INFO "Using env-dir: $AUV_ENV_DIRECTORY"

# Do some mapping here (quickzand -> zander, zandstone -> zander)

if [ -n "$AUV_ENV_ALIAS" ] && [ -d "$AUV_ENV_DIRECTORY/$AUV_ENV_ALIAS" ]; then
    # This is set by auv-docker.py for loading environment locally
    log $blue INFO "AUV_ENV_ALIAS set, using alias $AUV_ENV_ALIAS"
    env_dir="$AUV_ENV_DIRECTORY/$AUV_ENV_ALIAS"
else
    env_dir="$AUV_ENV_DIRECTORY/$host"
fi

if [ ! -d "$env_dir" ]; then
    env_aliases=($AUV_ENV_DIRECTORY/*/env_aliases)
    aliased_host=$(grep ^$host\$ -H $env_aliases | awk -F "/" '{print $(NF-1)}')
    aliased_alt_host=$(grep ^$alt_host\$ -H $env_aliases | awk -F "/" '{print $(NF-1)}')
    
    if [ -n "$aliased_alt_host" ]; then
        log $blue INFO "Found hostname alias for $aliased_alt_host"
        host=$aliased_alt_host
        env_dir="$AUV_ENV_DIRECTORY/$aliased_alt_host"
    elif [ -n "$aliased_host" ]; then
        log $blue INFO "Found IP alias for $aliased_host"
        host=$aliased_host
        env_dir="$AUV_ENV_DIRECTORY/$aliased_host"
    fi
fi

if [ -d "$env_dir" ]; then
    # Load files from $env_dir
    log $green SUCCESS "Found directory $env_dir"
    
    for SCRIPT in $env_dir/*; do
        if [ -f $SCRIPT -a -x $SCRIPT ]; then
            log $blue INFO "Running script \"$SCRIPT\""
            source "$SCRIPT"
        fi
    done

    alias git-user="env_dir=$env_dir $AUV_ENV_DIRECTORY/git-user.sh"
else
    log $red FAIL "Could not find host $host"
    return
fi
