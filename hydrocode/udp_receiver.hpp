//
//  udp_receiver.hpp
//  hydromathd
//
//  Created by Vlad on 9/10/18.
//  Copyright © 2018 Vlad. All rights reserved.
//

#ifndef udp_receiver_hpp
#define udp_receiver_hpp

#include <cstdint>

class UDPSampleReceiver {
public:
	UDPSampleReceiver(unsigned int port, unsigned int pkt_len);
	~UDPSampleReceiver(void);
	void recv();
	unsigned int getPktNum(void);
	unsigned int getPingerGainLvl(void);
	unsigned int getCommsGainLvl(void);
	float getPingerMaxSample(void);
	float getCommsMaxSample(void);
	float getSample(unsigned int ch_num, unsigned int sample_num);

private:
	static const unsigned int PKT_HEADER_SIZE;
	static const unsigned int NUM_CHS;
	static const unsigned int PKT_NUM_OFFSET;
	static const unsigned int PINGER_GAIN_LVL_OFFSET;
	static const unsigned int COMMS_GAIN_LVL_OFFSET;
	static const unsigned int PINGER_MAX_SAMPLE_OFFSET;
	static const unsigned int COMMS_MAX_SAMPLE_OFFSET;

	unsigned int pkt_len;
	int sock;
	std::uint8_t *buff;
};

#endif /* udp_receiver_hpp */

