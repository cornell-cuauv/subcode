//
//  pinger_tracking.cpp
//  hydromathd
//
//  Pinger tracking code. Executes on every new packet.
//
//  Created by Vlad on 10/27/18.
//  Copyright © 2018 Vlad. All rights reserved.
//

#include <cstdio>
#include <cstdint>

#include "libshm/c/vars.h"
//#include "shm_mac.hpp"
#include "pinger_tracking.hpp"
//#include "audible_ping.hpp"
#include "common_dsp.hpp"
#include "udp_sender.hpp"
#include "liquid.h"
#include "structs.hpp"

//extern FILE *audible_file;

static const int trigger_plot_length = 2 * dft_length; //length of the trigger plot (in samples)
static const int dft_plot_length = (int)(pinger_period * pinger_period_factor * sampling_rate / packet_length - gain_propagation_packets); //length of the dft plot (in samples)
static float dft_peak;
static buffer dft_results_buffer(dft_length + 1);
static buffer dft_plot_amplitudes(dft_plot_length);
static buffer dft_plot_ratios(dft_plot_length);
static buffer dft_plot_trigger_point(1);
static float dft_ratio_plot_peak;
static float dft_ratio_good_peak;
static int gain_lvl = default_gain_lvl;
static int good_freq_no = 0;
static triple_phasor last_dft_result[freq_list_length];
static float noise_sum;
static int packet_no = 0;
static triple_sample ping_phase;
static buffer_triple raw_buffer(raw_buffer_length);
static float raw_peak;
static buffer_triple raw_plot(raw_plot_length);
static struct hydrophones_settings shm_settings;
static struct hydrophones_results_track shm_results_track;
static int trigger_packet_no;
static buffer_triple trigger_plot(trigger_plot_length);

void slidingDFTBin(triple_phasor &X, const buffer_triple &signal_buffer, int buffer_length, int dft_length, float target_frequency, float sampling_rate)
{
    //Updates a DFT bin on every new sample. Sliding window is dft_length samples long.
    
    triple_phasor new_term, term_to_remove;
    float w0_n;
    
    w0_n = 2 * M_PI * round(target_frequency * dft_length / sampling_rate) / dft_length; //target frequency normalized to the range [0, 2 pi)
    
    new_term = signal_buffer.read(buffer_length - 1);
    term_to_remove = signal_buffer.read(buffer_length - 1 - dft_length);
    
    X = (X + new_term - term_to_remove) * std::exp(std::complex<float>(0, 1) * w0_n);
}

void scalePlot(buffer &plot, int plot_length, float scaling_factor)
{
    //Multiplies all of the values in a plot by "scaling_factor".
    
    for(int data_point_no = 0; data_point_no < plot_length; data_point_no++)
    {
        plot.push(plot.read(0) * scaling_factor);
    }
}

void savePlot(const buffer_triple &data_buffer, int data_buffer_length, buffer_triple &copy_buffer, int copy_length, float scaling_factor)
{
    //Saves the last "copy length" values in a triple buffer.

    for(int data_point_no = 0; data_point_no < copy_length; data_point_no++)
    {
        copy_buffer.push(data_buffer.read(data_point_no + data_buffer_length - copy_length) * scaling_factor);
        //function also scales a plot while saving, to avoid running through the values twice. we need a separate scaling function because dft plot buffers are continuously pushed to, not captured via this function
    }
}

void normalizePhase(float &phase, float reference)
{
    //Converts an absolute phase to a phase difference relative to the reference. Brings the result to the interval (-PI, PI].
    
    phase = phase - reference; //it is impossible for this to be smaller than -2 * PI or larger than 2 * PI
    if(phase < -M_PI)
    {
        phase += 2 * M_PI;
    }
    if(phase > M_PI)
    {
        phase -= 2 * M_PI;
    }
}

void computeHeading(triple_sample ping_phase, float frequency, float &heading, float &elevation, bool &elevation_correct)
{
    //Computes heading and elevation based on the phase differences relative to the reference. Reports if the obtained elevation is valid.
    
    float cos_elevation;
    float path_diff_1, path_diff_2;
    bool is_mainsub;
    
    is_mainsub = strcmp(std::getenv("CUAUV_VEHICLE_TYPE"), "mainsub") == 0;
    
    path_diff_1 = ping_phase.ch1 * sound_speed / (2 * M_PI * frequency);
    path_diff_2 = ping_phase.ch2 * sound_speed / (2 * M_PI * frequency);
    
    if(is_mainsub)
    {
        heading = atan2(path_diff_1, -path_diff_2);
    }
    else
    {
        heading = atan2(path_diff_1, -path_diff_2);
    }
    
    cos_elevation = sqrt((path_diff_1 * path_diff_1 + path_diff_2 * path_diff_2)) / nipple_distance;
    if(cos_elevation > 1) //this can happen if the measured path differences are larger than they can theoretically be for a certain frequency
    {
        elevation = 0; //path differences are maximized when sub is in plane with pinger, aka 0 elevation
        elevation_correct = 0; //on the highest frequency, this can also hint aliasing since our transducer separation is close to the maximum allowed
    }
    else
    {
        elevation = acos(cos_elevation);
        elevation_correct = 1;
    }
}

void pinger_tracking_dsp(uint16_t *fpga_packet, bool reset_signal)
{
    //Main function, executes every packet and controls the pinger tracking program flow.
    
    if(reset_signal == 1)
    {
        packet_no = 0;
    }
    
    //preparing for a new interval. every interval is guaranteed to contain at least one ping
    if(packet_no == 0)
    {
        bool freq_ok = 0;
        
        dft_peak = 0;
        dft_ratio_plot_peak = 0;
        dft_ratio_good_peak = 0;
        noise_sum = 0;
        ping_phase = triple_sample();
        raw_buffer.clear();
        raw_peak = 0;
        trigger_packet_no = 0;
        
        for(int freq_no = 0; freq_no < freq_list_length; freq_no++)
        {
            last_dft_result[freq_no] = triple_phasor();
        }

        printf("%s \n", "new interval. mode: tracking");
        
        shm_getg(hydrophones_settings, shm_settings);
        
        //the desired gain is set everytime a new interval starts
        setGain(gain_lvl);
        printf("%s%d \n", "gain: x", gainz[gain_lvl]);
        
        //checking whether the shm frequency target setting is correct (present in the hardcoded frequency list)
        for(int freq_no = 0; freq_no < freq_list_length; freq_no++)
        {
            if(shm_settings.track_frequency_target == freqs[freq_no])
            {
                good_freq_no = freq_no;
                freq_ok = 1;
                break;
            }
        }
        if(freq_ok == 1)
        {
            printf("%s %d %s \n", "tracking", freqs[good_freq_no], "Hz");
        }
        else
        {
            printf("%s %d %s \n", "WARNING TARGET FREQUENCY INVALID. UPDATE FREQ LIST AND DFT LENGTH OR CHOOSE A VALID FREQUENCY. tracking", freqs[good_freq_no], "Hz");
        }
    }

    //actual operations for an interval only start after the fpga has had enough time to set the gain
    if(packet_no >= gain_propagation_packets)
    {
        float average_noise;
        float dft_ratio = 0;
        
        average_noise = noise_sum / (packet_no - gain_propagation_packets + 1);

        //operations performed on every triple_sample in a packet
        for(int packet_sample_no = 0; packet_sample_no < packet_length; packet_sample_no++)
        {
            //this section executes on every sample
            
            triple_sample new_raw_sample;
            
            //pushing each triple_sample into the raw triple_sample buffer
            new_raw_sample.ch0 = fpga_packet[4 * packet_sample_no + 0];
            new_raw_sample.ch1 = fpga_packet[4 * packet_sample_no + 1];
            new_raw_sample.ch2 = fpga_packet[4 * packet_sample_no + 2];
            raw_buffer.push(new_raw_sample);
            
            triple_sample new_normalized_sample;
            new_normalized_sample.ch0 = new_raw_sample.ch0 - (highest_quantization_lvl / 2);
            new_normalized_sample.ch1 = new_raw_sample.ch1 - (highest_quantization_lvl / 2);
            new_normalized_sample.ch2 = new_raw_sample.ch2 - (highest_quantization_lvl / 2);
            //printAudible(new_normalized_sample);
            
            //everytime we get a record high triple_sample in the interval, we check for clipping (if autogain is on), and we rewrite the raw plot to capture the signal around this value
            if(new_raw_sample.max() > raw_peak)
            {
                raw_peak = new_raw_sample.max();
                    
                if(shm_settings.auto_gain == 1)
                {
                    if(raw_peak > clipping_threshold * highest_quantization_lvl)
                    {
                        printf("%s \n","clipping detected");
                        
                        if(gain_lvl > 0)
                        {
                            gain_lvl--; //decreasing the gain for the next interval
                            
                            printf("%s \n", "gain decreased");
                            
                            goto end_interval; //clipping invalidates the whole interval
                        }
                        else
                        {
                            printf("%s \n", "gain cannot be decreased further!");
                        }
                    }
                }
                
                savePlot(raw_buffer, raw_buffer_length, raw_plot, raw_plot_length, raw_plot_length / highest_quantization_lvl);
            }
            
            //updating the DFT results buffer
            for(int freq_no = 0; freq_no < freq_list_length; freq_no++)
            {
                slidingDFTBin(last_dft_result[freq_no], raw_buffer, raw_buffer_length, dft_length, freqs[freq_no], sampling_rate);
            }
            dft_results_buffer.push(last_dft_result[good_freq_no].combinedAmplitude());
            
            //calculating the ratio between the amplitudes of two non-overlapping windows, our function of interest for triggering
            if(packet_no >= gain_propagation_packets + ceil(2 * (float)dft_length / (float)packet_length))
            {
                dft_ratio = (dft_results_buffer.read(dft_length) + average_noise) / (dft_results_buffer.read(0) + average_noise);
                //when calculating the ratio, we add to both amplitudes the noise level first. this hurts cases when the amplitudes are very small and prevents triggering on random noise
                
                //handling a record high ratio - potential triggering event
                if(dft_ratio > dft_ratio_good_peak)
                {
                    bool reject_event = 0;
                    
                    for(int freq_no = 0; freq_no < freq_list_length; freq_no++)
                    {
                        if(last_dft_result[freq_no].combinedAmplitude() > dft_results_buffer.read(dft_length))
                        {
                            reject_event = 1;
                            break;
                        }
                    }
                    
                    if(reject_event != 1)
                    {
                        dft_ratio_good_peak = dft_ratio;
                        
                        //keeping the phase for this potential trigger event and updating the trigger packet number
                        ping_phase = last_dft_result[good_freq_no].phase();
                        trigger_packet_no = packet_no;
                    
                        //rewriting the trigger plot to capture the signal around the trigger sample
                        savePlot(raw_buffer, raw_buffer_length, trigger_plot, trigger_plot_length, trigger_plot_length / highest_quantization_lvl);
                    }
                }
            }
        }
        
        //this section only executes once per packet, using the last dft window
        
        //updating the average dft result magnitude, which can be considered the noise level in our case since we only have very short pings. updating the noise level on every sample is superfluous.
        noise_sum += dft_results_buffer.read(dft_length);
    
        //updating the amplitudes part of the dft plot for this interval. plot wouldn't have enough resolution to show dft results for every sample
        dft_plot_amplitudes.push(dft_results_buffer.read(dft_length));
        if(dft_results_buffer.read(dft_length) > dft_peak) //highest value needed for plot scaling
        {
            dft_peak = dft_results_buffer.read(dft_length);
        }
        
        //updating the ratios part of the dft plot for the interval
        dft_plot_ratios.push(dft_ratio);
        if(dft_ratio > dft_ratio_plot_peak) //highest value needed for plot scaling
        {
            dft_ratio_plot_peak = dft_ratio;
        }
    }
    
    //incrementing the interval packet counter
    packet_no++;
    
    //ending an interval
    if(packet_no == (int)(pinger_period * pinger_period_factor * sampling_rate / packet_length))
    {
        float elevation;
        bool elevation_correct;
        float heading;

        //increasing gain for the next interval if signal would not have clipped on higher gain (if autogain enabled)
        if(shm_settings.auto_gain == 1)
        {
            if(increaseGain(raw_peak, gain_lvl) == 1)
            {
                printf("%s \n", "gain increased");
            }
        }
        else
        {
            gain_lvl = shm_settings.target_gain; //ensuring the gain in sync with shm if autogain is off
        }
        
        //scaling the plots and adding the trigger packet number to the dft plot. it could not be done on the go because we didn't know the peak values for the interval
        //scaling means making the plot square and having the highest value on the very top / lowest value on the very bottom
        //we want square plots because the penguin meme is a square image
        scalePlot(dft_plot_amplitudes, dft_plot_length, dft_plot_length / dft_peak);
        scalePlot(dft_plot_ratios, dft_plot_length, dft_plot_length / dft_ratio_plot_peak);
        dft_plot_trigger_point.push((float)(trigger_packet_no - gain_propagation_packets));
        
        //sending the plots via UDP to the Python scripts
        sendPlot(raw_plot.get(0), 0, raw_plot_length);
        sendPlot(raw_plot.get(1), 0, raw_plot_length);
        sendPlot(raw_plot.get(2), 0, raw_plot_length);
        sendPlot(trigger_plot.get(0), 1, trigger_plot_length);
        sendPlot(trigger_plot.get(1), 1, trigger_plot_length);
        sendPlot(trigger_plot.get(2), 1, trigger_plot_length);
        sendPlot(dft_plot_amplitudes.get(), 2, dft_plot_length);
        sendPlot(dft_plot_ratios.get(), 2, dft_plot_length);
        sendPlot(dft_plot_trigger_point.get(), 2, 1);

        //computing the heading and elevation based on the phase saved from the trigger packet
        normalizePhase(ping_phase.ch1, ping_phase.ch0);
        normalizePhase(ping_phase.ch2, ping_phase.ch0);
        computeHeading(ping_phase, shm_settings.track_frequency_target, heading, elevation, elevation_correct);
        
        //updating the shm results
        shm_results_track.tracked_ping_heading_radians = heading;
        shm_results_track.tracked_ping_elevation_radians = elevation;
        //shm_results_track.tracked_ping_elevation_correct = elevation_correct;
        shm_setg(hydrophones_results_track, shm_results_track);
        //shm_setg(shm_results_track);
        
        //in case of clipping, no plots shown and no headings calculated
        end_interval:
        
        packet_no = 0;
        
        printf("%s %4.2f%s \n", "signal peak was:", raw_peak / highest_quantization_lvl * 100, "% of highest quantization level");
        
        printf("\n");
    }
}
