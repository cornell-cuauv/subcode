#!/usr/bin/env python3

import shm
import time
import math

print("ensure the below number is increasing...if the number is not increasing pingerd is down")
for i in range(0,60):
    print(f"pinger packets: {shm.hydrophones_pinger_status.packet_number.get()}", end='\r')
    time.sleep(1/30)
print()

print("hydrophones is set to frequency", shm.hydrophones_pinger_settings.frequency.get())
print("if this is incorrect, use 'shm.hydrophones_pinger_status.frequency <freq>'")
time.sleep(2)
print("watching:")
while True:
    direction = shm.hydrophones_pinger_results.heading.get()
    print("heading in degrees", (direction * 180 / math.pi + 180) % 360)
    time.sleep(0.5)
