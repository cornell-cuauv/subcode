from pathlib import Path, PurePosixPath
import os
import pwd
import platform

"""
You can override these defaults: create a new file called `user.py` (in this
folder, `docker`) with a dict called `config`. Any keys defined in this dict
will override the default ones below. An example user.py:

```
from pathlib import Path, PurePosixPath

config = {
    "WORKSPACE_DIRECTORY": Path("~/path/to/my/repo/").expanduser(),
}
```

We use a separate file so that we don't track user-specific changes.
"""

def get_user():
   try:
      return pwd.getpwuid(os.getuid()).pw_name
   except Exception:
      return ''

machine = platform.machine()

defaults = {
    "WORKSPACE_DIRECTORY": Path("~/cuauv/workspaces").expanduser(),
    "CONTAINER_WORKSPACE_DIRECTORY": PurePosixPath("/home/software/cuauv/workspaces"),

    "DOCKER_REPO": f"docker.cuauv.org/cuauv-20-{machine}",
    "DOCKER_REPO_JETSON": "docker.cuauv.org/cuauv-jetson",

    "GIT_REPO_URL": "git@github.coecis.cornell.edu:CUAUV/subcode.git",
    "BRANCH": "master",

    "GROUP_ID": 9999,

    # default to current Linux user name
    "AUV_ENV_ALIAS": get_user(),
}

try:
   import user
   if hasattr(user, 'config'):
      conf = dict(defaults, **user.config)
   else:
      conf = defaults
except ImportError:
   conf = defaults

def get_config(key):
   return conf[key]
