//
//  common_dsp.hpp
//  hydromathd
//
//  Created by Vlad on 11/8/18.
//  Copyright © 2018 Vlad Mihai. All rights reserved.
//

#ifndef common_dsp_hpp
#define common_dsp_hpp

static const float clipping_threshold = 0.9; //clipping declared if signal above this level (fraction of maximum possible level)
static const float clipping_threshold_hysteresis = 0.2;
static const int default_gain_lvl = 0; //gain level upon startup if autogain enabled
static const int gain_propagation_packets = 250; //time taken for fpga to switch gain, conservatively (in packets)
static const float highest_quantization_lvl = 16383; //maximum possible level of a signal
static const int packet_length = 128; //number of samples for a channel in an FPGA packet
static const float sampling_rate = 200000; //self explanatory, no?

static const int gainz[14] = {1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128}; //possible gain settings

bool increaseGain(float raw_peak, int &gain_lvl);
void setGain(int gain_lvl);

#endif /* common_dsp_hpp */
