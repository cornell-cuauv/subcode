#!/usr/bin/env python3

import gevent, termcolor, time, argparse, sys, os, signal
import test
from tests import *

from conf.vehicle import VEHICLE_TYPE

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', help='Display verbose output (default: false)', action='store_true')
parser.add_argument('-c', '--continuous', help='Run in continuous mode (default: false)', action='store_true')
parser.add_argument('-e', '--environment', help='Ignore environment and run all (default: false)', action='store_true')
parser.add_argument('-a', '--autonomous', help='Run for an autonomous run (default: false)', action='store_true')
args = parser.parse_args()

def handler(signal, frame):
    sys.stdout.write('Caught Ctrl-C, terminating...')
    sys.exit(0)

signal.signal(signal.SIGINT, handler)

statuses = {
    test.OK: termcolor.colored('OK  ', 'green', attrs = ['bold']),
    test.WARN: termcolor.colored('WARN', 'yellow', attrs = ['bold']),
    test.ERR: termcolor.colored('ERR ', 'red', attrs = ['bold'])
}

def run(t, last_result = None):
    result = t.expr()
    show_result = args.verbose

    if last_result is None:
        # First run of test
        show_result |= not result
    else:
        show_result |= last_result != result

    if show_result:
        status = statuses[t.on_success if result else t.on_error]
        sys.stdout.write('[{timestamp}] {status} {testname} TEST:\n {source}'.format(
            timestamp=termcolor.colored(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()), 'cyan'),
            status=status,
            testname=termcolor.colored(t.name.ljust(40), 'blue'),
            source=termcolor.colored(t.raw.ljust(50), 'magenta')
        ))
        sys.stdout.flush()
    if args.continuous:
        gevent.sleep(0.5)
        run(t, result)
    else:
        return result

greenlets = []

if VEHICLE_TYPE == 'mainsub':
    vehicle_id = test.MAINSUB
elif VEHICLE_TYPE == 'minisub':
    vehicle_id = test.MINISUB
else:
    raise ValueError("CUAUV_VEHICLE_TYPE must be set to one of {mainsub, minisub}!")

environment_id = 2
if(not args.environment):
    LAND_DEPTHS = {
        test.MAINSUB: 0.01,
        test.MINISUB: 0.35,
    }

    if shm.kalman.depth.get() > LAND_DEPTHS[vehicle_id]:
        environment_id = test.WATER
    else:
        environment_id = test.LAND

sys.stdout.write('Running tests for vehicle: {} in environment {}\n'.format(vehicle_id,environment_id))
sys.stdout.flush()

for t in Test.active_tests(vehicle_id, environment_id, args.autonomous):
    greenlets.append(gevent.spawn(run, t))


gevent.joinall(greenlets)

num_failed = sum(not x.get() for x in greenlets)

if num_failed == 0:
    sys.stdout.write('[{timestamp}] {ok_status} All systems are go!\n'.format(
        timestamp=termcolor.colored(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()), 'cyan'),
        ok_status=statuses[test.OK]
    ))
    sys.stdout.flush()

sys.exit(num_failed)
