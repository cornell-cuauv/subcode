#!/usr/bin/env python3
import sys
import tomlkit
import os

from time import sleep

from control.thrusters import all_thrusters
from control.util import zero_motors
from shm import kalman, motor_desires, reversed_thrusters, switches, navigation_desires, settings_control, gx4
from conf.vehicle import VEHICLE, is_mainsub


# directory than toml file is in
CONF = "/home/software/cuauv/workspaces/worktrees/master/conf"

class Failure(Exception):
    def __init__(self, msg, extra_lines=[], *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.extra_lines = extra_lines

    def extra(self, line):
        self.extra_lines.append(line)

# Code is mostly from thruster_mapper.py
class TomlParseFailure(Failure):
    pass

def load_conf(file_name):
    path = os.path.join(CONF, file_name)
    if not os.path.isfile(path):
        raise Failure("File '{}' does not exist in '{}'".format(file_name, CONF))
    
    try:
        with open(path) as f:
            return tomlkit.parse(f.read())
    except tomlkit.exceptions.ParseError as e:
        raise TomlParseFailure(str(e))

def find_values(toml, predicate, type_filter=None, lst=[], path=""):
    def handle(value, handle_path):
        if type_filter is None or isinstance(value, type_filter) and predicate(value):
            list.append((handle_path[1:], value))
    for key, value in toml.items():
        new_path = '{}.{}'.format(path, key)
        handle(value, new_path)
        if isinstance(value, dict):
            find_values(value, predicate, type_filter=type_filter, lst=lst, path=new_path)
        if isinstance(value, list):
            for val in value:
                handle(val, new_path)

def main():
    vehicle_conf = load_conf('{}.toml'.format(VEHICLE))

    if not "thrusters" in vehicle_conf or not isinstance(vehicle_conf["thrusters"], list):
        raise TomlParseFailure("No list of thrusters")

    thrusters = vehicle_conf["thrusters"]
    

    for thruster in thrusters:
        motor_status = getattr(reversed_thrusters, thruster["name"])
        if motor_status.get() == 1:
            thruster["reversed"] = True
        else:
            thruster["reversed"] = False
    vehicle_conf["thrusters"] = thrusters
    output = tomlkit.dumps(vehicle_conf)
    with open(os.path.join(CONF, "{}.toml".format(VEHICLE)), "w") as f:
        f.write(output)
    print("{}.toml has been overwritten".format(VEHICLE))
        


def check_soft_kill(log=sys.stdout):
    if switches.soft_kill.get():
        log.write("Vehicle is soft-killed, unkill before testing motors\n\n")
        return False
    return True

def thruster_reversal_test(log=sys.stdout, speed=1.0):
    print("BEGINNING THRUSTER REVERSAL TEST\n\n")

    zero_motors()

    if check_soft_kill(log):
        motor_tuples = [("port", "starboard"), ("sway_fore", "sway_aft"), ("aft_starboard", "fore_starboard"), ("aft_port", "fore_port")]            

        for motor1, motor2 in motor_tuples:
            print("Checking " + motor1 + " and " + motor2 + "...")

            motor1_status = getattr(reversed_thrusters, motor1)
            motor2_status = getattr(reversed_thrusters, motor2)
            motor1_status.set(0)
            motor2_status.set(0)

            if is_mainsub:
                check_motors_vel(motor1, motor2)
            else:
                check_motors_accel(motor1, motor2)

            sleep(3.0)

        print("Thruster reversal complete!")
    else:
        print("Stopped because sub is softkilled")


def check_motors_vel(motor_name1, motor_name2, motor_power=30, sleep_time=3.0):
    for motor in all_thrusters:
        if motor.name == motor_name1:
            motor1 = motor
        elif motor.name == motor_name2:
            motor2 = motor

    motor1.set(motor_power)
    motor2.set(motor_power)
    sleep(sleep_time)

    new_heading_rate = kalman.heading_rate.get()
    new_pitch_rate = kalman.pitch_rate.get()
    new_roll_rate = kalman.roll_rate.get()
    new_x_vel = kalman.velx.get()
    new_y_vel = kalman.vely.get()
    motor1.set(0)
    motor2.set(0)
    sleep(sleep_time)

    if motor_name1 == "port" and motor_name2 == "starboard":
        val1 = -new_heading_rate
        val2 = new_x_vel
    elif motor_name1 == "sway_fore" and motor_name2 == "sway_aft":
        val1 = -new_heading_rate
        val2 = new_y_vel
    elif motor_name1 == "aft_starboard" and motor_name2 == "fore_starboard":
        val1 = new_pitch_rate
        val2 = -2 * new_roll_rate
    elif motor_name1 == "aft_port" and motor_name2 == "fore_port":
        val1 = new_pitch_rate
        # negative because this one is the same as aft_starboard and fore_starboard except the 
        # thrusters need to be reversed if the roll_rate is positive instead of negative
        val2 = 2 * new_roll_rate
    else:
        print("Invalid motors")
    
    determine_reversed(motor1, motor2, val1, val2)
       
    print(motor_name1 + " and " + motor_name2 + " check complete\n\n")

def check_motors_accel(motor_name1, motor_name2, motor_power=30, sleep_time=3.0):
    for motor in all_thrusters:
        if motor.name == motor_name1:
            motor1 = motor
        elif motor.name == motor_name2:
            motor2 = motor    
    
    old_accel_x = kalman.accelx.get()
    old_accel_y = kalman.accely.get()
    old_heading_rate = kalman.heading_rate.get()
    old_pitch_rate = kalman.pitch_rate.get()
    old_roll_rate = kalman.roll_rate.get()

    motor1.set(motor_power)
    motor2.set(motor_power)
    sleep(sleep_time)

    new_heading_rate = kalman.heading_rate.get() - old_heading_rate
    new_pitch_rate = kalman.pitch_rate.get() - old_pitch_rate
    new_roll_rate = kalman.roll_rate.get() - old_roll_rate
    new_accel_x = kalman.velx.get()
    new_accel_y = kalman.vely.get()
    motor1.set(0)
    motor2.set(0)
    sleep(sleep_time)

    accel_x_diff = new_accel_x - old_accel_x
    accel_y_diff = new_accel_y - old_accel_y

    if motor_name1 == "port" and motor_name2 == "starboard":
        val1 = -new_heading_rate
        val2 = 0.01 * accel_x_diff
    elif motor_name1 == "sway_fore" and motor_name2 == "sway_aft":
        val1 = -new_heading_rate
        val2 = 0.01 * accel_y_diff
    elif motor_name1 == "aft_starboard" and motor_name2 == "fore_starboard":
        val1 = new_pitch_rate
        val2 = -2 * new_roll_rate
    elif motor_name1 == "aft_port" and motor_name2 == "fore_port":
        val1 = new_pitch_rate
        val2 = 2 * new_roll_rate
    else:
        print("Invalid motors")
    determine_reversed(motor1, motor2, val1, val2)

    print(motor_name1 + " and " + motor_name2 + " check complete\n\n")

def determine_reversed(motor1, motor2, val1, val2):
    if abs(val1) > abs(val2):
        if val1 < 0:
            reverse_motor(motor1)
        else:
            reverse_motor(motor2)
    elif val2 < 0:
            reverse_motor(motor1)
            reverse_motor(motor2)


def reverse_motor(motor):
    print("Reversing " + motor.name + "...")
    motor_status = getattr(reversed_thrusters, motor.name)
    motor_status.set(1)

if __name__ == "__main__":
    is_soft_killed = switches.soft_kill.get()

    try:
        zero_motors()
        settings_control.enabled.set(0)

        if is_soft_killed:
            keep_killed = input("Softkill is enabled, would you like to override it? [yN] ")
            if keep_killed == "y":
                print("Disabling softkill...")
                switches.soft_kill.set(0)
            else:
                if keep_killed == "" or keep_killed == "n":
                    print("Softkill is enabled. Exiting")
                    sys.exit()
                else:
                    print("Invalid response.")
                    sys.exit(1)
        
        input("Press ENTER to start thruster reversal test. Press CTRL-C to exit.")

        thruster_reversal_test()
        main()
    except Exception as e:
        print(e)
        zero_motors()
        settings_control.enabled.set(1)
        print("Exception caught, quitting, but as the pinnacle of grace and elegance")
    finally:
        settings_control.enabled.set(1)
        switches.soft_kill.set(is_soft_killed)
