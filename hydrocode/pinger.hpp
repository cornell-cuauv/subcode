//
//  pinger.hpp
//  hydromathd
//
//  Created by Vlad on 7/31/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#ifndef pinger_hpp
#define pinger_hpp

#include <cstdint>

#include <complex>
#include "liquid.h"

float calcHdg(float path_diff1, float path_diff2, float sub_hdg);
float calcElev(float path_diff1, float path_diff2, float sample_distance);

class Averager {
public:
	Averager(unsigned int len);
	~Averager(void);
	float push(float in_sample);

private:
	unsigned int len;
	float avg;
	windowf buff;
};

class ComplexAverager {
public:
	ComplexAverager(unsigned int len);
	~ComplexAverager(void);
	std::complex<float> push(std::complex<float> in_sample);

private:
	unsigned int len;
	std::complex<float> avg;
	windowcf buff;
};

class GainControl {
public:
	static const unsigned int GAINZ[14];

	static unsigned int calcGain(float max_sample, unsigned int curr_gain_lvl);

private:
	static const float CLIPPING_THRESHOLD;
	static const float CLIPPING_THRESHOLD_HYSTERESIS;
};

class GaussTuner {
public:
	GaussTuner(unsigned int in_sample_rate, unsigned int decim_factor, unsigned int freq, unsigned int stopband);
	~GaussTuner(void);
	bool push(float in_sample);
	void setFreq(unsigned int freq);
	unsigned int getFiltRiseTime(void);
	std::complex<float> getSample(void);

private:
	static const unsigned int STOPBAND_ATTEN;
	static const unsigned int FILT_RISE_RATIO;
	static const unsigned int NUM_FILT_STAGES;

	std::uint64_t n;
	unsigned int in_sample_rate;
	unsigned int decim_factor;
	unsigned int stopband;
	std::complex<float> conv_sample;

	nco_crcf mix_osc;
	ComplexAverager filt_stage1;
	ComplexAverager filt_stage2;
	ComplexAverager filt_stage3;
	ComplexAverager filt_stage4;

	static unsigned int calcFiltLen(unsigned int sample_rate, unsigned int stopband);
};

#endif /* pinger_hpp */

