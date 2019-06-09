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

const float clipping_threshold = 0.97; //clipping declared if signal above this level (fraction of maximum possible level)
const float clipping_threshold_hysteresis = 0.1; //hysteresis to prevent over-zealous gain increasing (fraction of maximum possible level)
const float highest_quantization_lvl = 16383; //maximum possible level of a signal
const int dc_calc_length = 64; //length of running average for calculating the DC bias (in samples)
const int default_gain_lvl = 0; //gain level upon startup if autogain enabled
const int dft_length = 80; //length of the sliding dft bin window (in samples)
const int freq_list_length = 4; //length of the hardcoded frequencies list
const int gain_propagation_packets = 250; //time taken for fpga to switch gain, conservatively (in packets)
const float nipple_distance = 0.0178; //distance between the teats (in meters)
const float pinger_period = 2; //time between pings (in seconds)
const float pinger_period_factor = 1.2; //ensuring that every interval will contain at least one ping, accounting for the gain propagation deadtime
const int raw_buffer_length = 512; //length of the raw buffer (in samples)
const int raw_plot_length = 64; //length of the raw plot (in samples)
const float sampling_rate = 200000; //self-explanatory, no?
const float sound_speed = 1481; //speed of sound in fresh water at 20 degrees Celsius

const int freqs[freq_list_length] = {25000, 30000, 35000, 40000}; //hardcoded frequencies list. read wiki entry before updating this!
const int gainz[14] = {1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128}; //possible gain settings

void pinger_tracking_dsp(uint16_t *fpga_packet);

#endif /* pinger_tracking_hpp */
