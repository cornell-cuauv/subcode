//
//  pinger_tracking.hpp
//  hydromathd
//
//  Created by Vlad on 10/27/18.
//  Copyright © 2018 Vlad. All rights reserved.
//

#ifndef pinger_tracking_hpp
#define pinger_tracking_hpp

#include <cstdint>

static const int dc_calc_length = 64; //length of running average for calculating the DC bias (in samples)
static const int dft_length = 80; //length of the sliding dft bin window (in samples)
static const int freq_list_length = 4; //length of the hardcoded frequencies list
static const float nipple_distance = 0.0178; //distance between the teats (in meters)
static const float pinger_period = 2; //time between pings (in seconds)
static const float pinger_period_factor = 1.2; //ensuring that every interval will contain at least one ping, accounting for the gain propagation deadtime
static const int raw_buffer_length = 512; //length of the raw buffer (in samples)
static const int raw_plot_length = 64; //length of the raw plot (in samples)
static const float sound_speed = 1481; //speed of sound in fresh water at 20 degrees Celsius

static const int freqs[freq_list_length] = {25000, 30000, 35000, 40000}; //hardcoded frequencies list. read wiki entry before updating this!

void pinger_tracking_dsp(uint16_t *fpga_packet, bool reset_signal);

#endif /* pinger_tracking_hpp */
