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
static int last_gain_set_packet, last_raw_comms_plot_packet;
static float raw_comms_plot_peak;
static float raw_peak;

void savePlotSingle(const buffer &data_buffer, int data_buffer_length, buffer &copy_buffer, int copy_length, float scaling_factor)
{
    for(int data_point_no = 0; data_point_no < copy_length; data_point_no++)
    {
        copy_buffer.push(data_buffer.read(data_point_no + data_buffer_length - copy_length) * scaling_factor);
    }
}

void comms_dsp(uint16_t *fpga_packet, bool reset_signal)
{
    shm_getg(hydrophones_settings, shm_settings);
    
    if(reset_signal == 1 || packet_no = 0)
    {
        packet_no = 0;
        last_gain_set_packet = 0;
        last_raw_comms_plot_packet = 0;
        raw_comms_plot_peak = 0;
        raw_peak = 0;
    }
    
    for(int packet_sample_no = 0; packet_sample_no < packet_length; packet_sample_no++)
    {
        float new_raw_sample;
            
        new_raw_sample = fpga_packet[4 * packet_sample_no + 3];
        raw_comms_buffer.push(new_raw_sample);
            
        if(new_raw_sample > raw_peak)
        {
            raw_peak = new_raw_sample;
            
            if(new_raw_sample > raw_comms_plot_peak)
            {
                raw_comms_plot_peak = new_raw_sample;
                savePlotSingle(raw_comms_buffer, raw_comms_buffer_length, raw_comms_plot, raw_comms_plot_length, raw_comms_plot_length / highest_quantization_lvl);
            }
        }
    }
    
    if(packet_no - last_gain_set_packet >= (int)(comms_agc_interval * sampling_rate / packet_length))
    {
        if(shm_settings.auto_gain == 1)
        {
            if(raw_peak > clipping_threshold * highest_quantization_lvl)
            {
                if(gain_lvl > 0)
                {
                    gain_lvl--;
                }
            }
            else
            {
                increaseGain(raw_peak, gain_lvl);
            }
        }
        else
        {
            gain_lvl = shm_settings.target_gain;
        }
        
        setGain(gain_lvl);
        raw_peak = 0;
        last_gain_set_packet = packet_no;
    }
    
    if(packet_no - last_raw_comms_plot_packet >= (int)(raw_comms_plot_interval * sampling_rate / packet_length))
    {
        sendPlot(raw_comms_plot.get(), 3, raw_comms_plot_length);
        
        raw_comms_plot_peak = 0;
    }
    
    packet_no++;
}
