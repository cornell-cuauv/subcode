//
//  constants.cpp
//  hydromathd
//
//  Created by Vlad on 7/3/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#include "constants.hpp"

extern const std::vector<unsigned int> FREQS = {25'000, 30'000, 35'000, 40'000};
extern const unsigned int DECIM_FACTOR = 15;
extern const unsigned int STOPBAND = 9'000;
extern const unsigned int AMPL_AVG_LEN = 20'000;
extern const unsigned int INTERV_LEN = 21'000;
extern const unsigned int SEARCH_INTERV_LEN = 1000;

extern const unsigned int ADC_SAMPLE_RATE = 153'061;
extern const unsigned int SOUND_SPEED = 1481;
extern const float NIPPLE_DISTANCE = 0.0178;

extern const unsigned int BUFF_LEN = 65'536;

extern const char PLOT_DISPLAY_ADDR[] = "127.0.0.1";
extern const unsigned int RAW_PLOT_PORT = 49153;
extern const unsigned int SENSE_PLOT_PORT = 49154;
extern const unsigned int TRIGGER_PLOT_PORT = 49155;
extern const unsigned int RAW_PLOT_LEN = 70;
extern const unsigned int TRIGGER_PLOT_LEN = 20;

extern const char BOARD_ADDR[] = "192.168.0.102";
extern const unsigned int LOCAL_SAMPLE_PORT = 49152;
extern const unsigned int BOARD_CONFIG_PORT = 49152;
extern const unsigned int SAMPLE_PKT_LEN = 31;

