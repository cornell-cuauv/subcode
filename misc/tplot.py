#!/usr/bin/env python3

import argparse
from subprocess import run
from tempfile import NamedTemporaryFile
from time import time, sleep

import shm

parser = argparse.ArgumentParser(description='Graph some SHM')
parser.add_argument('variables', metavar='GROUP.VAR', type=str, nargs='+',
                    help='Variables to graph')
args = parser.parse_args()

tracks = { name: (shm._eval(name), NamedTemporaryFile()) for name in args.variables }
plotfile = NamedTemporaryFile()
print(plotfile.name)

with open(plotfile.name, "w") as f:
    f.write('set xlabel "Label"\n')
    f.write('set ylabel "Label2"\n')
    f.write('set term dumb\n')

    plots = []
    for name, (var, filename) in tracks.items():
        plots.append('"{}" title "{}" with linespoint'.format(filename.name, name))

    f.write("plot ")
    f.write(",".join(plots))
    f.write("\n")


for name, (var, filename) in tracks.items():
    with open("{}".format(filename.name), "w") as f:
        f.write("# Time {}\n".format(name))


while True:
    for name, (var, filename) in tracks.items():
        with open("{}".format(filename.name), "a") as f:
            f.write("{} {}\n".format(time(), var.get()))

    run("gnuplot -c {} | grep --color=always -E \"A|B|C|$\"".format(plotfile.name), shell=True)

    sleep(.5)
