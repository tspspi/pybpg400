# Examples for ```pybpg400``` library

## A simple pressure logger and plotter (```logpressure.py```)

The ```logpressure.py``` script contains a simple script that opens
the ```BPG400``` pressure gauge via a specified serial port, measures pressure
till it gets interrupted and then dumps all measured timestamps and
data into the specified file as well as displays a plot using ```matplotlib```
