//
//  udp_sender.hpp
//  hydromathd
//
//  Created by Vlad on 9/15/18.
//  Copyright © 2018 Vlad. All rights reserved.
//

#ifndef udp_sender_hpp
#define udp_sender_hpp

#include <cstdint>
#include <netinet/in.h>

#include <complex>
#include "liquid.h"

struct sockaddr_in;

class UDPBoardConfigSender {
public:
	UDPBoardConfigSender(const char addr[], unsigned int port);
	~UDPBoardConfigSender(void);
	void send(void);
	void setReset(std::uint8_t setting);
	void setPingerAutogain(std::uint8_t setting);
	void setCommsAutogain(std::uint8_t setting);
	void setPingerGainLvl(std::uint8_t gain_lvl);
	void setCommsGainLvl(std::uint8_t gain_lvl);

private:
	static const unsigned int PKT_SIZE;
	static const unsigned int RESET_OFFSET;
	static const unsigned int PINGER_AUTOGAIN_OFFSET;
	static const unsigned int PINGER_MAN_GAIN_LVL_OFFSET;
	static const unsigned int COMMS_AUTOGAIN_OFFSET;
	static const unsigned int COMMS_MAN_GAIN_LVL_OFFSET;

	int sock;
	struct sockaddr_in serv_addr;
	std::uint8_t *buff;
};

class UDPPlotSender {
public:
	UDPPlotSender(const char addr[], unsigned int port, unsigned int num_signals, unsigned int signal_len);
	~UDPPlotSender(void);
	void send(void);
	void takeReal(unsigned int signal_num, windowf source, unsigned int source_len);
	void takeComplex(unsigned int signal_num, windowcf source, unsigned int source_len);

private:
	static const unsigned int PKT_SIZE;

	unsigned int num_signals;
	unsigned int signal_len;
	int sock;
	struct sockaddr_in serv_addr;
	float *buff;
};

#endif /* udp_sender_hpp */
