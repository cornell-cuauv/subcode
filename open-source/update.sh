#!/bin/bash

set -euo pipefail
LOC="$(dirname $0)"
F_EXCLUSIONS="$LOC/exclusions"
readarray -t EXCLUSIONS < "$F_EXCLUSIONS"
REPO_DIR="$1"

if [ $(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD) != "master" ]; then
    echo "Repo should probably be on master branch!" >&2
    echo -n "Continue (y/n)? " >&2
    read v
    [ "x$v" != "xy" ] && echo "Exiting." && exit 1
fi

if [ ! -d .git ]; then
    git init
    echo >> .git/info/exclude
    cat "$LOC/exclusions" >> .git/info/exclude
fi

if [ -f PRIV_COMMIT ]; then
    PREV_COMMIT="$(cat PRIV_COMMIT)"
else
    PREV_COMMIT="4b825dc642cb6eb9a060e54bf8d69288fbee4904" # "first commit"
fi

FIRST_COMMIT="218b789f9528b941f9ab093996a99b9a5e505b91"

GIT_AUTHOR_NAME="CUAUV"
GIT_AUTHOR_EMAIL="leader@cuauv.org"
GIT_COMMITTER_NAME="CUAUV"
GIT_COMMITTER_EMAIL="leader@cuauv.org"
export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL

git -C "$REPO_DIR" log $PREV_COMMIT..HEAD --format="%H %at %ai %ct %ci %s" | tac | (
#declare -a nomatch
nomatch=()
while read hash aunix_timestamp adate atime atimezone cunix_timestamp cdate ctime ctimezone message; do
    if case $message in "Merge pull request #"*) MSG="$message"; true;; *) [ $hash == $FIRST_COMMIT ] && MSG="First open-source commit";; esac; then
        git -C "$REPO_DIR" diff --binary --full-index "$PREV_COMMIT" "$hash" | git apply --whitespace=nowarn --index > /dev/null

        for ((i=0;i<${#EXCLUSIONS[@]};i++)); do
            l="${EXCLUSIONS[$i]}"
            case l in
                "#"*) continue;;
                *)
                    ll=(`echo "$REPO_DIR/$l"`) 
                    [ ${#ll[@]} == 0 ] || [ ${#ll[@]} == 1 -a ! -e "${ll[0]}" ] && nomatch[$i]="$hash" # && echo "Warning: Line \"$l\" of exclusions file matches nothing @ ${hash} (${message})"
                ;;
            esac
        done

        echo -n "$hash" > PRIV_COMMIT
        git add PRIV_COMMIT

        GIT_AUTHOR_DATE="$aunix_timestamp $atimezone" GIT_COMMIT_DATE="$cunix_timestamp $ctimezone" git commit -m "$MSG" > /dev/null

        PREV_COMMIT="$hash"
    fi
done
if [ -n ${nomatch+x} ] && [ ${#nomatch[@]} -gt 0 ]; then
    ml=0
    for ((i=0;i<${#EXCLUSIONS[@]};i++)); do
        nm="${EXCLUSIONS[$i]}"
        if [ $i -lt ${#nomatch[@]} ] && \
            [ -n ${nomatch[$i]+x} ] && [ ${#nm} -gt $ml ]; then
            ml=${#nm}
        fi
    done
    printf "%${ml}s  Last didn't match\n" "Exclusion"
    for ((i=0;i<${#EXCLUSIONS[@]};i++)); do
        #echo ${exclusions[i]}: ${nomatch[i]}
        if [ -z "${EXCLUSIONS[$i]}" ] || [ -z ${nomatch[$i]+x} ]; then continue; fi
        printf "%${ml}s  " "${EXCLUSIONS[$i]}"
        h=
        if [ "x$PREV_COMMIT" == "x${nomatch[$i]}" ]; then h=" (last)"; fi
        git --no-pager -C "$REPO_DIR" log --format="%h (%s)$h" -n1 ${nomatch[$i]}
    done
fi
)

