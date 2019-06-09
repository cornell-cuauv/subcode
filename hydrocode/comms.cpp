//
//  comms.cpp
//  hydromathd
//
//  Created by Vlad on 2/5/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#include <cstdio>
#include <cstdint>

//#include "libshm/c/vars.h"
#include "shm_mac.hpp"
#include "comms.hpp"
#include "common_dsp.hpp"
#include "udp_sender.hpp"
#include "liquid.h"
#include "structs.hpp"

void comms_dsp(uint16_t *fpga_packet)
{
    if(packet_no == 0)
    {
        printf("%s \n", "new interval. mode: comms");
    }
    
    if(packet_no >= gain_propagation_packets)
    {
        for(int packet_sample_no = 0; packet_sample_no < packet_length; packet_sample_no++)
        {
            new_raw_sample = fpga_packet[4 * packet_sample_no + 3];
            raw_buffer.push(new_raw_sample);
            
            if(new_raw_sample > raw_peak)
            {
                raw_peak = new_raw_sample;
                
                if(shm_settings.auto_gain == 1)
                {
                    if(raw_peak > clipping_threshold * highest_quantization_lvl)
                    {
                        printf("%s \n","clipping detected");
                        
                        if(gain_lvl > 0)
                        {
                            gain_lvl--;
                            
                            printf("%s \n", "gain decreased");
                            
                            goto end_interval;
                        }
                        else
                        {
                            printf("%s \n", "gain cannot be decreased further!");
                        }
                    }
                }
                
                savePlot(raw_buffer, raw_buffer_length, raw_plot, raw_buffer_length, raw_plot_length / highest_quantization_lvl);
            }
        }
    }
}
