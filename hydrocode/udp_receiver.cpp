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
const unsigned int UDPSampleReceiver::PINGER_GAIN_LVL_OFFSET = 4;
const unsigned int UDPSampleReceiver::COMMS_GAIN_LVL_OFFSET = 5;
const unsigned int UDPSampleReceiver::PINGER_MAX_SAMPLE_OFFSET = 6;
const unsigned int UDPSampleReceiver::COMMS_MAX_SAMPLE_OFFSET = 8;

UDPSampleReceiver::UDPSampleReceiver(unsigned int port, unsigned int pkt_len):
pkt_len(pkt_len),
sock(socket(AF_INET, SOCK_DGRAM, 0)),
buff(new std::uint8_t[NUM_CHS * pkt_len * sizeof(std::int16_t) + PKT_HEADER_SIZE]) {
	struct sockaddr_in serv_addr;

	serv_addr.sin_family = AF_INET;
	serv_addr.sin_port = htons(port);
	serv_addr.sin_addr.s_addr = INADDR_ANY;

	int status = bind(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr));
	if (status) {
		printf("\nCan't bind sample receive socket\n\n");
	}
}
UDPSampleReceiver::~UDPSampleReceiver(void) {
	delete [] buff;
}
void UDPSampleReceiver::recv(void) {
	recvfrom(sock, buff, NUM_CHS * pkt_len * sizeof(std::int16_t) + PKT_HEADER_SIZE, 0, NULL, NULL);
}
unsigned int UDPSampleReceiver::getPktNum(void) {
	std::uint32_t pkt_num;

	std::memcpy(&pkt_num, buff + PKT_NUM_OFFSET, sizeof(std::uint32_t));

	return pkt_num;
}
unsigned int UDPSampleReceiver::getPingerGainLvl(void) {
	std::uint8_t gain_lvl;

	std::memcpy(&gain_lvl, buff + PINGER_GAIN_LVL_OFFSET, sizeof(std::uint8_t));

	return gain_lvl;
}
unsigned int UDPSampleReceiver::getCommsGainLvl(void) {
	std::uint8_t gain_lvl;

	std::memcpy(&gain_lvl, buff + COMMS_GAIN_LVL_OFFSET, sizeof(std::uint8_t));

	return gain_lvl;
}
float UDPSampleReceiver::getPingerMaxSample(void) {
	std::uint16_t max_sample;

	std::memcpy(&max_sample, buff + PINGER_MAX_SAMPLE_OFFSET, sizeof(std::uint8_t));

	return max_sample;
}
float UDPSampleReceiver::getCommsMaxSample(void) {
	std::uint16_t max_sample;

	std::memcpy(&max_sample, buff + COMMS_MAX_SAMPLE_OFFSET, sizeof(std::uint8_t));

	return max_sample;
}
float UDPSampleReceiver::getSample(unsigned int ch_num, unsigned int sample_num) {
	std::int16_t sample;

	std::memcpy(&sample, buff + PKT_HEADER_SIZE + (sample_num * NUM_CHS + ch_num) * sizeof(std::int16_t), sizeof(std::int16_t));

	return sample;
}

