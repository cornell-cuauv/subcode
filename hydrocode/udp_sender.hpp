//
//  udp_sender.hpp
//  hydromathd
//
//  Created by Vlad on 9/15/18.
//  Copyright © 2018 Vlad. All rights reserved.
//

#ifndef udp_sender_hpp
#define udp_sender_hpp

#define UDP_RAW_PLOT_ADDRESS "192.168.22.1" //local host because the plotting scripts are on the same machine
const int udp_raw_plot_port = 9001; //raw plot script listens on this port

#define UDP_TRIGGER_PLOT_ADDRESS "192.168.22.1" //local host because the plotting scripts are on the same machine
const int udp_trigger_plot_port = 9002; //trigger plot script listens on this port

#define UDP_DFT_PLOT_ADDRESS "192.168.22.1" //local host because the plotting scripts are on the same machine
const int udp_dft_plot_port = 9003; ////dft plot script listens on this port

#define UDP_FIX_FPGA_PLOT_ADDRESS "192.168.22.1"
const int udp_fix_fpga_plot_port = 9004;

#define UDP_GAIN_ADDRESS "192.168.91.13" //FPGA IP address
const int udp_gain_port = 5005; //FPGA listens on this port for gain settings

const int udp_gain_payload_size = 2; //size of the FPGA gain setting packet (in bytes)
const int udp_send_payload_size = 512; //size of the UDP plot packets (in bytes). don't go over like 1024

void udpSenderInit();
void sendPlot(float *values, int plot_type, int plot_length);
void sendGain(char *gain_packet);

#endif /* udp_sender_hpp */
