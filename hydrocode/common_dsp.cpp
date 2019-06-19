//
//  common_dsp.cpp
//  hydromathd
//
//  Created by Vlad on 6/17/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#include "common_dsp.hpp"
#include "udp_sender.hpp"

bool increaseGain(float raw_peak, int &gain_lvl)
{
    //Tries to increase gain, taking into account the signal strength on the current interval ("raw_peak") and the current gain level ("gain_lvl"). Returns 1 if gain has been increased
    
    //because the possible gain levels are a few random numbers like x6, x24, etc., it is easy to try all of them in decreasing order
    for(int try_gain_lvl = 13; try_gain_lvl > gain_lvl; try_gain_lvl--)
    {
        //if signal would not have clipped on a higher gain, then gain can be incresed. DC bias needs to be accounted for because it does not change with gain. it is very roughly "highest_quantization_lvl / 2" at all times because we are working with single rail supplies.
        if((raw_peak - highest_quantization_lvl / 2) / gainz[gain_lvl] * gainz[try_gain_lvl] <= (clipping_threshold - clipping_threshold_hysteresis) * highest_quantization_lvl / 2)
        {
            gain_lvl = try_gain_lvl;
            return 1;
        }
    }
    
    return 0;
}

void setGain(int gain_lvl)
{
    //Prepares and sends gain settings to the FPGA.
    
    char gain_packet[2]; //changing the gain requires sending the setting in a string format to the FPGA
    
    gain_packet[0] = (gain_lvl + 1) / 10 + '0';
    gain_packet[1] = (gain_lvl + 1) % 10 + '0';
    
    sendGain(gain_packet);
}
