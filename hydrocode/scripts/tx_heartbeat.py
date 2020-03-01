#!/usr/bin/env python3

HB_INTERVAL = 7000
MSG = 0xAAAA

while 1:
	if shm.blabla.tx_heartbeat.get() == 1:
		if curr_time - last_hb_time >= HB_INTERVAL:
			last_hb_time = curr_time;

			shm.blabla.Word0WriteVar.set(MSG)

			shm.blabla.NewDataWriteVar.set(1)
			while(!shm.blabla.TransmissionDoneReadVar.get())
			shm.blabla.NewDataWriteVar.set(0)

			data = bytes()



