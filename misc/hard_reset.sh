
BRANCH="$(git symbolic-ref HEAD | cut -f 3 -d /)"
if [ "$BRANCH" = "master" ]; then
    git fetch origin master
    git checkout --force -B master origin/master
    git reset --hard
    git clean -fdx
<<<<<<< HEAD
=======
    git submodule update --init --recursive --force
    git submodule foreach git fetch
    git submodule foreach git checkout --force -B master origin/master
    git submodule foreach git reset --hard
    git submodule foreach git clean -fdx
>>>>>>> added hard reset script
else
    echo "Error: auv-hard-reset can only be used on the master branch."
fi
