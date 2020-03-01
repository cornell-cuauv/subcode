//
//  comms.hpp
//  hydromathd
//
//  Created by Vlad on 2/5/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#ifndef COMMS_HPP
#define COMMS_HPP

#include <cstdint>

#include <complex>
#include "liquid.h"

void printPkt(unsigned char *pkt, unsigned int size);

class StdDev {
public:
	StdDev(unsigned int len);
	~StdDev(void);
	float push(float in_sample);

private:
	unsigned int len;
	float std_dev;
	windowf buff;
};

class Tuner {
public:
	Tuner(unsigned int in_sample_rate, unsigned int decim_factor, unsigned int freq, unsigned int bandwidth);
	~Tuner(void);
	bool push(float in_sample);
	void setFreq(unsigned int freq);
	std::complex<float> getSample(void);

private:
	static const unsigned int TRANS_WIDTH;
	static const unsigned int STOPBAND_ATTEN;

	std::uint64_t n;
	unsigned int in_sample_rate;
	unsigned int decim_factor;
	std::complex<float> conv_sample;

	nco_crcf mix_osc;
	firfilt_crcf filt;
};

class FSKSynchronizer {
public:
	FSKSynchronizer(unsigned int samples_per_symbol, const int code[], const int orth_code[], unsigned int code_len);
	~FSKSynchronizer(void);
	bool push(std::complex<float> symbol0_sample, std::complex<float> symbol1_sample);
	bool getLockedOn(void);
	windowf dumpInBuff(void);
	windowf dumpSigOutBuff(void);
	windowf dumpOrthOutBuff(void);
	windowf dumpDynThreshBuff(void);
	void reset(void);

private:
	static const unsigned int BUFF_LEN;
	static const float THRESH_CALC_LEN;
	static const float THRESH_FACTOR;

	unsigned int samples_per_symbol;
	std::uint64_t samples_since_triggered;
	unsigned int code_len;
	bool triggered;
	float sig_peak;
	bool locked_on;

	windowf in_buff, sig_out_buff, orth_out_buff, dyn_thresh_buff;
	firfilt_rrrf corr_sig, corr_orth;
	StdDev thresh_calc;
};

class FSKDecider {
public:
	FSKDecider(unsigned int samples_per_symbol, unsigned int num_symbols);
	~FSKDecider(void);
	bool push(std::complex<float> *ch0_samples, std::complex<float> *ch1_samples, std::complex<float> *ch2_samples, std::complex<float> *ch3_samples);
	unsigned int getSymbol(void);
	void reset(void);

private:
	unsigned int samples_per_symbol;
	unsigned int num_symbols;
	unsigned int num_accum_samples;
	float *energies;
	unsigned int highest_energy_symbol;
};

class SymbolPacker {
public:
	SymbolPacker(unsigned int pkt_size, unsigned int bits_per_symbol);
	~SymbolPacker(void);
	bool push(unsigned int symbol);
	unsigned char* getPkt(void);
	void reset(void);

private:
	unsigned int pkt_size;
	unsigned int bits_per_symbol;
	unsigned int num_collected_symbols;
	unsigned char *symbol_buff;
	unsigned char *pkt;
};

#endif /* comms_hpp */

