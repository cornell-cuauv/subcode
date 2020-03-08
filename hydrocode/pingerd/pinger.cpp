//
//  pinger.cpp
//  hydromathd
//
//  Created by Vlad on 7/31/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#include "pinger.hpp"

#include <cstdlib>
#include <cmath>
#include <cstring>

const std::vector<unsigned int> GainControl::GAINZ = {1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128};
const unsigned int GainControl::CLIPPING_THRESHOLD = 8000;
const unsigned int GainControl::CLIPPING_THRESHOLD_HYSTERESIS = 200;

const unsigned int GaussTuner::STOPBAND_ATTEN = 60;
const unsigned int GaussTuner::FILT_RISE_RATIO = 100;
const unsigned int GaussTuner::NUM_FILT_STAGES = 4;

float calcHdg(float path_diff1, float path_diff2, float sub_hdg) {
	bool is_mainsub;
	
	is_mainsub = strcmp(std::getenv("CUAUV_VEHICLE_TYPE"), "mainsub") == 0;
	is_mainsub = 0;
	
	if (is_mainsub) {
		return std::fmod(static_cast<float>(std::atan2(path_diff2, path_diff1) * 180) / M_PI + sub_hdg, 360);
	} else {
		return std::fmod(static_cast<float>(std::atan2(-path_diff1, path_diff2) * 180) / M_PI + sub_hdg, 360);
	}
}

float calcElev(float path_diff1, float path_diff2, float sample_distance) {
	float cos_elev = static_cast<float>(std::sqrt(path_diff1 * path_diff1 + path_diff2 * path_diff2)) / sample_distance;
	
	if (cos_elev < 1) {
		return static_cast<float>(std::acos(cos_elev) * 180) / M_PI;
	} else {
		return 0;
	}
}

Averager::Averager(unsigned int len):
len(len),
avg(0),
buff(windowf_create(len)) {
}
Averager::~Averager(void) {
	windowf_destroy(buff);
}
float Averager::push(float in_sample) {
	float oldest_sample;
	
	windowf_index(buff, 0, &oldest_sample);
	windowf_push(buff, in_sample);
	avg += static_cast<float>(in_sample - oldest_sample) / len;
	
	return avg;
}

ComplexAverager::ComplexAverager(unsigned int len):
len(len),
avg(0),
buff(windowcf_create(len)) {
}
ComplexAverager::~ComplexAverager(void) {
	windowcf_destroy(buff);
}
std::complex<float> ComplexAverager::push(std::complex<float> in_sample) {
	std::complex<float> oldest_sample;
	
	windowcf_index(buff, 0, &oldest_sample);
	windowcf_push(buff, in_sample);
	avg += (in_sample - oldest_sample) / static_cast<float>(len);
	
	return avg;
}

unsigned int GainControl::calcGain(float max_sample, unsigned int curr_gain_lvl) {
	unsigned int new_gain_lvl = curr_gain_lvl;
	
	if (max_sample > CLIPPING_THRESHOLD) {
		if (curr_gain_lvl > 0) {
			new_gain_lvl = curr_gain_lvl - 1;
		}
	} else {
		for (unsigned int try_gain_lvl = static_cast<unsigned int>(GAINZ.size()); try_gain_lvl > curr_gain_lvl; try_gain_lvl--) {
			if (static_cast<float>(max_sample) / GAINZ[curr_gain_lvl] * GAINZ[try_gain_lvl] < CLIPPING_THRESHOLD - CLIPPING_THRESHOLD_HYSTERESIS) {
				new_gain_lvl = try_gain_lvl;
				break;
			}
		}
	}
	
	return new_gain_lvl;
}

GaussTuner::GaussTuner(unsigned int in_sample_rate, unsigned int freq, unsigned int stopband):
in_sample_rate(in_sample_rate),
stopband(stopband),
filt_rise_time(calcFiltRiseTime()),
filt_len(calcFiltLen(in_sample_rate, stopband)),
conv_sample(0),
mix_osc(nco_crcf_create(LIQUID_NCO)),
filt_stage1(filt_len),
filt_stage2(filt_len),
filt_stage3(filt_len),
filt_stage4(filt_len) {
	float f0_hat = static_cast<float>(freq) / in_sample_rate;
	
	nco_crcf_set_phase(mix_osc, 0);
	nco_crcf_set_frequency(mix_osc, 2 * M_PI * f0_hat);
}
GaussTuner::~GaussTuner(void) {
	nco_crcf_destroy(mix_osc);
}
void GaussTuner::push(float in_sample) {
	std::complex<float> mixed;
	
	nco_crcf_mix_down(mix_osc, in_sample, &mixed);
	nco_crcf_step(mix_osc);
	
	conv_sample = filt_stage4.push(filt_stage3.push(filt_stage2.push(filt_stage1.push(mixed))));
}
void GaussTuner::setFreq(unsigned int freq) {
	float f0_hat = static_cast<float>(freq) / in_sample_rate;
	
	nco_crcf_set_frequency(mix_osc, 2 * M_PI * f0_hat);
}
unsigned int GaussTuner::getFiltRiseTime(void) {
	return filt_rise_time;
}
unsigned int GaussTuner::getFiltLen(void) {
	return filt_len;
}
std::complex<float> GaussTuner::getSample(void) {
	return conv_sample;
}
unsigned int GaussTuner::calcFiltRiseTime(void) {
	float stopband_hat = static_cast<float>(stopband) / in_sample_rate;

	return static_cast<unsigned int>(static_cast<float>(std::sqrt(16 * std::log(FILT_RISE_RATIO) * std::log(10) * static_cast<float>(STOPBAND_ATTEN) / 20)) / (M_PI * stopband_hat));
}
unsigned int GaussTuner::calcFiltLen(unsigned int sample_rate, unsigned int stopband) {
	float stopband_hat = static_cast<float>(stopband) / sample_rate;
	
	return static_cast<unsigned int>(std::sqrt(1 + 24 * std::log(10) * static_cast<float>(static_cast<float>(STOPBAND_ATTEN) / 20) / (NUM_FILT_STAGES * M_PI * M_PI * stopband_hat * stopband_hat)));
}

