#!/usr/bin/env bash

if [[ $TERM = "dumb" ]]; then
    bash && exit
fi

export MY_EMAIL='tennysontaylorbardwell@gmail.com'
export MY_NAME='Tennyson T Bardwell'

export GIT_AUTHOR_NAME=$MY_NAME
export GIT_AUTHOR_EMAIL=$MY_EMAIL
export GIT_COMMITTER_NAME=$MY_NAME
export GIT_COMMITTER_EMAIL=$MY_EMAIL

export EDITOR="emacsclient -nw -c"
export VISUAL=$EDITOR
alias emc=$VISUAL
