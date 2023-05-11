from bpg400.bpg400 import BGP400_RS232
from labdevices.pressuregauge import PressureGaugeUnit
from time import sleep

import textwrap
import sys
import json

def printUsage():
    print(textwrap.dedent("""
        Usage: {} [OPTIONS] command

        Controls or queries the BPG400 pressure gauge via a RS232C
        serial interface.

        Options:

        \t--port PORTNAME
        \t\tSpecifies the serial port device to use
        \t--json
        \t\tSets output format to JSON for further processing
        \t--debug
        \t\tRun in debug mode (dump RX and TX packets)

        Supported commands:

        \tquery
        \t\tQuery the current pressure in the set unit
        \tsetmbar
        \t\tSet display unit to millibar
        \tsettorr
        \t\tSet display unit to torr
        \tsetpa
        \t\tSet display unit to pascal
        \tdegas
        \t\tEnable degas mode
        \tnodegas
        \t\tStop degas mode
        \tsleep N
        \t\tSleep N seconds before performing next command
    """.format(sys.argv[0])))

def main():
    port = "/dev/ttyU0"
    writeJson = False
    debugMode = False

    if len(sys.argv) < 2:
        printUsage()
        sys.exit(0)

    i = 1

    cmds = []

    while i < len(sys.argv):
        if sys.argv[i].strip() == "--port":
            if i == (len(sys.argv) - 1):
                print("Missing port filename after --port argument")
                print("\n")
                printUsage()
                sys.exit(1)
            port = sys.argv[i+1].strip()
            i = i + 2
            continue
        elif sys.argv[i].strip() == "--json":
            writeJson = True
            i = i + 1
            continue
        elif sys.argv[i].strip() == "--debug":
            debugMode = True
            i = i + 1
            continue
        elif sys.argv[i].strip() == "query":
            cmds.append({ 'cmd' : 'query'})
            i = i + 1
        elif sys.argv[i].strip() == "setmbar":
            cmds.append({ 'cmd' : 'setunit', 'unit' : PressureGaugeUnit.MBAR })
            i = i + 1
        elif sys.argv[i].strip() == "settorr":
            cmds.append({ 'cmd' : 'setunit', 'unit' : PressureGaugeUnit.TORR })
            i = i + 1
        elif sys.argv[i].strip() == "setpa":
            cmds.append({ 'cmd' : 'setunit', 'unit' : PressureGaugeUnit.PASCAL })
            i = i + 1
        elif sys.argv[i].strip() == "degas":
            cmds.append({ 'cmd' : 'degas', 'enable' : True })
            i = i + 1
        elif sys.argv[i].strip() == "nodegas":
            cmds.append({ 'cmd' : 'degas', 'enable' : False })
            i = i + 1
        elif sys.argv[i].strip() == "sleep":
            if i == (len(sys.argv) - 1):
                print("Missing duration after --sleep argument")
            try:
                duration = int(sys.argv[i+1])
            except ValueError:
                print(f"Argument {sys.argv[i+1]} is not a valid sleep duration")
                print("\n")
                printUsage()
                sys.exit(1)
            if duration <= 0:
                print(f"Argument {sys.argv[i+1]} is not a valid sleep duration")
                print("\n")
                printUsage()
                sys.exit(1)
            cmds.append({ 'cmd' : 'sleep', 'duration' : duration })
            i = i + 2
        else:
            print(f"Unknown command or argument {sys.argv[i]}")
            print("\n")
            printUsage()
            sys.exit(1)

    with BGP400_RS232(port, debugMode) as pg:
        for cmd in cmds:
            if cmd['cmd'] == 'query':
                while pg.get_pressure() is None:
                    # Wait for a valid measurement
                    sleep(0.1)
                pres = pg.get_pressure()
                unit = pg.get_unit()
                if unit == PressureGaugeUnit.MBAR:
                    unitstring = "mbar"
                elif unit == PressureGaugeUnit.TORR:
                    unitstring = "torr"
                elif unit == PressureGaugeUnit.PASCAL:
                    unitstring = "pa"
                else:
                    unitstring = ""

                if not writeJson:
                    print(f"{pres} {unitstring}")
                else:
                    print(f"{ 'pressure' : {pres}, 'unit' : '{unitstring}' }")
            elif cmd['cmd'] == 'setunit':
                if not writeJson:
                    print("Setting display unit")
                pg.set_unit(cmd['unit'])
            elif cmd['cmd'] == "degas":
                if not writeJson:
                    print(f"Degassing: {cmd['enable']}")
                pg.degas(cmd['enable'])
            elif cmd['cmd'] == "sleep":
                sleep(cmd['duration'])


if __name__ == "__main__":
    main()
