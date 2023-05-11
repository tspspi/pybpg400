# ```pybpg400```: Unofficial Python library to control and access the INFICON BPG400 pressure gauge (via RS232C)

This is an unofficial Python library (and a mini CLI utility)
to control and access the INFICON BPG400 pressure gauge via
it's RS232C serial port.

## Installation

This library (and the CLI utility) is provided via PyPi:

```
pip install pybpg400-tspspi
```

## Usage

More elaborate examples can be found in the ```examples``` folder.

The device can be simply opened via context management routines (in
addition to imperative ```connect()``` and ```disconnect()``` routines):

```
from bpg400.bpg400 import RPG400_RS232
from labdevices.pressuregauge import PressureGaugeUnit

with BPG400_RS232("/dev/ttyUSB0") as pg:
	# Perform your operations
```

The library starts an background thread that continuously
parses the datastream received by the BPG400 pressure gauge.
To query the latest pressure reading one can simply use
the ```get_pressure``` method. This method also allows one to
supply the unit - it defaults to ```mbar```:

```
print(pg.get_pressure())
```

or

```
print(pg.get_pressure(PressureGaugeUnit.TORR))
```

One can simply change the display unit using the ```set_unit```
method:

```
pg.set_unit(PressureGaugeUnit.MBAR)
pg.set_unit(PressureGaugeUnit.TORR)
pg.set_unit(PressureGaugeUnit.PASCAL)
```

## The CLI utility

The package also comes with a simple command line utility
called ```bpg400```.

One can for example simply query the current pressure
using a single shell command:

```
bpg400 --port /dev/ttyU0``` query
```

```
Usage: bpg400 [OPTIONS] command

Controls or queries the BPG400 pressure gauge via a RS232C
serial interface.

Options:

	--port PORTNAME
		Specifies the serial port device to use
	--json
		Sets output format to JSON for further processing
	--debug
		Run in debug mode (dump RX and TX packets)

Supported commands:

	query
		Query the current pressure in the set unit
	setmbar
		Set display unit to millibar
	settorr
		Set display unit to torr
	setpa
		Set display unit to pascal
	degas
		Enable degas mode
	nodegas
		Stop degas mode
	sleep N
		Sleep N seconds before performing next command
```
