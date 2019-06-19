//
//  comms.hpp
//  hydromathd
//
//  Created by Vlad on 2/5/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#ifndef comms_hpp
#define comms_hpp

#include <cstdint>

static const float comms_agc_interval = 0.2;
static const float print_interval = 2;
static const int raw_comms_buffer_length = 512;
static const float raw_comms_plot_interval = 2;
static const int raw_comms_plot_length = 64;

void comms_dsp(uint16_t *fpga_packet, bool reset_signal);

#endif /* comms_hpp */
