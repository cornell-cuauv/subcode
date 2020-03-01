//
//  constants.hpp
//  hydromathd
//
//  Created by Vlad on 7/3/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#ifndef constants_hpp
#define constants_hpp

namespace Pinger {
extern const unsigned int NUM_FREQS;
extern const unsigned int FREQS[4];
extern const unsigned int DECIM_FACTOR;
extern const unsigned int STOPBAND;
extern const unsigned int AMPL_AVG_LEN;
extern const unsigned int INTERV_LEN;

extern const unsigned int RAW_PLOT_PORT;
extern const unsigned int SENSE_PLOT_PORT;
extern const unsigned int TRIGGER_PLOT_PORT;
extern const unsigned int RAW_PLOT_LEN;
extern const unsigned int TRIGGER_PLOT_LEN;
}

namespace Comms {
extern const unsigned int BITS_PER_SYMBOL;
extern const unsigned int NUM_SYMBOLS;
extern const unsigned int SYMBOLS[2];
extern const unsigned int CODE_LEN;
extern const int CODE[32];
extern const int ORTH_CODE[32];
extern const unsigned int DECIM_FACTOR;
extern const unsigned int SYMBOL_WIDTH;
extern const unsigned int SAMPLES_PER_SYMBOL;
extern const unsigned int BITS_PER_SYMBOL;
extern const unsigned int PKT_SIZE;

extern const unsigned int RAW_PLOT_PORT;
extern const unsigned int CORR_PLOT_PORT;
extern const unsigned int RAW_PLOT_LEN;
extern const unsigned int CORR_PLOT_LEN;
}

extern const unsigned int BUFF_LEN;

extern const unsigned int ADC_SAMPLE_RATE;
extern const unsigned int SOUND_SPEED;
extern const float NIPPLE_DISTANCE;

extern const char PLOT_DISPLAY_ADDR[];
extern const char BOARD_ADDR[];
extern const unsigned int LOCAL_SAMPLE_PORT;
extern const unsigned int BOARD_CONFIG_PORT;
extern const unsigned int SAMPLE_PKT_LEN;

#endif /* constants_hpp */

