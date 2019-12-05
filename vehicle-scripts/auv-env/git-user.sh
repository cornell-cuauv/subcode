#!/usr/bin/env bash

# TODO zsh completion

SCRIPT_NAME="git-user"

if [ ! -d "$env_dir" ]; then
    echo "Cannot run $SCRIPT_NAME, AUV user environment not set up correctly"
    echo "env_dir is set to $env_dir"
    exit 1
fi

WORK_TREE="$CUAUV_SOFTWARE"
GIT_DIR="$env_dir/.git"

FLAGS="--git-dir=$GIT_DIR --work-tree=$WORK_TREE"

if [ $# -gt 1 ] && [ "$1" = "add" ] && [ ! "$2" = "-f" ]; then
    # add

    tracked=()

    for file in "${@:2}"; do
        # check to see if file is tracked in main repo
        if [ -f "$file" ] && [ `git ls-files --error-unmatch "$file" 2> /dev/null` ]; then
            tracked+=($file)
        fi
    done

    if [ ${#tracked[@]} -ne 0 ]; then
        echo ""
        echo "You are trying to add a file that is tracked by the main git repo."
        echo "It is recommended to not do this. Re-run with -f to force add."
        echo ""
        echo "Offending files:"
        for file in ${tracked[@]}; do
            echo "  $file"
        done
        echo ""

        exit 1
    fi

    # do the add, but force it because the files are ignored
    git $FLAGS add -f "${@:2}"

elif [ $# -gt 0 ] && [ "$1" = "init" ]; then
    # init

    git $FLAGS "$@"

    # ignore everything by default
    echo "*" >> "$GIT_DIR/info/exclude"

elif [ $# -gt 0 ] && [ "$1" = "destroy" ]; then
    # destroy (not a real git command)

    rm -rf $GIT_DIR

else
    # all other commands

    git $FLAGS "$@"
fi
