#!/usr/bin/env python3 
 
import shm 
import threading 
import time 
 
recording = False 
name = None 
def record(): 
    while True:
        while not recording:
            time.sleep(0.1)
        pwms = []
        while recording:
            desires = shm.motor_desires.get()
            pwms.append([
                time.time(),
                desires.fore_starboard,
                desires.aft_port,
                desires.port,
                desires.starboard,
                desires.sway_fore,
                desires.sway_aft,
                desires.aft_starboard,
                desires.fore_port
            ])
            time.sleep(0.1)
        while name == None:
            time.sleep(0.1)
        with open(f'pwm_record_{name}.csv', 'w') as f:
            for pwm in pwms:
                f.write(','.join(str(x) for x in pwm) + '\n')

record_thread = threading.Thread(target=record)
record_thread.start()
while True:
    input('Press enter to start recording...')
    name = None
    recording = True
    input('Press enter to stop record...')
    recording = False
    name = input('Name for this experiment: ')
