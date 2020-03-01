//
//  pinger.cpp
//  hydromathd
//
//  Created by Vlad on 7/31/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#include "pinger.hpp"

#include <cmath>

const unsigned int GainControl::GAINZ[14] = {1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128};
const float GainControl::CLIPPING_THRESHOLD = 8000;
const float GainControl::CLIPPING_THRESHOLD_HYSTERESIS = 200;

const unsigned int GaussTuner::STOPBAND_ATTEN = 60;
const unsigned int GaussTuner::FILT_RISE_RATIO = 100;
const unsigned int GaussTuner::NUM_FILT_STAGES = 4;

float calcHdg(float path_diff1, float path_diff2, float sub_hdg) {
	bool is_mainsub;
	
	//is_mainsub = strcmp(std::getenv("CUAUV_VEHICLE_TYPE"), "mainsub") == 0;
	is_mainsub = 0;
	
	if (is_mainsub) {
		return std::fmod(std::atan2(path_diff2, path_diff1) * 180.0f / M_PI + sub_hdg, 360.0f);
	} else {
		return std::fmod(std::atan2(-path_diff1, path_diff2) * 180.0f / M_PI + sub_hdg, 360.0f);
	}
}

float calcElev(float path_diff1, float path_diff2, float sample_distance) {
	float cos_elev = std::sqrt((path_diff1 * path_diff1 + path_diff2 * path_diff2)) / sample_distance;
	
	if (cos_elev < 1) {
		return std::acos(cos_elev) * 180.0f / M_PI;
	} else {
		return 0.0f;
	}
}

Averager::Averager(unsigned int len):
len(len),
avg(0.0f),
buff(windowf_create(len)) {
}
Averager::~Averager(void) {
	windowf_destroy(buff);
}
float Averager::push(float in_sample) {
	float oldest_sample;
	
	windowf_index(buff, 0, &oldest_sample);
	windowf_push(buff, in_sample);
	avg += (in_sample - oldest_sample) / (float)len;
	
	return avg;
}

ComplexAverager::ComplexAverager(unsigned int len):
len(len),
avg(0.0f),
buff(windowcf_create(len)) {
}
ComplexAverager::~ComplexAverager(void) {
	windowcf_destroy(buff);
}
std::complex<float> ComplexAverager::push(std::complex<float> in_sample) {
	std::complex<float> oldest_sample;
	
	windowcf_index(buff, 0, &oldest_sample);
	windowcf_push(buff, in_sample);
	avg += (in_sample - oldest_sample) / (std::complex<float>)len;
	
	return avg;
}

unsigned int GainControl::calcGain(float max_sample, unsigned int curr_gain_lvl) {
	unsigned int new_gain_lvl = curr_gain_lvl;
	
	if (max_sample > CLIPPING_THRESHOLD) {
		if (curr_gain_lvl > 0) {
			new_gain_lvl = curr_gain_lvl - 1;
		}
	} else {
		for (unsigned int try_gain_lvl = 13; try_gain_lvl > curr_gain_lvl; try_gain_lvl--) {
			if (max_sample / (float)GAINZ[curr_gain_lvl] * (float)GAINZ[try_gain_lvl] < CLIPPING_THRESHOLD - CLIPPING_THRESHOLD_HYSTERESIS) {
				new_gain_lvl = try_gain_lvl;
				break;
			}
		}
	}
	
	return new_gain_lvl;
}

GaussTuner::GaussTuner(unsigned int in_sample_rate, unsigned int decim_factor, unsigned int freq, unsigned int stopband):
n(0),
in_sample_rate(in_sample_rate),
decim_factor(decim_factor),
stopband(stopband),
conv_sample(0.0f),
mix_osc(nco_crcf_create(LIQUID_NCO)),
filt_stage1(calcFiltLen(in_sample_rate, stopband)),
filt_stage2(calcFiltLen(in_sample_rate, stopband)),
filt_stage3(calcFiltLen(in_sample_rate, stopband)),
filt_stage4(calcFiltLen(in_sample_rate, stopband)) {
	float f0_hat = (float)freq / (float)in_sample_rate;
	
	nco_crcf_set_phase(mix_osc, 0.0f);
	nco_crcf_set_frequency(mix_osc, 2.0f * M_PI * f0_hat);
}
GaussTuner::~GaussTuner(void) {
	nco_crcf_destroy(mix_osc);
	filt_stage1.~ComplexAverager();
	filt_stage2.~ComplexAverager();
	filt_stage3.~ComplexAverager();
	filt_stage4.~ComplexAverager();
}
bool GaussTuner::push(float in_sample) {
	bool ret = false;
	std::complex<float> mixed;
	
	nco_crcf_mix_down(mix_osc, in_sample, &mixed);
	nco_crcf_step(mix_osc);
	
	conv_sample = filt_stage4.push(filt_stage3.push(filt_stage2.push((filt_stage1.push(mixed)))));
	
	if (n % decim_factor == 0) {
		ret = true;
	}
	
	n++;
	
	return ret;
}
void GaussTuner::setFreq(unsigned int freq) {
	float f0_hat = (float)freq / (float)in_sample_rate;
	
	nco_crcf_set_frequency(mix_osc, 2.0f * M_PI * f0_hat);
}
unsigned int GaussTuner::getFiltRiseTime(void) {
	float stopband_hat = (float)stopband / (float)in_sample_rate;
	
	return (unsigned int)(std::sqrt(16.0f * std::log((float)FILT_RISE_RATIO) * std::log(10.0f) * ((float)STOPBAND_ATTEN / 20.0f)) / (M_PI * (float)stopband_hat) / (float)decim_factor);
}
std::complex<float> GaussTuner::getSample(void) {
	return conv_sample;
}
unsigned int GaussTuner::calcFiltLen(unsigned int sample_rate, unsigned int stopband) {
	float stopband_hat = (float)stopband / (float)sample_rate;
	
	return (unsigned int)std::sqrt(1.0f + 24.0f * std::log(10.0f) * ((float)STOPBAND_ATTEN / 20.0f) / ((float)NUM_FILT_STAGES * M_PI * M_PI * stopband_hat * stopband_hat));
}

