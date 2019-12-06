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
EXCLUDE_FILE="$GIT_DIR/info/exclude"

FLAGS="--git-dir=$GIT_DIR --work-tree=$WORK_TREE"

TRACKED_WARNING_NUM=20

if [ $# -gt 0 ] && [ "$1" = "add" ]; then
    args=""
    force=0

    # search for "-x" and remove it from args
    # this way the -x flag can appear anywhere in the arguments
    for arg in "${@:2}"; do
        if [ "$arg" = "-x" ]; then
            force=1
        else
            args+=$arg
            args+=" "
        fi
    done

    # everything is ignored by default
    # just for this command, disable the ignore rule so that we can add files
    # the alternative is passing -f to force add
    # but that approach doesn't respect directory-specific .gitignores
    trap 'echo "*" > "$EXCLUDE_FILE"' EXIT
    echo "" > "$EXCLUDE_FILE"

    if [ $force -eq 0 ]; then
        # find all files that would be added
        mapfile -t dry_run < <(git $FLAGS add -n $args 2> /dev/null)

        tracked=()

        for dry_run_line in "${dry_run[@]}"; do
            # dry run outputs lines like "add 'path/to/filename'"
            file=${dry_run_line:5:$((${#dry_run_line}-6))}

            exists=$([ -f "$file" ])
            tracked_main=`git ls-files --error-unmatch "$WORK_TREE/$file" 2> /dev/null`
            tracked_user=`git $FLAGS ls-files --error-unmatch "$WORK_TREE/$file" 2> /dev/null`

            # check to see if file is tracked in main repo
            # but ignore if already tracked in the user repo
            if $exists && [ $tracked_main ] && [ ! $tracked_user ]; then
                tracked+=($file)
            fi
        done

        if [ ${#tracked[@]} -ne 0 ]; then
            echo ""
            echo "You are trying to add a file that is tracked by the main git repo."
            echo "It is recommended to not do this. Re-run with -x to force add."
            echo ""
            echo "Offending files:"
            # only show up to TRACKED_WARNING_NUM
            for file in ${tracked[@]:0:$TRACKED_WARNING_NUM}; do
                echo "  $file"
            done
            # if we truncated the list, show an ellipsis
            if [ ${#tracked[@]} -gt $TRACKED_WARNING_NUM ]; then
                echo "  ..."
                echo ""
                echo "[$((${#tracked[@]} - $TRACKED_WARNING_NUM)) other files not shown]"
            fi
            echo ""

            exit 1
        fi
    fi

    # do the add
    git $FLAGS add $args

elif [ $# -gt 0 ] && [ "$1" = "init" ]; then
    # init

    git $FLAGS "$@"

    # ignore everything by default
    echo "*" > "$EXCLUDE_FILE"

elif [ $# -gt 0 ] && [ "$1" = "destroy" ]; then
    # destroy (not a real git command)

    rm -rf $GIT_DIR

else
    # all other commands

    git $FLAGS "$@"
fi
