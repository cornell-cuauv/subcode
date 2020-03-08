//
//  udp_sender.cpp
//  hydromathd
//
//  Created by Vlad on 9/15/18.
//  Copyright © 2018 Vlad. All rights reserved.
//

#include "udp_sender.hpp"

#include <cstdio>
#include <cstring>
#include <sys/socket.h>
#include <arpa/inet.h>

const unsigned int UDPBoardConfigSender::PKT_SIZE = 3;
const unsigned int UDPBoardConfigSender::RESET_OFFSET = 0;
const unsigned int UDPBoardConfigSender::AUTOGAIN_OFFSET = 1;
const unsigned int UDPBoardConfigSender::MAN_GAIN_LVL_OFFSET = 2;

const unsigned int UDPPlotSender::PKT_SIZE = 512;

UDPBoardConfigSender::UDPBoardConfigSender(const char addr[], unsigned int port):
sock(socket(AF_INET, SOCK_DGRAM, 0)),
buff(new std::uint8_t[PKT_SIZE]) {
	if (sock == -1) {
		std::printf("\nCan't create board config socket\n\n");
	}

	serv_addr.sin_family = AF_INET;
	serv_addr.sin_port = htons(port);
	serv_addr.sin_addr.s_addr = inet_addr(addr);
}
void UDPBoardConfigSender::send(void) {
	sendto(sock, buff.get(), PKT_SIZE, 0, reinterpret_cast<sockaddr*>(&serv_addr), sizeof(serv_addr));
}
void UDPBoardConfigSender::setReset(std::uint8_t setting) {
	std::memcpy(buff.get() + RESET_OFFSET, &setting, sizeof(std::uint8_t));
}
void UDPBoardConfigSender::setAutogain(std::uint8_t setting) {
	std::memcpy(buff.get() + AUTOGAIN_OFFSET, &setting, sizeof(std::uint8_t));
}
void UDPBoardConfigSender::setGainLvl(std::uint8_t gain_lvl) {
	std::memcpy(buff.get() + MAN_GAIN_LVL_OFFSET, &gain_lvl, sizeof(std::uint8_t));
}

UDPPlotSender::UDPPlotSender(const char addr[], unsigned int port, unsigned int num_signals, unsigned int signal_len):
num_signals(num_signals),
signal_len(signal_len),
sock(socket(AF_INET, SOCK_DGRAM, 0)),
buff(new float[num_signals * signal_len]) {
	if (sock == -1) {
		std::printf("\nCan't create plot display socket\n\n");
	}

	serv_addr.sin_family = AF_INET;
	serv_addr.sin_port = htons(port);
	serv_addr.sin_addr.s_addr = inet_addr(addr);
}
void UDPPlotSender::send(void) {
	for (unsigned int signal_num = 0; signal_num < num_signals; signal_num++) {
		const unsigned int num_full_packets = signal_len * sizeof(float) / PKT_SIZE;
		const unsigned int partial_pkt_size = signal_len * sizeof(float) % PKT_SIZE;

		for (unsigned int pkt_num = 0; pkt_num < num_full_packets; pkt_num++) {
			sendto(sock, buff.get() + signal_num * signal_len + pkt_num * PKT_SIZE / sizeof(float), PKT_SIZE, 0, reinterpret_cast<sockaddr*>(&serv_addr), sizeof(serv_addr));
		}

		if (partial_pkt_size != 0) {
			sendto(sock, buff.get() + signal_num * signal_len + num_full_packets * PKT_SIZE / sizeof(float), partial_pkt_size, 0, reinterpret_cast<sockaddr*>(&serv_addr), sizeof(serv_addr));
		}
	}
}
void UDPPlotSender::takeReal(unsigned int signal_num, windowf &source, unsigned int source_end_index) {
	float *buff_ptr;

	windowf_read(source, &buff_ptr);

	std::memcpy(buff.get() + signal_num * signal_len, buff_ptr + source_end_index - signal_len, signal_len * sizeof(float));
}
void UDPPlotSender::takeComplex(unsigned int signal_num, windowcf &source, unsigned int source_end_index) {
	std::complex<float> *buff_ptr;

	windowcf_read(source, &buff_ptr);

	std::memcpy(buff.get() + signal_num * signal_len, reinterpret_cast<float*>(buff_ptr + source_end_index) - signal_len, signal_len * sizeof(float));
}

