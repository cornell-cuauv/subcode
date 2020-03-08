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
#include <memory>

class UDPSampleReceiver {
public:
	UDPSampleReceiver(unsigned int port, unsigned int pkt_len);
	void recv();
	unsigned int getPktNum(void);
	unsigned int getGainLvl(void);
	float getMaxSample(void);
	float getSample(unsigned int ch_num, unsigned int sample_num);

private:
	static const unsigned int PKT_HEADER_SIZE;
	static const unsigned int NUM_CHS;
	static const unsigned int PKT_NUM_OFFSET;
	static const unsigned int GAIN_LVL_OFFSET;
	static const unsigned int MAX_SAMPLE_OFFSET;

	unsigned int pkt_len;
	int sock;
	std::unique_ptr<uint8_t[]> buff;
};

#endif /* udp_receiver_hpp */

