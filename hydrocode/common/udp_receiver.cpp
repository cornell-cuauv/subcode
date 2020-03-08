//
//  udp_receiver.cpp
//  hydromathd
//
//  Created by Vlad on 9/10/18.
//  Copyright © 2018 Vlad. All rights reserved.
//

#include "udp_receiver.hpp"

#include <cstdio>
#include <cstring>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

const unsigned int UDPSampleReceiver::PKT_HEADER_SIZE = 10;
const unsigned int UDPSampleReceiver::NUM_CHS = 8;
const unsigned int UDPSampleReceiver::PKT_NUM_OFFSET = 0;
const unsigned int UDPSampleReceiver::GAIN_LVL_OFFSET = 4;
const unsigned int UDPSampleReceiver::MAX_SAMPLE_OFFSET = 6;

UDPSampleReceiver::UDPSampleReceiver(unsigned int port, unsigned int pkt_len):
pkt_len(pkt_len),
sock(socket(AF_INET, SOCK_DGRAM, 0)),
buff(new uint8_t[NUM_CHS * pkt_len * sizeof(std::int16_t) + PKT_HEADER_SIZE]) {
	sockaddr_in serv_addr;

	serv_addr.sin_family = AF_INET;
	serv_addr.sin_port = htons(port);
	serv_addr.sin_addr.s_addr = INADDR_ANY;

	int status = bind(sock, reinterpret_cast<sockaddr*>(&serv_addr), sizeof(serv_addr));
	if (status) {
		printf("\nCan't bind sample receive socket\n\n");
	}
}

void UDPSampleReceiver::recv(void) {
	recvfrom(sock, buff.get(), NUM_CHS * pkt_len * sizeof(std::int16_t) + PKT_HEADER_SIZE, 0, NULL, NULL);
}
unsigned int UDPSampleReceiver::getPktNum(void) {
	std::uint32_t pkt_num;

	std::memcpy(&pkt_num, buff.get() + PKT_NUM_OFFSET, sizeof(std::uint32_t));

	return pkt_num;
}
unsigned int UDPSampleReceiver::getGainLvl(void) {
	std::uint8_t gain_lvl;

	std::memcpy(&gain_lvl, buff.get() + GAIN_LVL_OFFSET, sizeof(std::uint8_t));

	return gain_lvl;
}
float UDPSampleReceiver::getMaxSample(void) {
	std::uint16_t max_sample;

	std::memcpy(&max_sample, buff.get() + MAX_SAMPLE_OFFSET, sizeof(std::uint16_t));

	return max_sample;
}
float UDPSampleReceiver::getSample(unsigned int ch_num, unsigned int sample_num) {
	std::int16_t sample;

	std::memcpy(&sample, buff.get() + PKT_HEADER_SIZE + (sample_num * NUM_CHS + ch_num) * sizeof(std::int16_t), sizeof(std::int16_t));

	return sample;
}

