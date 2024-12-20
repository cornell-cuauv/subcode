#!/usr/bin/env python3

# TODO: Update documentation style with clize 3.1

def check_imports(*names):
    not_found = []
    for name in names:
        try:
            __import__(name)
        except ImportError:
            not_found.append(name)

    if len(not_found) > 0:
        print(('\nauv-docker requires these packages: {}\n'
              + 'Install with "pip3 install {}"\n')
              .format(', '.join(not_found), ' '.join(not_found)))
        quit()

check_imports('docker', 'clize')

import os
from pathlib import Path
import socket
import subprocess
import time

import clize
import docker
from docker.errors import ContainerError, ImageNotFound, APIError, NotFound

from config import get_config

WORKSPACE_DIRECTORY=get_config("WORKSPACE_DIRECTORY")
CONTAINER_WORKSPACE_DIRECTORY=get_config("CONTAINER_WORKSPACE_DIRECTORY")
REPO_URL=get_config("GIT_REPO_URL")
BRANCH=get_config("BRANCH")
DOCKER_REPO=get_config("DOCKER_REPO")
DOCKER_REPO_JETSON=get_config("DOCKER_REPO_JETSON")
GROUP_ID=get_config("GROUP_ID")
AUV_ENV_ALIAS=get_config("AUV_ENV_ALIAS")

GUARD_DIRECTORY = WORKSPACE_DIRECTORY / ".guards"
REPO_PATH = WORKSPACE_DIRECTORY / "repo"
CONFIGS_DIRECTORY = WORKSPACE_DIRECTORY / "configs"
WORKTREES_DIRECTORY = WORKSPACE_DIRECTORY / "worktrees"
LOGS_DIRECTORY = WORKSPACE_DIRECTORY / "logs"
VIDEOS_DIRECTORY = WORKSPACE_DIRECTORY / "videos"
STORAGE_DIRECTORY = WORKSPACE_DIRECTORY / "container_storage"

NAME_CONFIG_PATH = CONFIGS_DIRECTORY / "name"
EMAIL_CONFIG_PATH = CONFIGS_DIRECTORY / "email"


CUAUV_CONTAINER_PREFIX = 'cuauv-workspace-'

try:
    client = docker.from_env()
except docker.errors.DockerException as e:
    print("Error connecting to docker daemon: {}".format(e))
    print("Make sure docker is installed and running")
    print("If you are on WSL2, make sure you have enabled docker integration and have docker desktop open")
    quit()


def guarded_call(name, function, message=None):
    """
    Run a function once by creating a guard file on first run
    """
    GUARD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    guard_file = GUARD_DIRECTORY / name

    if not guard_file.exists():
        if message is None:
            print("Running {}".format(name))
        function()
        guard_file.touch()


def remove_guard(name):
    """
    Removes a guard created via guarded_call()
    """
    guard_file = GUARD_DIRECTORY / name

    if guard_file.exists():
        guard_file.unlink()


def get_worktree_guard(branch: str) -> str:
    return "worktree_{}".format(branch)


def check_output(args, cwd):
    return subprocess.check_output(args, cwd=cwd).decode("utf-8").strip()


def get_docker_name(branch: str, vehicle: bool):
    if vehicle:
        return "cuauv_vehicle"
    else:
        return "{}{}".format(CUAUV_CONTAINER_PREFIX, branch)


def get_containers(docker_name: str):
    running = client.containers.list(filters={"name": "^/{}$".format(docker_name)})
    return running


def init(*, on_vehicle=False, set_permissions=False):
    """
    Initialize the CUAUV workspaces filesystem structure. This should be run
    before any other workspace command.

    on_vehicle: If True, the workspace will be structured to be run
    directly on a vehicle.
    """

    def create_directories():
        WORKSPACE_DIRECTORY.mkdir(exist_ok=True)
        GUARD_DIRECTORY.mkdir(exist_ok=True)
        WORKTREES_DIRECTORY.mkdir(exist_ok=True)
        LOGS_DIRECTORY.mkdir(exist_ok=True)
        CONFIGS_DIRECTORY.mkdir(exist_ok=True)
        STORAGE_DIRECTORY.mkdir(exist_ok=True)

        # Adds a user group to be shared both inside and outside the docker
        # file and changes the workspace directory group ownership
        if set_permissions:
            group_exists = subprocess.run(
                ["getent", "group", str(GROUP_ID)],
                stdout=subprocess.PIPE,
                encoding="utf-8"
            )

            if group_exists.returncode == 0:
                print(("GID {} already exists on the system. Are you sure you "
                       "want the workspace owned by this GID? [y/n]").format(str(GROUP_ID)))
                if input() != "y":
                    raise Exception

            subprocess.run(
                ["setfacl", "-dR", "-m", "g:{}:rwX".format(str(GROUP_ID)), str(WORKSPACE_DIRECTORY)],
                check=True
            )

            subprocess.run(
                ["setfacl", "-R", "-m", "g:{}:rwX".format(str(GROUP_ID)), str(WORKSPACE_DIRECTORY)],
                check=True
            )

            print(("The workspace is now owned by GID {}. To use permissions, "
                   "create a group with that GID and add yourself to it.").format(str(GROUP_ID)))


    guarded_call(
        "create_workspace_directory",
        create_directories,
        "Creating CUAUV Docker Workspace directory"
    )

    if not on_vehicle:
        def get_initial_configs():
            confirmed = False

            while not confirmed:
                name = input("Enter your name: ")
                email = input("Enter your email (including @cornell.edu): ")

                print()
                print("Name: {}".format(name))
                print("Email: {}".format(email))
                confirmed = input("Is this information correct? [yn]") == "y"

                NAME_CONFIG_PATH.write_text(name)
                EMAIL_CONFIG_PATH.write_text(email)

        guarded_call(
            "get_initial_configs",
            get_initial_configs,
            "Prompting user for initial configurations"
        )

    def clone_repo():
        cwd = os.path.dirname(os.path.realpath(__file__))
        try:
            current_git_repo = check_output(["git", "rev-parse", "--show-toplevel"], cwd)
        except subprocess.CalledProcessError:
            current_git_repo = None
        if current_git_repo and check_output(["git", "remote", "get-url", "origin"], cwd) == REPO_URL:
            # If already in main repository, then move it to repo path
            subprocess.run(
                ["mv", current_git_repo, str(REPO_PATH)],
                check=True
            )
            print("mv {} {}".format(current_git_repo, str(REPO_PATH)))
        else:
            # Otherwise, clone main repository
            subprocess.run(
                ["git", "clone", REPO_URL, str(REPO_PATH)],
                check=True
            )

        if not on_vehicle:
            # Configure user name and email for git in repo directory
            subprocess.run(
                ["git", "config", "user.name", "\"{}\"".format(NAME_CONFIG_PATH.read_text())],
                cwd=str(REPO_PATH),
                check=True
            )

            subprocess.run(
                ["git", "config", "user.email", "\"{}\"".format(EMAIL_CONFIG_PATH.read_text())],
                cwd=str(REPO_PATH),
                check=True
            )

        if set_permissions:
            subprocess.run(
                ["setfacl", "-dR", "-m", "g:{}:rwX".format(str(GROUP_ID)), str(REPO_PATH)],
                check=True
            )
            subprocess.run(
                ["setfacl", "-R", "-m", "g:{}:rwX".format(str(GROUP_ID)), str(REPO_PATH)],
                check=True
            )

    guarded_call(
        "clone_repo",
        clone_repo,
        "Cloning repo"
    )

    def clone_videos_repo():
        if VIDEOS_DIRECTORY.exists():
            print(f"Removing existing {VIDEOS_DIRECTORY} directory...")
            subprocess.run(["rm", "-rf", str(VIDEOS_DIRECTORY)], check=True)
        
        print(f"Cloning videos repository into {VIDEOS_DIRECTORY}...")
        subprocess.run(
            ["git", "clone", "git@github.coecis.cornell.edu:CUAUV/videos.git", str(VIDEOS_DIRECTORY)],
            check=True
        )
    
    guarded_call(
        "clone_videos_repo",
        clone_videos_repo,
        "Cloning videos repository"
    )

    def set_git_configs():
        subprocess.run(
            ["git", "config", "push.default", "simple"],
            cwd=str(REPO_PATH),
            check=True
        )

        subprocess.run(
            ["git", "config", "pull.rebase", "true"],
            cwd=str(REPO_PATH),
            check=True
        )

        subprocess.run(
            ["git", "config", "rebase.autostash", "true"],
            cwd=str(REPO_PATH),
            check=True
        )

    guarded_call(
        "set_git_configs",
        set_git_configs,
        "Setting Git configs"
    )


def create_worktree(branch=BRANCH, print_help=True, *, b=False):
    """
    Sets up a worktree directory for a branch.

    branch: Branch workspace to use.

    print_help: Defaults to True. If False, will not print help afterwards.

    b: True to create and push a new branch.
    """
    # If using master branch, then simply symlink to the existing clone

    branch_directory = WORKTREES_DIRECTORY / branch

    def _create_worktree():
        if branch == "master":
            def symlink_master():
                branch_directory.symlink_to("../repo", target_is_directory=True)

            guarded_call("symlink_master", symlink_master, "Symlinking workspace for master")

        else:
            if b:
                subprocess.run(
                    ["git", "worktree", "add", str(branch_directory), "-b", branch],
                    cwd=str(REPO_PATH),
                    check=True,
                )

                subprocess.run(
                    ["git", "push", "-u", "origin", branch],
                    cwd=str(REPO_PATH),
                    check=True,
                )
            else:
                subprocess.run(
                    ["git", "fetch", "origin", "{}:{}".format(branch, branch), "--"],
                    cwd=str(REPO_PATH),
                    check=True,
                )

                subprocess.run(
                    ["git", "worktree", "add", str(branch_directory), branch],
                    cwd=str(REPO_PATH),
                    check=True,
                )

                subprocess.run(
                    ["git", "branch", "-u", "origin/{}".format(branch), branch],
                    cwd=str(REPO_PATH),
                    check=True,
                )

            # Change git paths to relative paths so they work inside the docker container
            (branch_directory / ".git").write_text("gitdir: ../../repo/.git/worktrees/{}".format(branch))
            (REPO_PATH / ".git" / "worktrees" / branch / "gitdir").write_text("../worktrees/{}".format(branch))

    guarded_call(
        get_worktree_guard(branch),
        _create_worktree,
        "Creating workspace for branch {}".format(branch)
    )

    if print_help:
        print('\nYou can now run this command to move to the worktree:\n\n' +
              'cd {}\n\n'.format(branch_directory) +
              'Add this line to your .bashrc or .zshrc for a shortcut:\n\n' +
              'ccd() {\n' +
              '    $HOME/cuauv/workspaces/repo/docker/auv-docker.py create-worktree $1 False\n' +
              '    cd $HOME/cuauv/workspaces/worktrees/$1\n' +
              '}\n'
        )


def start(*, branch:"b"=BRANCH, gpu=True, env=None, vehicle=False, mount_gpu=False, ports=None):
    """
    Starts a Docker container with the proper configuration. This does not
    currently recreate a container if different configurations options are
    passed.

    branch: Branch workspace to use.

    gpu: If True, the GPU device will be mounted into the container and
    all windows will be rendered directly to the host X server (bypassing SSH X
    forwarding).

    env: Extra environment variables to inject into the container.

    vehicle: Indicates the container should be configured to run
    directly on a vehicle.

    mount_gpu: If True, the GPU device will be mounted into the container.
    """

    create_worktree(branch, print_help=False)

    docker_name = get_docker_name(branch, vehicle)
    running = get_containers(docker_name)

    if not running:
        print("Starting new container")

        software_path = CONTAINER_WORKSPACE_DIRECTORY / "worktrees" / branch


        docker_args = {
            "image": "{}:{}".format(DOCKER_REPO, branch),
            "command": ["bash", "-c", "mkdir -p /run/sshd && /sbin/sshd && sleep infinity"],
            "user": "root",
            "detach": True,
            "environment": {
                "software_path": str(software_path),
                "CUAUV_SOFTWARE": "{}/".format(software_path),
                "CUAUV_LOCALE": "simulator",
                "CUAUV_VEHICLE": "polaris",
                "CUAUV_VEHICLE_TYPE": "mainsub",
                "CUAUV_CONTEXT": "development",
                "VISION_TEST_PATH": str(CONTAINER_WORKSPACE_DIRECTORY / "videos"),
                "CUAUV_LOG": str(CONTAINER_WORKSPACE_DIRECTORY / "logs"),
                "TERM": "xterm",
                "AUV_ENV_ALIAS": AUV_ENV_ALIAS,
            },
            "hostname": docker_name,
            "name": docker_name,
            "remove": True,
            "volumes": {
                str(WORKSPACE_DIRECTORY): {
                    "bind": str(CONTAINER_WORKSPACE_DIRECTORY),
                    "mode": "rw",
                },
                str(Path.home() / ".ssh/id_rsa.pub"): {
                    "bind": "/home/software/.ssh/id_rsa.pub",
                    "mode": "ro",  # Read-only for security
                },
                str(Path.home() / ".ssh/id_rsa"): {
                    "bind": "/home/software/.ssh/id_rsa",
                    "mode": "ro",  # Read-only for security
                },
            },
            "devices": [],
            "shm_size": "7G",
            "security_opt": ["seccomp=unconfined"], # for gdb
        }


        # no need to set ports if network_mode is host
        if ports and not vehicle:
            docker_args["ports"] = ports

        if gpu:
            subprocess.run(["xhost", "+local:"])
            docker_args["environment"]["DISPLAY"] = os.getenv("DISPLAY")
            docker_args["volumes"]["/tmp/.X11-unix/X0"] = {
                "bind": "/tmp/.X11-unix/X0",
                "mode": "rw",
            }
            docker_args["devices"] += ["/dev/dri:/dev/dri:rw"]
            
        if mount_gpu:
            docker_args["device_requests"] = [docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])]

        if vehicle:
            
            docker_args["image"] = "{}:{}".format(DOCKER_REPO_JETSON, branch)
            docker_args["volumes"]["/dev"] = {
                "bind": "/dev",
                "mode": "rw",
            }
            docker_args["volumes"][str(REPO_PATH / "misc/sshd_config")] = {
                    "bind": "/etc/ssh/sshd_config",
                    "mode": "rw"
            }
            docker_args["devices"] += ['/dev/snd', '/dev/bus/usb']
            
            docker_args["volumes"]["/home/software/sdcard"] = {
                "bind": "/home/software/sdcard",
                "mode": "rw",
            }
            docker_args["volumes"]["/home/software/mounts/local/zed/resources"] = {
                "bind": "/usr/local/zed/resources",
                "mode": "rw",
            }

            docker_args["network_mode"] = "host"
            docker_args["privileged"] = True
            docker_args["hostname"] = env["CUAUV_VEHICLE"]
            docker_args["runtime"] = "nvidia"

            
        if env:
            docker_args["environment"].update(env)

        print("Actually starting new container")
        try:
            container = client.containers.run(**docker_args)
            time.sleep(2)  # Give some time for the container to initialize

            try:
                container.reload()  # Attempt to reload the container's status
            except NotFound:
                print("Container was not found after starting. It may have exited or been removed.")
                return None

            # If the container is found but has exited
            if container.status == 'exited':
                exit_status = container.attrs['State']['ExitCode']
                print(f"Container exited immediately with status code: {exit_status}")
                logs = container.logs().decode('utf-8')
                print("Container logs:\n", logs)
                return None
            else:
                print("Container started successfully.")

            # Your existing exec_run commands and setup...
            # Ensure to wrap these in try-except blocks as well, logging any exceptions.

        except (ContainerError, ImageNotFound, APIError) as e:
            print(f"An error occurred: {e}")
            return None

        env_parts = ["export {}={}".format(key, value) for key, value in docker_args["environment"].items()]
        envs = "bash -c 'printf \"{}\\n\" > /home/software/.env'".format("\\n".join(env_parts))

        container.exec_run(envs, user="software")
        container.exec_run("sudo groupadd -g {} cuauv".format(str(GROUP_ID)))
        container.exec_run("sudo usermod -aG {} software".format(str(GROUP_ID)))
        container.exec_run("chmod +x /home/software/.env", user="software")
        container.exec_run("rm /home/software/.zshrc_user", user="software")
        container.exec_run("ln -s {} /home/software/.zshrc_user".format(software_path / "install/zshrc"), user="software")
        container.exec_run("sudo rmdir /home/software/cuauv/software", user="software")
        container.exec_run("sudo ln -s {} /home/software/cuauv/software".format(software_path), workdir="/", user="software")
    else:
        container = running[0]

    return container


def cdw(branch=BRANCH):
    """
    Enter the workspace container for a branch, creating and starting a
    workspace/container as needed.

    branch: Branch workspace to enter (and possibly create/start).
    """

    # forward 8080 so we can access webgui
    container = start(branch=branch, ports={8080:8080})
    ip = client.api.inspect_container(container.id)["NetworkSettings"]["Networks"]["bridge"]["IPAddress"]

    subprocess.run(
         ["ssh", "software@{}".format(ip), "-p", "22", "-A", "-o", "StrictHostKeyChecking no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ForwardX11Timeout 596h"]
    )

def cdw_wsl(branch=BRANCH):
    """
    Enter the workspace container for a branch, creating and starting a
    workspace/container as needed.
    
    branch: Branch workspace to enter (and possibly create/start).
    """

    os.environ['DISPLAY'] = ":0"

    container = start(branch=branch, mount_gpu=True, ports={22:2353, 8080:8080, 6060:6060})

    subprocess.run(
        ["ssh", "software@localhost", "-p", "2353", "-A", "-o", "StrictHostKeyChecking no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ForwardX11Timeout 596h"]
    )

def stop(branch=BRANCH, vehicle=False):
    """
    Stop a running container for a branch.

    branch: Branch workspace to clean up.
    vehicle: Whether running on the vehicle.
    """
    # Remove container
    docker_name = get_docker_name(branch, vehicle)
    container = get_containers(docker_name)
    if not container:
        print("No container for branch={}, vehicle={}".format(branch, vehicle))
        return
    container[0].stop()


def destroy(branch=BRANCH, vehicle=False):
    """
    Remove a container for a branch and clean up the worktree for the branch.

    branch: Branch workspace to clean up.
    vehicle: Whether running on the vehicle.
    """
    # Remove container
    docker_name = get_docker_name(branch, vehicle)
    container = get_containers(docker_name)
    if container:
        container[0].remove(force=True)
        print("Removed container for branch={}, vehicle={}".format(branch, vehicle))
    else:
        print("No container for branch={}, vehicle={}".format(branch, vehicle))

    # Delete image for branch
    image_name = "{}:{}".format(DOCKER_REPO, branch)
    try:
        client.images.remove(image_name)
        print("Deleted image {}".format(image_name))
    except docker.errors.ImageNotFound:
        print("No image {}".format(image_name))

    # Delete worktree
    subprocess.run(
        ["rm", "-rf", branch],
        cwd=str(WORKTREES_DIRECTORY),
        check=True,
    )

    subprocess.run(
        ["git", "worktree", "prune"],
        cwd=str(REPO_PATH),
        check=True,
    )
    print("Deleted worktree {}/{}".format(WORKTREES_DIRECTORY, branch))

    # Remove guard file created for the worktree branch
    remove_guard(get_worktree_guard(branch))


def vehicle(*, branch:"b"="master", vehicle:"v"=None):
    """
    Starts a container on a vehicle.

    branch: Branch workspace to be used. You probably shouldn't change this...
    """

    if vehicle is None:
        vehicle = socket.gethostname()

    vehicle_types = {
        "sirius": "mainsub",
        "polaris": "minisub",
    }

    vehicle_type = vehicle_types[vehicle]

    env = {
        "CUAUV_LOCALE": "teagle",
        "CUAUV_VEHICLE": vehicle,
        "CUAUV_VEHICLE_TYPE": vehicle_type,
        "CUAUV_CONTEXT": "vehicle",
    }

    start(vehicle=True, branch=branch, gpu=False, env=env)

def set_permissions():
    """
    Sets group permissions for the workspace using ACL.

    The GID of the cuauv group can be changed in config.py.
    """
    subprocess.run(
        ["sudo", "setfacl", "-dR", "-m", "g:{}:rwX".format(str(GROUP_ID)), str(WORKSPACE_DIRECTORY)],
        check=True
    )

    subprocess.run(
        ["sudo", "setfacl", "-R", "-m", "g:{}:rwX".format(str(GROUP_ID)), str(WORKSPACE_DIRECTORY)],
        check=True
    )

def get_running_containers():
    """
    Get all running CUAUV containers.
    """
    containers = client.containers.list()
    return list(filter(lambda c: c.name.startswith(CUAUV_CONTAINER_PREFIX), containers))

def _list():
    """
    List all branches with currently running containers.
    """
    containers = get_running_containers()
    if len(containers) == 0:
        print('No running containers!')
    else:
        print('Running containers:')
        for container in containers:
            print('  {}'.format(container.name[len(CUAUV_CONTAINER_PREFIX):]))

def stop_all():
    """
    Stop all running branch containers.
    """
    containers = get_running_containers()
    if len(containers) == 0:
        print('No running containers!')
    else:
        for container in containers:
            print('Stopping {}'.format(container.name[len(CUAUV_CONTAINER_PREFIX):]))
            container.stop()


clize.run(init, start, create_worktree, cdw, cdw_wsl, _list, stop, stop_all, destroy, vehicle, set_permissions)
