//
//  main.cpp
//  pingerd
//
//  Created by Vlad on 9/10/18.
//  Copyright © 2018 Vlad. All rights reserved.
//

#include "libshm/c/vars.h"
//#include "shm_mac.hpp"
#include "constants.hpp"
#include "pinger.hpp"
#include "../common/udp_receiver.hpp"
#include "../common/udp_sender.hpp"

#include <cstdio>
#include <cstdint>
#include <memory>
#include <vector>
#include <iterator>
#include <algorithm>
#include <cstring>

#include <complex>
#include "../common/liquid.h"

int main(void) {
	std::printf("Pingerd starting...\n\n");

	hydrophones_pinger_status shm_status;
	hydrophones_pinger_results shm_results;
	hydrophones_pinger_settings shm_settings;
	gx4 shm_imu;
	UDPSampleReceiver sample_recvr(LOCAL_SAMPLE_PORT, SAMPLE_PKT_LEN);
	UDPBoardConfigSender board_config_sender(BOARD_ADDR, BOARD_CONFIG_PORT);

	std::uint64_t n0 = 0, n1 = 0;
	std::uint64_t interv_start_n1 = 0, interv_max_ampl_n1 = 0;
	std::uint16_t interv_max_raw = 0;
	float interv_max_ampl = 0;
	unsigned int shm_freq_num = 0;
	windowf ch0_raw_buff = windowf_create(BUFF_LEN);
	windowf ch1_raw_buff = windowf_create(BUFF_LEN);
	windowf ch2_raw_buff = windowf_create(BUFF_LEN);
	windowf ch3_raw_buff = windowf_create(BUFF_LEN);
	windowf gain_buff = windowf_create(BUFF_LEN);
	windowcf ch0_baseb_buff = windowcf_create(BUFF_LEN);
	windowcf ch1_baseb_buff = windowcf_create(BUFF_LEN);
	windowcf ch2_baseb_buff = windowcf_create(BUFF_LEN);
	windowcf ch3_baseb_buff = windowcf_create(BUFF_LEN);
	windowf ampl_buff = windowf_create(BUFF_LEN);
	windowf sense_ratio_buff = windowf_create(BUFF_LEN);
	windowf imu_hdg_buff = windowf_create(BUFF_LEN);
	windowf imu_pitch_buff = windowf_create(BUFF_LEN);
	windowf trigger_n1_buff = windowf_create(BUFF_LEN);
	std::vector<std::shared_ptr<GaussTuner>> ch0_tuners;
	std::vector<std::shared_ptr<GaussTuner>> ch1_tuners;
	std::vector<std::shared_ptr<GaussTuner>> ch2_tuners;
	std::vector<std::shared_ptr<GaussTuner>> ch3_tuners;
	Averager ampl_averager(AMPL_AVG_LEN);
	UDPPlotSender raw_plot_sender(PLOT_DISPLAY_ADDR, RAW_PLOT_PORT, 5, RAW_PLOT_LEN);
	UDPPlotSender sense_plot_sender(PLOT_DISPLAY_ADDR, SENSE_PLOT_PORT, 2, INTERV_LEN);
	UDPPlotSender trigger_n1_sender(PLOT_DISPLAY_ADDR, SENSE_PLOT_PORT, 1, 1);
	UDPPlotSender trigger_plot_sender(PLOT_DISPLAY_ADDR, TRIGGER_PLOT_PORT, 4, TRIGGER_PLOT_LEN * 2);

	for (unsigned int freq_num = 0; freq_num < static_cast<unsigned int>(FREQS.size()); freq_num++) {
		ch0_tuners.push_back(std::make_shared<GaussTuner>(ADC_SAMPLE_RATE, FREQS[freq_num], STOPBAND));
		ch1_tuners.push_back(std::make_shared<GaussTuner>(ADC_SAMPLE_RATE, FREQS[freq_num], STOPBAND));
		ch2_tuners.push_back(std::make_shared<GaussTuner>(ADC_SAMPLE_RATE, FREQS[freq_num], STOPBAND));
		ch3_tuners.push_back(std::make_shared<GaussTuner>(ADC_SAMPLE_RATE, FREQS[freq_num], STOPBAND));
	}

	shm_init();
	shm_getg(hydrophones_pinger_settings, shm_settings);
	shm_getg(gx4, shm_imu);

	sample_recvr.recv();
	shm_status.packet_number = sample_recvr.getPktNum();
	shm_setg(hydrophones_pinger_status, shm_status);

	shm_results.heading = 0;
	shm_results.elevation = 0;
	shm_setg(hydrophones_pinger_results, shm_results);

	board_config_sender.send();

	std::printf("Listening for packets...\n\n");

	while (true) {
		sample_recvr.recv();

		std::uint32_t curr_pkt_num = sample_recvr.getPktNum();
		std::uint32_t expected_pkt_num = static_cast<std::uint32_t>(shm_status.packet_number) + 1;
		if (curr_pkt_num == 0) {
			std::printf("\nHydrophones board has resetted\n\n");
		} else if (curr_pkt_num != expected_pkt_num) {
		std::printf("\nSample packet discontinuity detected. Got %d when expecting %d\n\n", curr_pkt_num, expected_pkt_num);
		}
		shm_status.packet_number = curr_pkt_num;
		shm_setg(hydrophones_pinger_status, shm_status);

		for (unsigned int sample_num = 0; sample_num < SAMPLE_PKT_LEN; sample_num++) {
			std::int16_t ch0_raw = sample_recvr.getSample(0, sample_num);
			std::int16_t ch1_raw = sample_recvr.getSample(1, sample_num);
			std::int16_t ch2_raw = sample_recvr.getSample(2, sample_num);
			std::int16_t ch3_raw = sample_recvr.getSample(3, sample_num);

			windowf_push(ch0_raw_buff, ch0_raw);
			windowf_push(ch1_raw_buff, ch1_raw);
			windowf_push(ch2_raw_buff, ch2_raw);
			windowf_push(ch3_raw_buff, ch3_raw);

			unsigned int gain = GainControl::GAINZ[sample_recvr.getGainLvl()];
			windowf_push(gain_buff, gain);

			float ch0_norm = static_cast<float>(ch0_raw) / gain;
			float ch1_norm = static_cast<float>(ch1_raw) / gain;
			float ch2_norm = static_cast<float>(ch2_raw) / gain;
			float ch3_norm = static_cast<float>(ch3_raw) / gain;

			ch0_tuners[shm_freq_num]->push(ch0_norm);
			ch1_tuners[shm_freq_num]->push(ch1_norm);
			ch2_tuners[shm_freq_num]->push(ch2_norm);
			ch3_tuners[shm_freq_num]->push(ch3_norm);

			if (n0 % DECIM_FACTOR == 0) {
				if (n1 == interv_start_n1) {
					shm_getg(hydrophones_pinger_settings, shm_settings);

					if (shm_settings.user_gain_control) {
						board_config_sender.setGainLvl(shm_settings.user_gain_lvl);
					} else {
						board_config_sender.setGainLvl(GainControl::calcGain(interv_max_raw, sample_recvr.getGainLvl()));
					}
					board_config_sender.send();

					std::vector<unsigned int>::const_iterator shm_freq = find(FREQS.begin(), FREQS.end(), shm_settings.frequency);
					if (shm_freq == FREQS.end()) {
						shm_freq = FREQS.begin();
						std::printf("SHM frequency invalid. ");
					}
					std::printf("\nTracking %d kHz\n", *shm_freq);
					shm_freq_num = static_cast<unsigned int>(std::distance(FREQS.begin(), shm_freq));
				}

				std::complex<float> ch0_baseb = ch0_tuners[shm_freq_num]->getSample();
				std::complex<float> ch1_baseb = ch1_tuners[shm_freq_num]->getSample();
				std::complex<float> ch2_baseb = ch2_tuners[shm_freq_num]->getSample();
				std::complex<float> ch3_baseb = ch3_tuners[shm_freq_num]->getSample();

				windowcf_push(ch0_baseb_buff, ch0_baseb);
				windowcf_push(ch1_baseb_buff, ch1_baseb);
				windowcf_push(ch2_baseb_buff, ch2_baseb);
				windowcf_push(ch3_baseb_buff, ch3_baseb);

				float ampl = std::abs(ch0_baseb) + std::abs(ch1_baseb) + std::abs(ch2_baseb) + std::abs(ch3_baseb);
				windowf_push(ampl_buff, ampl);

				if (ampl > interv_max_ampl) {
					interv_max_ampl_n1 = n1;

					interv_max_ampl = ampl;
				}

				float avg_ampl = ampl_averager.push(ampl);

				float old_ampl;
				windowf_index(ampl_buff, BUFF_LEN - 1 - ch0_tuners[shm_freq_num]->getFiltRiseTime() / DECIM_FACTOR, &old_ampl);

				float sense_ratio;
				if (old_ampl + avg_ampl != 0) {
					sense_ratio = static_cast<float>(ampl + avg_ampl) / (old_ampl + avg_ampl);
				} else {
					sense_ratio = 0;
				}
				windowf_push(sense_ratio_buff, sense_ratio);

				windowf_push(imu_hdg_buff, shm_imu.heading);
				windowf_push(imu_pitch_buff, shm_imu.pitch);

				if (n1 + 1 - interv_start_n1 == INTERV_LEN) {
					std::uint64_t max_sense_ratio_n1 = interv_max_ampl_n1 - SEARCH_INTERV_LEN;
					float max_sense_ratio = 0;

					for (std::uint64_t sense_ratio_n1 = interv_max_ampl_n1 - SEARCH_INTERV_LEN;
						 sense_ratio_n1 <= interv_max_ampl_n1 + SEARCH_INTERV_LEN && sense_ratio_n1 <= n1;
						 sense_ratio_n1++) {
						float sense_ratio;

						windowf_index(sense_ratio_buff, static_cast<unsigned int>(BUFF_LEN - 1 - (n1 - sense_ratio_n1)), &sense_ratio);

						if (sense_ratio > max_sense_ratio) {
							max_sense_ratio_n1 = sense_ratio_n1;

							max_sense_ratio = sense_ratio;
						}
					}

					std::printf("%4.2f\n", max_sense_ratio);

					windowf_push(trigger_n1_buff, max_sense_ratio_n1 - interv_start_n1);

					std::complex<float> ch0_baseb;
					std::complex<float> ch1_baseb;
					std::complex<float> ch2_baseb;
					std::complex<float> ch3_baseb;

					windowcf_index(ch0_baseb_buff, static_cast<unsigned int>(BUFF_LEN - 1 - (n1 - max_sense_ratio_n1)), &ch0_baseb);
					windowcf_index(ch1_baseb_buff, static_cast<unsigned int>(BUFF_LEN - 1 - (n1 - max_sense_ratio_n1)), &ch1_baseb);
					windowcf_index(ch2_baseb_buff, static_cast<unsigned int>(BUFF_LEN - 1 - (n1 - max_sense_ratio_n1)), &ch2_baseb);
					windowcf_index(ch3_baseb_buff, static_cast<unsigned int>(BUFF_LEN - 1 - (n1 - max_sense_ratio_n1)), &ch3_baseb);

					float path_diff1 = static_cast<float>(remainder(std::arg(ch1_baseb) - std::arg(ch0_baseb), 2 * M_PI) * SOUND_SPEED) / (2 * M_PI * shm_settings.frequency);
					float path_diff2 = static_cast<float>(remainder(std::arg(ch2_baseb) - std::arg(ch0_baseb), 2 * M_PI) * SOUND_SPEED) / (2 * M_PI * shm_settings.frequency);

					float imu_hdg;
					float imu_pitch;

					windowf_index(imu_hdg_buff, static_cast<unsigned int>(BUFF_LEN - 1 - (n1 - max_sense_ratio_n1)), &imu_hdg);
					windowf_index(imu_pitch_buff, static_cast<unsigned int>(BUFF_LEN - 1 - (n1 - max_sense_ratio_n1)), &imu_pitch);

					shm_results.heading = calcHdg(path_diff1, path_diff2, imu_hdg);
					shm_results.elevation = calcElev(path_diff1, path_diff2, NIPPLE_DISTANCE);
					shm_setg(hydrophones_pinger_results, shm_results);

					std::printf("Heading: %4.2f\n", shm_results.heading);
					std::printf("Elevation: %4.2f\n", shm_results.elevation);

					trigger_plot_sender.takeComplex(0, ch0_baseb_buff, static_cast<unsigned int>(BUFF_LEN - (n1 - max_sense_ratio_n1)));
					trigger_plot_sender.takeComplex(1, ch1_baseb_buff, static_cast<unsigned int>(BUFF_LEN - (n1 - max_sense_ratio_n1)));
					trigger_plot_sender.takeComplex(2, ch2_baseb_buff, static_cast<unsigned int>(BUFF_LEN - (n1 - max_sense_ratio_n1)));
					trigger_plot_sender.takeComplex(3, ch3_baseb_buff, static_cast<unsigned int>(BUFF_LEN - (n1 - max_sense_ratio_n1)));
					sense_plot_sender.takeReal(0, ampl_buff, BUFF_LEN);
					sense_plot_sender.takeReal(1, sense_ratio_buff, BUFF_LEN);
					trigger_n1_sender.takeReal(0, trigger_n1_buff, BUFF_LEN);

					raw_plot_sender.send();
					sense_plot_sender.send();
					trigger_plot_sender.send();
					trigger_n1_sender.send();

					interv_start_n1 = n1 + 1;
					interv_max_ampl_n1 = n1 + 1;

					interv_max_raw = 0;
					interv_max_ampl = 0;
				}

				n1++;
			}

			n0++;
		}

		float pkt_max_raw = sample_recvr.getMaxSample();
		if (pkt_max_raw > interv_max_raw) {
			raw_plot_sender.takeReal(0, ch0_raw_buff, BUFF_LEN);
			raw_plot_sender.takeReal(1, ch1_raw_buff, BUFF_LEN);
			raw_plot_sender.takeReal(2, ch2_raw_buff, BUFF_LEN);
			raw_plot_sender.takeReal(3, ch3_raw_buff, BUFF_LEN);
			raw_plot_sender.takeReal(4, gain_buff, BUFF_LEN);

			interv_max_raw = pkt_max_raw;
		}
	}

	//toodles!!!!!
	return 0;
}
