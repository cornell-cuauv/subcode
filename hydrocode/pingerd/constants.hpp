//
//  constants.hpp
//  hydromathd
//
//  Created by Vlad on 7/3/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#ifndef constants_hpp
#define constants_hpp

#include <vector>

extern const std::vector<unsigned int> FREQS;
extern const unsigned int DECIM_FACTOR;
extern const unsigned int STOPBAND;
extern const unsigned int AMPL_AVG_LEN;
extern const unsigned int INTERV_LEN;
extern const unsigned int SEARCH_INTERV_LEN;

extern const unsigned int ADC_SAMPLE_RATE;
extern const unsigned int SOUND_SPEED;
extern const float NIPPLE_DISTANCE;

extern const unsigned int BUFF_LEN;

extern const char PLOT_DISPLAY_ADDR[];
extern const unsigned int RAW_PLOT_PORT;
extern const unsigned int SENSE_PLOT_PORT;
extern const unsigned int TRIGGER_PLOT_PORT;
extern const unsigned int RAW_PLOT_LEN;
extern const unsigned int TRIGGER_PLOT_LEN;

extern const char BOARD_ADDR[];
extern const unsigned int LOCAL_SAMPLE_PORT;
extern const unsigned int BOARD_CONFIG_PORT;
extern const unsigned int SAMPLE_PKT_LEN;

#endif /* constants_hpp */

