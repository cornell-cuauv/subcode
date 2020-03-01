//
//  comms.cpp
//  hydromathd
//
//  Created by Vlad on 2/5/19.
//  Copyright © 2019 Vlad. All rights reserved.
//

#include "comms.hpp"

#include <cstdio>
#include <cstring>
#include <cmath>

const unsigned int Tuner::TRANS_WIDTH = 500;
const unsigned int Tuner::STOPBAND_ATTEN = 60;

const unsigned int FSKSynchronizer::BUFF_LEN = 65536;
const float FSKSynchronizer::THRESH_CALC_LEN = 200;
const float FSKSynchronizer::THRESH_FACTOR = 3.0;

void printPkt(unsigned char *pkt, unsigned int size) {
	std::printf("\nReceived comms packet: ");
	for (unsigned int byte_num = 0; byte_num < size; byte_num++) {
		std::printf("0x%X ", pkt[byte_num]);
	}
	std::printf("\n\n");
}

StdDev::StdDev(unsigned int len):
len(len),
std_dev(0.0f),
buff(windowf_create(len)) {
}
StdDev::~StdDev(void) {
	windowf_destroy(buff);
}
float StdDev::push(float in_sample) {
	float oldest_sample;

	windowf_index(buff, 0, &oldest_sample);
	windowf_push(buff, in_sample);
	std_dev = std::sqrt((std_dev * std_dev * ((float)len - 1.0f) + in_sample * in_sample - oldest_sample * oldest_sample) / ((float)len - 1.0f));

	return std_dev;
}

Tuner::Tuner(unsigned int in_sample_rate, unsigned int decim_factor, unsigned int freq, unsigned int bandwidth):
n(0),
in_sample_rate(in_sample_rate),
decim_factor(decim_factor),
conv_sample(0.0f),
mix_osc(nco_crcf_create(LIQUID_NCO)) {
	float f0_hat = (float)freq / (float)in_sample_rate;
	float f_cutoff_hat = ((float)bandwidth / 2.0f) / (float)in_sample_rate;
	float trans_width_hat = (float)TRANS_WIDTH / (float)in_sample_rate;
	unsigned int filt_len = estimate_req_filter_len(trans_width_hat, STOPBAND_ATTEN);
	float *coeffs = new float[filt_len];
	std::complex<float> filt_unscaled_resp;

	nco_crcf_set_phase(mix_osc, 0.0f);
	nco_crcf_set_frequency(mix_osc, 2.0f * M_PI * f0_hat);

	liquid_firdes_kaiser(filt_len, f_cutoff_hat, STOPBAND_ATTEN, 0.0f, coeffs);
	filt = firfilt_crcf_create(coeffs, filt_len);
	firfilt_crcf_freqresponse(filt, 0.0f, &filt_unscaled_resp);
	firfilt_crcf_set_scale(filt, 1.0f / std::abs(filt_unscaled_resp));

	delete [] coeffs;
}
Tuner::~Tuner(void) {
	nco_crcf_destroy(mix_osc);
	firfilt_crcf_destroy(filt);
}
bool Tuner::push(float in_sample) {
	bool ret = false;
	std::complex<float> mixed;

	nco_crcf_mix_down(mix_osc, in_sample, &mixed);
	nco_crcf_step(mix_osc);

	firfilt_crcf_push(filt, mixed);

	if (n % decim_factor == 0) {
		firfilt_crcf_execute(filt, &conv_sample);
		ret = true;
	}

	n++;

	return ret;
}
void Tuner::setFreq(unsigned int freq) {
	float f0_hat = (float)freq / (float)in_sample_rate;

	nco_crcf_set_frequency(mix_osc, 2.0f * M_PI * f0_hat);
}
std::complex<float> Tuner::getSample(void) {
	return conv_sample;
}

FSKSynchronizer::FSKSynchronizer(unsigned int samples_per_symbol, const int code[], const int orth_code[], unsigned int code_len):
samples_per_symbol(samples_per_symbol),
code_len(code_len),
triggered(false),
locked_on(false),
in_buff(windowf_create(BUFF_LEN)),
sig_out_buff(windowf_create(BUFF_LEN)),
orth_out_buff(windowf_create(BUFF_LEN)),
dyn_thresh_buff(windowf_create(BUFF_LEN)),
thresh_calc(THRESH_CALC_LEN) {
	float *corr_sig_coeffs = new float[code_len * samples_per_symbol];
	float *corr_orth_coeffs = new float[code_len * samples_per_symbol];

	for (unsigned int coeff_no = 0; coeff_no < code_len * samples_per_symbol; coeff_no++) {
		corr_sig_coeffs[coeff_no] = (float)code[code_len - 1 - coeff_no / samples_per_symbol];
		corr_orth_coeffs[coeff_no] = (float)orth_code[code_len - 1 - coeff_no / samples_per_symbol];
	}
	corr_sig = firfilt_rrrf_create(corr_sig_coeffs, code_len * samples_per_symbol);
	corr_orth = firfilt_rrrf_create(corr_orth_coeffs, code_len * samples_per_symbol);

	delete [] corr_sig_coeffs;
	delete [] corr_orth_coeffs;
}
FSKSynchronizer::~FSKSynchronizer(void) {
	windowf_destroy(in_buff);
	windowf_destroy(sig_out_buff);
	windowf_destroy(orth_out_buff);
	windowf_destroy(dyn_thresh_buff);
	firfilt_rrrf_destroy(corr_sig);
	firfilt_rrrf_destroy(corr_orth);
	thresh_calc.~StdDev();
}
bool FSKSynchronizer::push(std::complex<float> symbol0_sample, std::complex<float> symbol1_sample) {
	bool ret = false;
	float sig_out, orth_out;

	float in = std::abs(symbol0_sample) - std::abs(symbol1_sample);
	windowf_push(in_buff, in);

	firfilt_rrrf_push(corr_sig, in);
	firfilt_rrrf_push(corr_orth, in);

	firfilt_rrrf_execute(corr_sig, &sig_out);
	firfilt_rrrf_execute(corr_orth, &orth_out);

	windowf_push(sig_out_buff, sig_out);
	windowf_push(orth_out_buff, orth_out);

	float dyn_thresh = THRESH_FACTOR * thresh_calc.push(orth_out);
	windowf_push(dyn_thresh_buff, dyn_thresh);

	if (triggered) {
		samples_since_triggered++;

		if (!locked_on) {
			if (samples_since_triggered >= code_len * samples_per_symbol) {
				locked_on = true;
			} else if (sig_out > sig_peak) {
				sig_peak = sig_out;
				ret = true;
			}
		}
	}
	else if (sig_out > dyn_thresh) {
		sig_peak = sig_out;
		triggered = true;
		samples_since_triggered = 0;
		ret = true;
	}

	return ret;
}
bool FSKSynchronizer::getLockedOn(void) {
	return locked_on;
}
windowf FSKSynchronizer::dumpInBuff(void) {
	return in_buff;
}
windowf FSKSynchronizer::dumpSigOutBuff(void) {
	return sig_out_buff;
}
windowf FSKSynchronizer::dumpOrthOutBuff(void) {
	return orth_out_buff;
}
windowf FSKSynchronizer::dumpDynThreshBuff(void) {
	return dyn_thresh_buff;
}
void FSKSynchronizer::reset(void) {
	triggered = false;
	locked_on = false;
}

FSKDecider::FSKDecider(unsigned int samples_per_symbol, unsigned int num_symbols):
samples_per_symbol(samples_per_symbol),
num_symbols(num_symbols),
num_accum_samples(0),
energies(new float[num_symbols]),
highest_energy_symbol(0) {
	std::memset(energies, 0.0f, num_symbols * sizeof(float));
}
FSKDecider::~FSKDecider(void) {
	delete [] energies;
}
bool FSKDecider::push(std::complex<float> *ch0_samples, std::complex<float> *ch1_samples, std::complex<float> *ch2_samples, std::complex<float> *ch3_samples) {
	bool ret = false;

	for (unsigned int symbol_index = 0; symbol_index < num_symbols; symbol_index++) {
		energies[symbol_index] += std::abs(ch0_samples[symbol_index]) + std::abs(ch1_samples[symbol_index]) + std::abs(ch2_samples[symbol_index]) + std::abs(ch3_samples[symbol_index]);
	}

	num_accum_samples++;

	if (num_accum_samples >= samples_per_symbol) {
		float highest_energy = 0;

		for (unsigned int symbol_index = 0; symbol_index < num_symbols; symbol_index++) {
			if (energies[symbol_index] > highest_energy) {
				highest_energy = energies[symbol_index];
				highest_energy_symbol = symbol_index;
			}
		}

		num_accum_samples = 0;
		std::memset(energies, 0.0f, num_symbols * sizeof(float));
		ret = true;
	}

	return ret;
}
unsigned int FSKDecider::getSymbol(void) {
	return highest_energy_symbol;
}
void FSKDecider::reset(void) {
	num_accum_samples = 0;
	std::memset(energies, 0.0f, num_symbols * sizeof(float));
}

SymbolPacker::SymbolPacker(unsigned int pkt_size, unsigned int bits_per_symbol):
pkt_size(pkt_size),
bits_per_symbol(bits_per_symbol),
num_collected_symbols(0),
symbol_buff(new unsigned char[pkt_size * sizeof(unsigned char) / bits_per_symbol]),
pkt(new unsigned char[pkt_size]) {
}
SymbolPacker::~SymbolPacker(void) {
	delete [] symbol_buff;
	delete [] pkt;
}
bool SymbolPacker::push(unsigned int symbol) {
	bool ret = false;

	symbol_buff[num_collected_symbols] = symbol;
	num_collected_symbols++;

	if (num_collected_symbols >= pkt_size * 8 / bits_per_symbol) {
		unsigned int num_symbols_written;
		liquid_repack_bytes(symbol_buff, bits_per_symbol, (unsigned int)pkt_size * 8 / bits_per_symbol, pkt, 8, (unsigned int)pkt_size, &num_symbols_written);

		num_collected_symbols = 0;
		ret = true;
	}

	return ret;
}
unsigned char* SymbolPacker::getPkt(void) {
	return pkt;
}
void SymbolPacker::reset(void) {
	num_collected_symbols = 0;
}

