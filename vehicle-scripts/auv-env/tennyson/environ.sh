#!/usr/bin/env bash

if [[ $TERM = "dumb" ]]; then
    bash && exit
fi

export EMAIL='tennysontaylorbardwell@gmail.com'
export NAME='Tennyson T Bardwell'

export GIT_AUTHOR_NAME=$NAME
export GIT_AUTHOR_EMAIL=$EMAIL
export GIT_COMMITTER_NAME=$NAME
export GIT_COMMITTER_EMAIL=$EMAIL

export EDITOR="emacsclient -nw -c"
export VISUAL=$EDITOR
alias emc=$VISUAL
