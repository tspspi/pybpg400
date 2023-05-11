from labdevices.pressuregauge import PressureGaugeUnit
from bpg400.bpg400 import BGP400_RS232

import sys
from time import sleep
from time import time

import matplotlib.pyplot as plt
import numpy as np

if len(sys.argv) < 3:
	print("Missing port filename and filename to store data in")
	print("\n")
	print(f"Usage: {sys.argv[0]} PORTNAME OUTFILE")
	sys.exit(1)

datats = []
data = []

with BGP400_RS232(sys.argv[1]) as pg:
	pg.set_unit(PressureGaugeUnit.MBAR)
	
	while pg.get_pressure() is None:
		print(".", end = "")
	print("\nReady\n\n")

	try:
		while True:
			pres = pg.get_pressure()
			ts = time()
			
			datats.append(ts)
			data.append(pres)
			print(f"{ts}: {pres} mbar")
			sleep(1)
	except KeyboardInterrupt:
		pass

datats = np.asarray(datats)
data = np.asarray(data)

np.savez(sys.argv[2], ts = datats, pressure = data)
print(f"Saved {len(datats)} samples to {sys.argv[2]}")

fig, ax = plt.subplots()
ax.set_xlabel("Timestamp [s]")
ax.set_ylabel("Pressure [mbar]")
ax.plot(datats, data)
ax.grid()
plt.show()
