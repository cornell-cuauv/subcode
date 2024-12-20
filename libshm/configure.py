#!/usr/bin/env python3

import subprocess

from build import ninja_common

build = ninja_common.Build('libshm')

BUILD_OCAML = False

scmfiles = [
            'shm.scm',
           ]

ocamlfiles = [
    'CUAUV_shm.ml',
    'CUAUV_shm.mli'
]

pyfiles = [
            'group.py',
            'watchers.py',
            'base.py'
          ]
files = [
            'shm.c',
            'shm.h',
            'log.cpp',
            'log.h',
            'serialize.cpp',
            'serialize.h',
            'shm_diagnose.cpp',
            'vars.h',
            'vars.c',
            'watcher.h',
            'watcher.c',
            'dynamic.h',
            'dynamic.cpp',
        ]

templates = ['templates/%s' % f for f in files + pyfiles + scmfiles + ocamlfiles]
# Lol... the Python, Scheme and OCaml files are piggybacking on the C files.
# This isn't really how this is supposed to be used... -- jyc
intermediates = ['c/%s' % f for f in files]
ocamlintermed = ['ocaml/%s' % f for f in ocamlfiles]
scmintermed = ['scm/%s' % f for f in scmfiles]

build.generate(intermediates + ocamlintermed + scmintermed, 'libshm/generate.py', templates + ['vars.conf'])
build.generate(['c/checksum.h'], 'libshm/checksum.sh', intermediates)

if BUILD_OCAML and subprocess.getstatusoutput('which opam')[0] == 0:
    build.generate(['ocaml/install.fake'], 'libshm/ocaml/generate.sh',
            ocamlintermed +
            ['templates/%s' % f for f in ocamlfiles] +
            ['vars.conf'])

build.generate(['c/dshm.h', 'c/dshm.c', 'scm/dshm.scm'], 'libshm/generate_dshm.py',
        [
            'vars.conf',
            'dtemplates/dshm.h',
            'dtemplates/dshm.c',
            'dtemplates/dshm.scm',
            'generate_dshm.py',
        ])

build.build_shared('auvshm',
                [
                    'c/log.cpp',
                    'c/serialize.cpp',
                    'c/shm.c',
                    'c/vars.c',
                    'c/watcher.c',
                    'c/dshm.c',
                    'c/dynamic.cpp',
                ],
                implicit=['libshm/c/checksum.h'],
                cflags=['-fno-var-tracking'])

build.build_cmd('auv-diagnose-shm',
        ['c/shm_diagnose.cpp'],
        auv_deps=['auvshm'])

build.install('auv-test-python-shm', 'libshm/test/bindings_test.py', is_test=True)
build.run_test('auv-test-python-shm')