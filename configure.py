#!/usr/bin/env python3

""" Generate ninja files for build by ninja. """

import os, argparse
import getpass

parser = argparse.ArgumentParser()
parser.add_argument(
  '--bamboo',
  help='Build for Bamboo',
  action='store_true')

args = parser.parse_args()

if args.bamboo:
  print('Configuring for Bamboo...')

from build import ninja_syntax

cflags = [
          '-pthread',
          '-lrt',
          '-lm',
          '-Wall',
          '-I.',
          '-ggdb2',
          '-O3',
          '-Werror',
         ]
cppflags = [
    '-std=c++14', '-fdiagnostics-color',
    '-Wno-int-in-bool-context', # Needed for eigen on gcc7+
]

# CUAUV libraries are found at run time using rpath, an absolute path
# optionally baked into ELF binaries that is added to the loader search path.
rpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "link-stage")
ldflags = cflags + ['-Llink-stage', '-Wl,-rpath %s' % rpath]

dirs = [
        'auv_math',
        'auv_math/libquat',
        'auvlog',
        'conf',
        'conf/json-decomment',
        'control',
        'control/controlhelm',
        'deadman',
        'lib',
        'libshm',
        'locator',
        'misc',
        # 'misc/3dcontrol',
        'mission',
        'mission/opt',
        # 'object-recognition',
        'positiontracker3',
        'self_test',
        'sensors',
        'sensors/3dmg/gx4',
        'sensors/dvld',
        'shm_tools',
        'shm_tools/shm-cli',
        'shm_tools/shm-editor',
        'shm_tools/shm-notifier',
        'shm_tools/shmlog',
        'slam',
        'system_check',
        'trogdor',
        'vision',
        'webserver',
       ]

context_excludes = {
    'all': [],

    'development': [
        'hydrocode',
        'lcd',
        'led',
        'pooltest',
        'serial/cli',
        'serial/debugger',
        'serial/libserial',
        'serial/seriald',
        'uptime',
        'vehicle-scripts',
    ],

    'vehicle': [
        'cave',
        'fishbowl',
        'fishbowl/body-frame-calc',
        'fishbowl/cw-he-calc',
        'visualizer',
    ],
}

context_var = 'CUAUV_CONTEXT'
context = os.environ[context_var] if context_var in os.environ else ""

if context not in context_excludes:
    print('CUAUV_CONTEXT is \'{}\''.format(context))
    print('... Try one of: {}'.format(sorted(context_excludes.keys())))
    print('... to build only the subsystems strictly necessary for your environment.')

for k, v in sorted(context_excludes.items()):
    if context != k:
        dirs += v

# Because bamboo can't build peacock and we don't want peacock on the sub
if not args.bamboo and context != 'vehicle':
    dirs += ['peacock']

#if not subprocess.getstatusoutput('which go')[0]:
#  dirs.extend([
#    'gocode/src/cuauv.org/shm',
#    'gocode/src/cuauv.org/shm/cli'
#  ])

buildfile = open('build.ninja', 'w')
n = ninja_syntax.Writer(buildfile)

n.comment('This file is used to build the CUAUV software tree.')
n.comment('It is generated by ' + os.path.basename(__file__) + '.')
n.newline()

n.variable('ar', os.environ.get('AR', 'ar'))
n.variable('cxx', os.environ.get('CXX', 'g++'))
n.variable('cc', os.environ.get('CC', 'gcc'))
n.variable('cflags', ' '.join(cflags))
n.variable('cppflags', ' '.join(cppflags))
n.variable('ldflags', ' '.join(ldflags))
n.variable('absdir', os.getcwd())
n.newline()

n.rule('cxx',
       command = '$cxx -MMD -MF $out.d $cflags $cppflags -c $in -o $out',
       description = 'CXX $out',
       depfile = '$out.d')

n.rule('cc',
       command = '$cc -MMD -MF $out.d -std=gnu99 $cflags -c $in -o $out',
       description = 'CC $out', depfile = '$out.d')

n.rule('link_shared',
       command='$cxx -shared -o $out $in $libs $ldflags',
       description='LINK $out')

n.rule('ar',
       command='rm -f $out && $ar crs $out $in',
       description='AR $out')

n.rule('link',
       command='$cxx -o $out $in $libs $ldflags',
       description='LINK $out')

n.rule('install',
       command = 'ln -sf $absdir/$in $out',
       description='INSTALL $out')

n.rule('generate',
       command = './$in $args',
       description = 'GENERATE $out',
       restat = True)

n.rule('run',
       command = '$in $args',
       description = 'RUN $out')

n.rule('configure',
       command = './$in',
       description = 'CONFIGURE $out',
       generator = True)

n.rule('go-build',
       command = 'go build -o $out $pkg',
       description = 'GO BUILD $pkg')

n.rule('go-install',
       command = 'go install $pkg',
       description = 'GO INSTALL $pkg')

if not args.bamboo and context != 'vehicle':
  n.rule('chicken-exe',
         command = 'csc $cflags $lflags $in -o $out',
         description='CHICKEN EXE $out')

  n.rule('chicken-lib',
         command = 'build/build_chicken_lib.sh $where $fake',
         description='CHICKEN LIB $out')

else:
  n.rule('chicken-exe', command = 'exit 0', description = 'Do nothing!')
  n.rule('chicken-lib', command = 'exit 0', description = 'Do nothing!')

if args.bamboo:
    # Don't run on Bamboo lol
    stack_home_prefix = "# "
else:
    stack_home_prefix = ""

STACK_COMMAND = '{}HOME=/home/{} stack --verbosity 0 --stack-yaml $config install --local-bin-path $bin'.format(stack_home_prefix, getpass.getuser())
n.rule('stack',
  command = STACK_COMMAND,
  description = 'Haskell Stack ( `{}` )'.format(STACK_COMMAND),
  restat = True)

n.rule('webpack',
  command = 'webpack --color --config $config',
  description = 'webpack $out',
  restat = True)

n.rule('general',
       command = './$in $args',
       description = '$name $out',
       restat = True)

n.newline()

# Add build.ninja target.
n.build('build.ninja',
        'configure',
        'configure.py',
        implicit = ['build/ninja_common.py'] + ['%s/build.ninja' % d for d in dirs])
n.newline()

# Arrays to keep track of subdirectory build targets
code_targets = []
test_targets = []
check_targets = []

# Run each config script to build each subninja that does not exist.
# Subninja each new file and add targets to rebuild them.
for d in dirs:
    n.build('%s/build.ninja' % d, 'configure', '%s/configure.py' % d, implicit=['build/ninja_common.py'])
    if os.system('%s/configure.py' % d) != 0:
        raise AssertionError('Failed to configure %s!\n' % d +
            'Please run %s/configure.py for more info.' % d)
    n.subninja('%s/build.ninja' % d)
    code_targets.append('code-%s' % d)
    test_targets.append('tests-%s' % d)
    check_targets.append('check-%s' % d)

# Add the global "code", "tests", and "check" targets
n.build('code', 'phony', implicit=code_targets)
n.build('tests', 'phony', implicit=test_targets)
n.build('check', 'phony', implicit=check_targets)

# Set the default targets to "code" and "tests"
n.default(['code', 'tests'])
