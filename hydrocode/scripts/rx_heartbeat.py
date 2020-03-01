#!/usr/bin/env python3

import select, time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ADDR, PORT))

sock.setblocking(0)

while 1:
	data = bytes()

	ready = select.select([sock], [], [], HB_TIMEOUT)
	if ready[0]:
		(udp_data_pkt, addr) = sock.recvfrom(UDP_PKT_SIZE * 4)
		data += udp_data_pkt

		if data == [0xAA, 0xAA]:
			shm.blabla.rx_heartbeat.set(1)
			last_hb_time = time.time()


	if time.time() - last_hb_time > HB_TIMEOUT:
		shm.blabla.rx_heartbeat.set(0)