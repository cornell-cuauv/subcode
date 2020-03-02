//
//  hydromathd.cpp
//  hydromathd
//
//  Created by Vlad on 9/10/18.
//  Copyright © 2018 Vlad. All rights reserved.
//

#include "libshm/c/vars.h"
//#include "shm_mac.hpp"
#include "constants.hpp"
#include "pinger.hpp"
#include "comms.hpp"
#include "udp_receiver.hpp"
#include "udp_sender.hpp"

#include <cstdio>
#include <cstdint>
#include <cmath>

#include <complex>
#include "liquid.h"

int main(void) {
	std::printf("Hydromathd starting...\n\n");

	std::uint64_t n = 0;
	struct hydrophones_status shm_status;
	struct hydrophones_pinger_results shm_pinger_results;
	struct hydrophones_pinger_settings shm_pinger_settings;
	struct gx4 shm_imu;
	UDPSampleReceiver sample_recvr(LOCAL_SAMPLE_PORT, SAMPLE_PKT_LEN);
	UDPBoardConfigSender board_config_sender(BOARD_ADDR, BOARD_CONFIG_PORT);

	std::uint64_t pinger_interv_start_n = 0, pinger_interv_trigger_n = 0;
	int shm_freq_num = 0;
	float pinger_max_sample = 0.0f, pinger_max_sense_ratio = 0.0f;
	windowf pinger0_raw_buff = windowf_create(BUFF_LEN);
	windowf pinger1_raw_buff = windowf_create(BUFF_LEN);
	windowf pinger2_raw_buff = windowf_create(BUFF_LEN);
	windowf pinger3_raw_buff = windowf_create(BUFF_LEN);
	windowf pinger_gain_buff = windowf_create(BUFF_LEN);
	windowcf pinger0_baseb_buff = windowcf_create(BUFF_LEN);
	windowcf pinger1_baseb_buff = windowcf_create(BUFF_LEN);
	windowcf pinger2_baseb_buff = windowcf_create(BUFF_LEN);
	windowcf pinger3_baseb_buff = windowcf_create(BUFF_LEN);
	windowf pinger_ampl_buff = windowf_create(BUFF_LEN);
	windowf pinger_sense_ratio_buff = windowf_create(BUFF_LEN);
	windowf pinger_trigger_n_buff = windowf_create(BUFF_LEN);
	GaussTuner *pinger0_beacon_tuners[Pinger::NUM_FREQS];
	GaussTuner *pinger1_beacon_tuners[Pinger::NUM_FREQS];
	GaussTuner *pinger2_beacon_tuners[Pinger::NUM_FREQS];
	GaussTuner *pinger3_beacon_tuners[Pinger::NUM_FREQS];
	Averager pinger_ampl_averager(Pinger::AMPL_AVG_LEN);
	UDPPlotSender pinger_raw_plot_sender(PLOT_DISPLAY_ADDR, Pinger::RAW_PLOT_PORT, 5, Pinger::RAW_PLOT_LEN);
	UDPPlotSender pinger_sense_plot_sender(PLOT_DISPLAY_ADDR, Pinger::SENSE_PLOT_PORT, 2, Pinger::INTERV_LEN);
	UDPPlotSender pinger_trigger_n_sender(PLOT_DISPLAY_ADDR, Pinger::SENSE_PLOT_PORT, 1, 1);
	UDPPlotSender pinger_trigger_plot_sender(PLOT_DISPLAY_ADDR, Pinger::TRIGGER_PLOT_PORT, 4, Pinger::TRIGGER_PLOT_LEN * 2);

	for (unsigned int freq_num = 0; freq_num < Pinger::NUM_FREQS; freq_num++) {
		pinger0_beacon_tuners[freq_num] = new GaussTuner(ADC_SAMPLE_RATE, Pinger::DECIM_FACTOR, Pinger::FREQS[freq_num], Pinger::STOPBAND);
		pinger1_beacon_tuners[freq_num] = new GaussTuner(ADC_SAMPLE_RATE, Pinger::DECIM_FACTOR, Pinger::FREQS[freq_num], Pinger::STOPBAND);
		pinger2_beacon_tuners[freq_num] = new GaussTuner(ADC_SAMPLE_RATE, Pinger::DECIM_FACTOR, Pinger::FREQS[freq_num], Pinger::STOPBAND);
		pinger3_beacon_tuners[freq_num] = new GaussTuner(ADC_SAMPLE_RATE, Pinger::DECIM_FACTOR, Pinger::FREQS[freq_num], Pinger::STOPBAND);
	}

	std::uint64_t last_comms_raw_plot_n = 0;
	windowf comms0_raw_buff = windowf_create(BUFF_LEN);
	windowf comms1_raw_buff = windowf_create(BUFF_LEN);
	windowf comms2_raw_buff = windowf_create(BUFF_LEN);
	windowf comms3_raw_buff = windowf_create(BUFF_LEN);
	windowf comms_gain_buff = windowf_create(BUFF_LEN);
	Tuner *comms0_symbol_tuners[Comms::NUM_SYMBOLS];
	Tuner *comms1_symbol_tuners[Comms::NUM_SYMBOLS];
	Tuner *comms2_symbol_tuners[Comms::NUM_SYMBOLS];
	Tuner *comms3_symbol_tuners[Comms::NUM_SYMBOLS];
	FSKSynchronizer comms_synch(Comms::SAMPLES_PER_SYMBOL, Comms::CODE, Comms::ORTH_CODE, Comms::CODE_LEN);
	FSKDecider comms_decid(Comms::SAMPLES_PER_SYMBOL, Comms::NUM_SYMBOLS);
	SymbolPacker comms_pack(Comms::PKT_SIZE, Comms::BITS_PER_SYMBOL);
	UDPPlotSender comms_raw_plot_sender(PLOT_DISPLAY_ADDR, Comms::RAW_PLOT_PORT, 5, Comms::RAW_PLOT_LEN);
	UDPPlotSender comms_corr_plot_sender(PLOT_DISPLAY_ADDR, Comms::CORR_PLOT_PORT, 4, Comms::CORR_PLOT_LEN);

	for (unsigned int symbol_num = 0; symbol_num < Comms::NUM_SYMBOLS; symbol_num++) {
		comms0_symbol_tuners[symbol_num] = new Tuner(ADC_SAMPLE_RATE, Comms::DECIM_FACTOR, Comms::SYMBOLS[symbol_num], Comms::SYMBOL_WIDTH);
		comms1_symbol_tuners[symbol_num] = new Tuner(ADC_SAMPLE_RATE, Comms::DECIM_FACTOR, Comms::SYMBOLS[symbol_num], Comms::SYMBOL_WIDTH);
		comms2_symbol_tuners[symbol_num] = new Tuner(ADC_SAMPLE_RATE, Comms::DECIM_FACTOR, Comms::SYMBOLS[symbol_num], Comms::SYMBOL_WIDTH);
		comms3_symbol_tuners[symbol_num] = new Tuner(ADC_SAMPLE_RATE, Comms::DECIM_FACTOR, Comms::SYMBOLS[symbol_num], Comms::SYMBOL_WIDTH);
	}

	shm_init();

	board_config_sender.setCommsAutogain(true);
	board_config_sender.send();

	sample_recvr.recv();
	shm_status.packet_number = sample_recvr.getPktNum();
	shm_pinger_results.heading = 0.0f;
	shm_pinger_results.elevation = 0.0f;

	std::printf("Listening for packets...\n\n");

    // a tad unfortunate
    shm_getg(hydrophones_pinger_settings, shm_pinger_settings);

	while (1) {
		bool new_sample = false;

		sample_recvr.recv();

		std::uint32_t curr_pkt_num = sample_recvr.getPktNum();
		if (curr_pkt_num != (std::uint32_t)shm_status.packet_number + 1) {
			std::printf("\nSample packet discontinuity detected\n\n");
		} else if (curr_pkt_num == 0) {
			std::printf("\nHydrophones board has resetted\n\n");
		}
		shm_status.packet_number = curr_pkt_num;

		if (n == pinger_interv_start_n) {
			shm_getg(hydrophones_pinger_settings, shm_pinger_settings);

			if (shm_pinger_settings.user_gain_control) {
				board_config_sender.setPingerGainLvl(shm_pinger_settings.user_gain_lvl);
			} else {
				board_config_sender.setPingerGainLvl(GainControl::calcGain(pinger_max_sample, sample_recvr.getPingerGainLvl()));
			}
			board_config_sender.send();

			shm_freq_num = -1;
			for (unsigned int freq_num = 0; freq_num < Pinger::NUM_FREQS; freq_num++) {
				if (Pinger::FREQS[freq_num] == (unsigned int)shm_pinger_settings.frequency) {
					shm_freq_num = freq_num;
					break;
				}
			}
			if (shm_freq_num != -1) {
				std::printf("Tracking %d kHz\n", Pinger::FREQS[shm_freq_num]);
			} else {
				shm_freq_num = 0;
				std::printf("SHM pinger frequency invalid. Tracking %d Hz\n", Pinger::FREQS[shm_freq_num]);
			}
		}

		for (unsigned int sample_num = 0; sample_num < SAMPLE_PKT_LEN; sample_num++) {
			float pinger0_raw_sample = sample_recvr.getSample(0, sample_num);
			float pinger1_raw_sample = sample_recvr.getSample(1, sample_num);
			float pinger2_raw_sample = sample_recvr.getSample(2, sample_num);
			float pinger3_raw_sample = sample_recvr.getSample(3, sample_num);

			windowf_push(pinger0_raw_buff, pinger0_raw_sample);
			windowf_push(pinger1_raw_buff, pinger1_raw_sample);
			windowf_push(pinger2_raw_buff, pinger2_raw_sample);
			windowf_push(pinger3_raw_buff, pinger3_raw_sample);

			unsigned int pinger_gain = GainControl::GAINZ[sample_recvr.getPingerGainLvl()];
			windowf_push(pinger_gain_buff, (float)pinger_gain);

			float pinger0_norm_sample = pinger0_raw_sample / pinger_gain;
			float pinger1_norm_sample = pinger1_raw_sample / pinger_gain;
			float pinger2_norm_sample = pinger2_raw_sample / pinger_gain;
			float pinger3_norm_sample = pinger3_raw_sample / pinger_gain;

			for (unsigned int freq_num = 0; freq_num < Pinger::NUM_FREQS; freq_num++) {
				new_sample |= pinger0_beacon_tuners[freq_num]->push(pinger0_norm_sample);
				new_sample |= pinger1_beacon_tuners[freq_num]->push(pinger1_norm_sample);
				new_sample |= pinger2_beacon_tuners[freq_num]->push(pinger2_norm_sample);
				new_sample |= pinger3_beacon_tuners[freq_num]->push(pinger3_norm_sample);
			}
			if (new_sample) {
				new_sample = false;

				std::complex<float> pinger0_baseb_sample = pinger0_beacon_tuners[shm_freq_num]->getSample();
				std::complex<float> pinger1_baseb_sample = pinger1_beacon_tuners[shm_freq_num]->getSample();
				std::complex<float> pinger2_baseb_sample = pinger2_beacon_tuners[shm_freq_num]->getSample();
				std::complex<float> pinger3_baseb_sample = pinger3_beacon_tuners[shm_freq_num]->getSample();

				windowcf_push(pinger0_baseb_buff, pinger0_baseb_sample);
				windowcf_push(pinger1_baseb_buff, pinger1_baseb_sample);
				windowcf_push(pinger2_baseb_buff, pinger2_baseb_sample);
				windowcf_push(pinger3_baseb_buff, pinger3_baseb_sample);

				float ampl = std::abs(pinger0_baseb_sample) + std::abs(pinger1_baseb_sample) + std::abs(pinger2_baseb_sample) + std::abs(pinger3_baseb_sample);
				windowf_push(pinger_ampl_buff, ampl);

				float avg_ampl = pinger_ampl_averager.push(ampl);

				float old_ampl;
				windowf_index(pinger_ampl_buff, BUFF_LEN - 1 - pinger0_beacon_tuners[shm_freq_num]->getFiltRiseTime(), &old_ampl);

				float sense_ratio;
				if (old_ampl + avg_ampl != 0.0f) {
					sense_ratio = (ampl + avg_ampl) / (old_ampl + avg_ampl);
				} else {
					sense_ratio = 0.0f;
				}
				windowf_push(pinger_sense_ratio_buff, sense_ratio);

				if (sense_ratio > pinger_max_sense_ratio) {
					bool sense_ok = true;
					for (unsigned int freq_num = 0; freq_num < Pinger::NUM_FREQS; freq_num++) {
						std::complex<float> pinger0_other_freq_sample = pinger0_beacon_tuners[freq_num]->getSample();
						std::complex<float> pinger1_other_freq_sample = pinger1_beacon_tuners[freq_num]->getSample();
						std::complex<float> pinger2_other_freq_sample = pinger2_beacon_tuners[freq_num]->getSample();
						std::complex<float> pinger3_other_freq_sample = pinger3_beacon_tuners[freq_num]->getSample();

						float other_freq_ampl = std::abs(pinger0_other_freq_sample) + std::abs(pinger1_other_freq_sample) + std::abs(pinger2_other_freq_sample) + std::abs(pinger3_other_freq_sample);
						if (other_freq_ampl > ampl) {
							sense_ok = false;
							break;
						}
					}

					if (sense_ok) {
						std::printf("%4.6f %4.6f %lu\n", ampl, sense_ratio, n - pinger_interv_start_n);

						float path_diff1 = remainder(std::arg(pinger1_baseb_sample) - std::arg(pinger0_baseb_sample), 2 * M_PI) * (float)SOUND_SPEED / (2.0f * M_PI * shm_pinger_settings.frequency);
						float path_diff2 = remainder(std::arg(pinger2_baseb_sample) - std::arg(pinger0_baseb_sample), 2 * M_PI) * (float)SOUND_SPEED / (2.0f * M_PI * shm_pinger_settings.frequency);

						shm_getg(gx4, shm_imu);

						shm_pinger_results.heading = calcHdg(path_diff1, path_diff2, shm_imu.heading);
						shm_pinger_results.elevation = calcElev(path_diff1, path_diff2, NIPPLE_DISTANCE);

						pinger_trigger_plot_sender.takeComplex(0, pinger0_baseb_buff, BUFF_LEN);
						pinger_trigger_plot_sender.takeComplex(1, pinger1_baseb_buff, BUFF_LEN);
						pinger_trigger_plot_sender.takeComplex(2, pinger2_baseb_buff, BUFF_LEN);
						pinger_trigger_plot_sender.takeComplex(3, pinger3_baseb_buff, BUFF_LEN);

						pinger_max_sense_ratio = sense_ratio;

						pinger_interv_trigger_n = (n - pinger_interv_start_n) / Pinger::DECIM_FACTOR;
					}
				}
			}


			float comms0_raw_sample = sample_recvr.getSample(4, sample_num);
			float comms1_raw_sample = sample_recvr.getSample(5, sample_num);
			float comms2_raw_sample = sample_recvr.getSample(6, sample_num);
			float comms3_raw_sample = sample_recvr.getSample(7, sample_num);

			windowf_push(comms0_raw_buff, comms0_raw_sample);
			windowf_push(comms1_raw_buff, comms1_raw_sample);
			windowf_push(comms2_raw_buff, comms2_raw_sample);
			windowf_push(comms3_raw_buff, comms3_raw_sample);

			unsigned int comms_gain = GainControl::GAINZ[sample_recvr.getCommsGainLvl()];
			windowf_push(comms_gain_buff, (float)comms_gain);

			float comms0_norm_sample = comms0_raw_sample / comms_gain;
			float comms1_norm_sample = comms1_raw_sample / comms_gain;
			float comms2_norm_sample = comms2_raw_sample / comms_gain;
			float comms3_norm_sample = comms3_raw_sample / comms_gain;

			for (unsigned int symbol_num = 0; symbol_num < Comms::NUM_SYMBOLS; symbol_num++) {
				new_sample |= comms0_symbol_tuners[symbol_num]->push(comms0_norm_sample);
				new_sample |= comms1_symbol_tuners[symbol_num]->push(comms1_norm_sample);
				new_sample |= comms2_symbol_tuners[symbol_num]->push(comms2_norm_sample);
				new_sample |= comms3_symbol_tuners[symbol_num]->push(comms3_norm_sample);
			}
			if (new_sample) {
				new_sample = false;

				std::complex<float> comms0_symbol_samples[Comms::NUM_SYMBOLS];
				std::complex<float> comms1_symbol_samples[Comms::NUM_SYMBOLS];
				std::complex<float> comms2_symbol_samples[Comms::NUM_SYMBOLS];
				std::complex<float> comms3_symbol_samples[Comms::NUM_SYMBOLS];

				for (unsigned int symbol_num = 0; symbol_num < Comms::NUM_SYMBOLS; symbol_num++) {
					comms0_symbol_samples[symbol_num] = comms0_symbol_tuners[symbol_num]->getSample();
					comms1_symbol_samples[symbol_num] = comms1_symbol_tuners[symbol_num]->getSample();
					comms2_symbol_samples[symbol_num] = comms2_symbol_tuners[symbol_num]->getSample();
					comms3_symbol_samples[symbol_num] = comms3_symbol_tuners[symbol_num]->getSample();
				}

				if (comms_decid.push(comms0_symbol_samples, comms1_symbol_samples, comms2_symbol_samples, comms3_symbol_samples)) {
					if (comms_pack.push(comms_decid.getSymbol()) && comms_synch.getLockedOn()) {
						printPkt(comms_pack.getPkt(), Comms::PKT_SIZE);

						comms_corr_plot_sender.send();

						comms_synch.reset();
					}
				}

				if (comms_synch.push(comms0_symbol_samples[0], comms0_symbol_samples[1])) {
					comms_corr_plot_sender.takeReal(0, comms_synch.dumpInBuff(), BUFF_LEN);
					comms_corr_plot_sender.takeReal(1, comms_synch.dumpSigOutBuff(), BUFF_LEN);
					comms_corr_plot_sender.takeReal(2, comms_synch.dumpOrthOutBuff(), BUFF_LEN);
					comms_corr_plot_sender.takeReal(3, comms_synch.dumpDynThreshBuff(), BUFF_LEN);

					comms_decid.reset();
					comms_pack.reset();
				}
			}

			n++;
		}

		float pkt_pinger_max_sample = sample_recvr.getPingerMaxSample();
		if (pkt_pinger_max_sample > pinger_max_sample) {
			pinger_raw_plot_sender.takeReal(0, pinger0_raw_buff, BUFF_LEN);
			pinger_raw_plot_sender.takeReal(1, pinger1_raw_buff, BUFF_LEN);
			pinger_raw_plot_sender.takeReal(2, pinger2_raw_buff, BUFF_LEN);
			pinger_raw_plot_sender.takeReal(3, pinger3_raw_buff, BUFF_LEN);
			pinger_raw_plot_sender.takeReal(4, pinger_gain_buff, BUFF_LEN);

			pinger_max_sample = pkt_pinger_max_sample;
		}

		if (n - pinger_interv_start_n >= Pinger::INTERV_LEN * Pinger::DECIM_FACTOR) {
			shm_setg(hydrophones_pinger_results, shm_pinger_results);
			//shm_setg(shm_pinger_results);

			windowf_push(pinger_trigger_n_buff, (float)pinger_interv_trigger_n);

			pinger_sense_plot_sender.takeReal(0, pinger_ampl_buff, BUFF_LEN);
			pinger_sense_plot_sender.takeReal(1, pinger_sense_ratio_buff, BUFF_LEN);
			pinger_trigger_n_sender.takeReal(0, pinger_trigger_n_buff, BUFF_LEN);

			pinger_raw_plot_sender.send();
			pinger_trigger_plot_sender.send();
			pinger_sense_plot_sender.send();
			pinger_trigger_n_sender.send();

			pinger_max_sample = 0;
			pinger_max_sense_ratio = 0;
			
			pinger_interv_start_n = n;
			pinger_interv_trigger_n = 0;
		}

		if (n - last_comms_raw_plot_n >= Comms::RAW_PLOT_LEN) {
			comms_raw_plot_sender.takeReal(0, comms0_raw_buff, BUFF_LEN);
			comms_raw_plot_sender.takeReal(1, comms1_raw_buff, BUFF_LEN);
			comms_raw_plot_sender.takeReal(2, comms2_raw_buff, BUFF_LEN);
			comms_raw_plot_sender.takeReal(3, comms3_raw_buff, BUFF_LEN);
			comms_raw_plot_sender.takeReal(4, comms_gain_buff, BUFF_LEN);

			comms_raw_plot_sender.send();

			last_comms_raw_plot_n = n;
		}

		shm_setg(hydrophones_status, shm_status);
	}

	//toodles!!!!!
	return 0;
}

