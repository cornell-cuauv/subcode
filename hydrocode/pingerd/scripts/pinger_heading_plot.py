#!/usr/bin/env python3

# Script for drawing polar plots of the heading and elevation of pings. Read Hydrophones Code wiki entry.

import math, shm
import matplotlib.pyplot as plt

REFRESH_INTERVAL = 0.25 # plot updates at this interval (in seconds)

# initialize plot window
fig = plt.figure(figsize = (7, 7))
ax = fig.add_subplot(111, polar = True)

plt.title("Heading and Elevation")

# set axes properties and remove ticks
ax.set_yticklabels([])
ax.set_theta_zero_location('N')
ax.set_theta_direction(-1)
ax.set_ylim(0, 1) # radius of plot is 1

# initialize graph with arbitrary numbers
theta = [0, 0]
r = [0, 1]
(line, ) = ax.plot(theta, r)

while True:
	# retrieve the most recent data from shm
	theta = math.radians(shm.hydrophones_results_track.tracked_ping_heading.get())
	r = math.cos(math.radians(shm.hydrophones_results_track.tracked_ping_elevation.get()))

	# update graph
	line.set_xdata([theta, theta])
	line.set_ydata([0, r])

	# draw the plot and pause until the next update
	plt.draw()
	plt.pause(REFRESH_INTERVAL)