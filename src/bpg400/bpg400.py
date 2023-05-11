from labdevices.pressuregauge import PressureGauge
from labdevices.pressuregauge import PressureGaugeUnit

from labdevices.serialringbuffer import SerialRingBuffer

import atexit
import serial
import threading

from time import time

class BGP400_RS232(PressureGauge):
    def __init__(
        self,
        port,

        debug = False
    ):
        super().__init__(
            measurementRange = ( 5e-10, 1e3 ),
            hasDegas = True,
            deviceSupportedUnits = [ PressureGaugeUnit.MBAR, PressureGaugeUnit.TORR, PressureGaugeUnit.PASCAL ],
            debug = debug
        )

        self._measurement = None
        self._lock = threading.Lock()
        self._thrProcessing = None
        self._rbInput = SerialRingBuffer()
        self._tslastSyncQuery = None

        if isinstance(port, serial.Serial):
            self._port = port
            self._portName = None
            self.__initialRequests()
        else:
            self._portName = port
            self._port = None

        atexit.register(self.__close)

    def __initialRequests(self):
        if self._thrProcessing is None:
            self._thrProcessing = threading.Thread(target = self._readerThreadMain)
            self._thrProcessing.start()
        pass

    # Context management routines

    def __enter__(self):
        if self._usedConnect:
            raise ValueError("Cannot use context management (with) on connected object")
        if (self._port is None) and (self._portName is not None):
            self._port = serial.Serial(self._portName, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=15)
            self.__initialRequests()

        self._usesContext = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__close()
        self._usesContext = False

    def __close(self):
        atexit.unregister(self.__close)
        if (self._port is not None) and (self._portName is not None):
            self._port.close()
            self._port = None
        while self._thrProcessing is not None:
            pass

    # Connect and disconnect

    def _connect(self):
        if (self._port is None) and (self._portName is not None):
            self._port = serial.Serial(self._portName, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=15)
            self.__initialRequests()
        return True

    def _disconnect(self):
        if (self._port is not None):
            self._close()
        return True

    def _readerThreadMain(self):
        try:
            while True:
                c = self._port.read(1)

                self._rbInput.push(c)

                # Try to process message
                if self._rbInput.available() < 9:
                    continue

                while (self._rbInput.available() >= 9):
                    syncpattern = int.from_bytes(self._rbInput.peek(0), 'little')
                    pagenum = int.from_bytes(self._rbInput.peek(1), 'little')
                    sensorType = int.from_bytes(self._rbInput.peek(7), 'little')

                    if (syncpattern == 7) and (pagenum == 5) and (sensorType == 10):
                        break

                    self._rbInput.discard(1)

                if self._rbInput.available() < 9:
                    continue

                # We have a potential message ...
                sum = 0
                for i in range(1, 8):
                    sum = sum + int.from_bytes(self._rbInput.peek(i), 'little')
                sum = sum % 256

                chksum = int.from_bytes(self._rbInput.peek(8), 'little')
                if sum != chksum:
                    # Resync at next byte ...
                    self._rbInput.discard(1)
                    continue

                # Decode whole packet ...
                pkg = self._rbInput.read(9)

                if self._debug:
                    print(f"[BPG400-DEBUG] Rx: {pkg}")

                for ib, b in enumerate(pkg):
                    pkg[ib] = int.from_bytes(b, 'little')

                # Decode packet data ...
                decodeError = False
                measurementReliable = True

                emissionCurrent = None
                degassing = False
                mbar1000adjust = False
                pressureUnit = None

                poorPiraniMeasurement = False
                BAError = False
                PiraniError = False

                if (pkg[2] & 0x03) == 0x00:
                    emissionCurrent = 0
                elif (pkg[2] & 0x03) == 0x01:
                    emissionCurrent = 25e-6
                elif (pkg[2] & 0x03) == 0x02:
                    emissionCurrent = 5e-3
                elif (pkg[2] & 0x03) == 0x03:
                    emissionCurrent = None
                    degassing = True

                if (pkg[2] & 0x04) == 0x04:
                    mbar1000adjust = True

                if (pkg[2] & 0x30) == 0x00:
                    pressureUnit = PressureGaugeUnit.MBAR
                elif (pkg[2] & 0x30) == 0x10:
                    pressureUnit = PressureGaugeUnit.TORR
                elif (pkg[2] & 0x30) == 0x20:
                    pressureUnit = PressureGaugeUnit.PASCAL
                else:
                    decodeError = True

                if (pkg[3] & 0xF0) == 0x80:
                    BAError = True
                    measurementReliable = False
                elif (pkg[3] & 0xF0) == 0x90:
                    PiraniError = True
                    measurementReliable = False
                elif (pkg[3] & 0xF0) == 0x50:
                    poorPiraniMeasurement = True
                    measurementReliable = False

                softVersion = float(pkg[6]) / 20

                # Decode pressure value
                pressureValueRaw = pkg[5] + pkg[4] * 256
                pressureValue = None
                pressureMbar = None

                if pressureUnit == PressureGaugeUnit.MBAR:
                    pressureValue = 10.0**(pressureValueRaw / 4000.0 - 12.5)
                    pressureMbar = pressureValue
                elif pressureUnit == PressureGaugeUnit.TORR:
                    pressureValue = 10.0**(pressureValueRaw / 4000.0 - 12.625)
                    pressureMbar = pressureValue * 1.33322
                elif pressureUnit == PressureGaugeUnit.PASCAL:
                    pressureValue = 10.0**(pressureValueRaw / 4000.0 - 10.5)
                    pressureMbar = pressureValue * 0.01

                # Update state ...
                with self._lock:
                    self._measurement = {
                        'ts' : time(),
                        'decodeError' : decodeError,
                        'reliable' : measurementReliable,
                        'degassing' : degassing,

                        '1baradjust' : mbar1000adjust,
                        'emissionCurrent' : emissionCurrent,

                        'error_poorPiraniMeasurement' : poorPiraniMeasurement,
                        'error_BayardAlpertError' : BAError,
                        'error_Pirani' : PiraniError,

                        'pressureUnit' : pressureUnit,

                        'pressure_raw' : pressureValueRaw,
                        'pressure' : pressureValue,
                        'pressure_mbar' : pressureMbar,

                        'firmwareVersion' : softVersion
                    }
                    if self._debug:
                        print(f"[BPG400-DEBUG] {self._measurement}")


        except serial.serialutil.SerialException:
            pass
        except Exception as e:
            # print(e)
            pass

        self._thrProcessing = None

    # Exposed (overwritten API)

    def _degas(self, degasOn):
        cmd = None
        if degasOn:
            cmd = bytearray([ 3, 16, 93, 148, 1 ])
        else:
            cmd = bytearray([ 3, 16, 93, 105, 214 ])

        if self._port is not None:
            if self._debug:
                print(f"[BPG400-DEBUG] Tx: {cmd}")
            self._port.write(cmd)
        else:
            raise ValueError("Device not connected")

    def _get_versions(self):
        with self._lock:
            if self._measurement is None:
                return None

            return {
                'firmware' : self._measurement['firmwareVersion']
            }

    def _get_device_type(self):
        return {
            'device' : 'BPG400'
        }

    def _get_pressure(self):
        with self._lock:
            if self._measurement is None:
                return None

            return {
                'raw' : self._measurement['pressure_raw'],
                'value' : {
                    self._measurement['pressureUnit'] : self._measurement['pressure']
                },
                'mbar' : self._measurement['pressure_mbar']
            }

    def _get_unit(self):
        with self._lock:
            if self._measurement is None:
                return None
            return self._measurement['pressureUnit']

    def _set_unit(self, unit):
        cmd = None

        if unit == PressureGaugeUnit.MBAR:
            cmd = bytearray([ 3, 16, 62, 0, 78 ])
        elif unit == PressureGaugeUnit.TORR:
            cmd = bytearray([ 3, 16, 62, 1, 79 ])
        elif unit == PressureGaugeUnit.PASCAL:
            cmd = bytearray([ 3, 16, 62, 2, 80 ])
        else:
            raise ValueError(f"Unsupported unit {unit} for this device")

        if self._port is None:
            raise ValueError(f"Device not connected")

        if self._debug:
            print(f"[BPG400-DEBUG] Tx: {cmd}")
        self._port.write(cmd)

if __name__ == "__main__":
    from time import sleep

    with BGP400_RS232(
        "/dev/ttyUSB0",
        debug = False
    ) as pg:
        pg.set_unit(PressureGaugeUnit.TORR)
        sleep(1)
        print(pg.get_pressure())
        sleep(10)
        pg.set_unit(PressureGaugeUnit.MBAR)
        sleep(1)
        print(pg.get_pressure())
        sleep(10)
        pg.set_unit(PressureGaugeUnit.TORR)
        sleep(1)
        print(pg.get_pressure())
        sleep(10)
        pg.set_unit(PressureGaugeUnit.MBAR)
        sleep(1)
        print(pg.get_pressure())
        while True:
            sleep(1)
            print(pg.get_pressure())
        pass