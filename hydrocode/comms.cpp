//
//  comms.cpp
//  hydromathd
//
//  Created by Vlad on 2/5/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#include <cstdio>
#include <cstdint>

#include "libshm/c/vars.h"
//#include "shm_mac.hpp"
#include "comms.hpp"
#include "common_dsp.hpp"
#include "udp_sender.hpp"
#include "liquid.h"
#include "structs.hpp"

static int gain_lvl = default_gain_lvl;
static struct hydrophones_settings shm_settings;
static int packet_no = 0;
static buffer raw_comms_buffer(raw_comms_buffer_length);
static buffer raw_comms_plot(raw_comms_plot_length);
static float raw_peak;
static bool transmission_lock;

void savePlotSingle(const buffer &data_buffer, int data_buffer_length, buffer &copy_buffer, int copy_length, float scaling_factor)
{
    for(int data_point_no = 0; data_point_no < copy_length; data_point_no++)
    {
        copy_buffer.push(data_buffer.read(data_point_no + data_buffer_length - copy_length) * scaling_factor);
    }
}

void comms_dsp(uint16_t *fpga_packet, bool reset_signal)
{
    if(reset_signal == 1)
    {
        packet_no = 0;
    }
    
    if(packet_no == 0)
    {
        raw_peak = 0;
        transmission_lock = 0;
        
        printf("%s \n", "new interval. mode: comms");
        
        shm_getg(hydrophones_settings, shm_settings);
        
        setGain(gain_lvl);
        printf("%s%d \n", "gain: x", gainz[gain_lvl]);
    }
    
    if(packet_no >= gain_propagation_packets)
    {
        for(int packet_sample_no = 0; packet_sample_no < packet_length; packet_sample_no++)
        {
            float new_raw_sample;
            
            new_raw_sample = fpga_packet[4 * packet_sample_no + 3];
            raw_comms_buffer.push(new_raw_sample);
            
            if(new_raw_sample > raw_peak)
            {
                raw_peak = new_raw_sample;
                
                savePlotSingle(raw_comms_buffer, raw_comms_buffer_length, raw_comms_plot, raw_comms_plot_length, raw_comms_plot_length / highest_quantization_lvl);
            }
        }
    }
    
    packet_no++;
    
    if(packet_no >= (int)(comms_period * sampling_rate / packet_length) && transmission_lock == 0)
    {
        if(shm_settings.auto_gain == 1)
        {
            if(raw_peak > clipping_threshold * highest_quantization_lvl)
            {
                printf("%s \n","clipping detected");
                
                if(gain_lvl > 0)
                {
                    gain_lvl--;
                    
                    printf("%s \n", "gain decreased");
                }
                else
                {
                    printf("%s \n", "gain cannot be decreased further!");
                }
            }
            else if(increaseGain(raw_peak, gain_lvl) == 1)
            {
                printf("%s \n", "gain increased");
            }
        }
        else
        {
            gain_lvl = shm_settings.manual_gain_value;
        }
        
        sendPlot(raw_comms_plot.get(), 3, raw_comms_plot_length);
        
        packet_no = 0;
        
        printf("%s %4.2f%s \n", "signal peak was:", raw_peak / highest_quantization_lvl * 100, "% of highest quantization level");
        
        printf("\n");
    }
}
