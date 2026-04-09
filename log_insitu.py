# Created by Yuna Katsuyama and Tim Suhling
# University of Bremen
# yuna@uni-bremen.de
# timsuh@uni-bremen.de
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serial logging for Insitu measurement device
Reads Serial ports according to .cfg file and save the data to a Buffer to be read by write_KML.py
Based on main.py
"""

import os
import sys
import serial
import threading
import collections
import time
import datetime
import configparser

from pynmeagps import NMEAReader
from contextlib import contextmanager


def getconfig(filename='insitu.cfg'):
    """Load configuration file to dictionary

    Parameters
    ----------
    filename : :class:`str <python:str>`
        Name of the config file. Defaults to 'insitu.cfg'

    Returns
    -------
    :class:`dict <python:dict>`
        Dictionary containing the config values

    """

    cfg = configparser.ConfigParser()
    cfgfile = os.path.abspath('./' + filename)
    cfg.read(cfgfile)

    print(cfgfile)

    return cfg


@contextmanager
def opencom(port, baudrate, timeout, **portkwargs):
    """Context manager for serial port

    Enables the use of `with`-statement with serial ports. Makes sure the
    ports are closed when the `with`-statement is exited.

    If the port is already open, it is closed and reopened again.

    Parameters
    ----------
    port : :class:`str <python:str>`
        The definition of the serial port.
    baudrate : :class:`int <python:int>`
        baudrate of the serial port
    timeout : :class:`int <python:int>`
        Time in seconds the port waits for a response until an error is raised
    **portkwargs : :class:`dict <python:dict>`
        Other keywords accepted by `serial.Serial()` command.

    Yields
    ------
    comport : :class:`serial.Serial`
        Opened serial port

    """

    comport = serial.Serial(port=port, baudrate=baudrate, timeout=timeout,
                            **portkwargs)

    try:
        comport.open()
    except serial.SerialException as serex:
        if str(serex) == 'Port is already open.':
            comport.close()
            comport.open()
        else:
            raise

    try:
        yield comport
    finally:
        comport.close()


def readgps(cfg, queue, event):
    """Get GPS coordinates from serial gps device using pynmeagps.
    Keeps last valid GPS coordinates if fix is lost.

    Parameters
    ----------
    cfg : dict
        Configuration dictionary containing 'GPS' section
    queue : collections.deque
        Queue to store GPS coordinates
    event : threading.Event
        Event to stop the thread
    """
    last_valid_gps = ['+000.00000', '+0000.00000', '00000', '00:00:00.000']

    port = cfg['GPS']['port']
    baud = cfg['GPS'].getint('baudrate')
    timeout = cfg['GPS'].getint('timeout')
    bytesize = cfg['GPS'].getint('bytesize')
    parity = cfg['GPS']['parity']
    stopbits = cfg['GPS'].getint('stopbits')

    while not event.is_set():
        try:
            with opencom(
                    port=port,
                    baudrate=baud,
                    timeout=timeout,
                    bytesize=bytesize,
                    parity=parity,
                    stopbits=stopbits
            ) as gpscom:

                nmr = NMEAReader(gpscom)

                while not event.is_set():
                    try:
                        raw_data, parsed_msg = nmr.read()

                        # Only process GGA messages
                        if parsed_msg and parsed_msg.msgID == 'GGA':
                            try:
                                coordarr = [
                                    '{0:+09.5f}'.format(round(parsed_msg.lat, 5)),
                                    '{0:+010.5f}'.format(round(parsed_msg.lon, 5)),
                                    '{0:05d}'.format(round(parsed_msg.alt)),
                                    parsed_msg.time.strftime('%H:%M:%S.%f')
                                ]
                                queue.append(coordarr)
                                print(f'readgps {coordarr}')
                            except TypeError as type_error:
                                print(parsed_msg)
                                print(f'GPS has currently no data, using latest vaild Coordinates until reconnect!')
                                continue

                    except serial.SerialException as e:
                        print(f"Serial read error, reopening GPS port: {e}")
                        break

                    except (ValueError, AttributeError):
                        continue

                    except Exception as e:
                        print(f"Unexpected GPS error: {e}")
                        continue

        except serial.SerialException as e:
            print(f"Could not open GPS port {port}: {e}, retrying in 5s...")
            time.sleep(5)

        time.sleep(1)


def read_device(cfg, queue, event, date):
    device_type = cfg['Default']['device']
    measnum = cfg['LogParams'].getint('startnum')

    gpsdata = ['+000.00000', '+0000.00000', '00000', '00:00:00.000']

    # -------------------------
    # DEVICE SETUP
    # -------------------------

    timelag = cfg[device_type].getint('timelag', fallback=3)
    port_path = cfg[device_type]['port']
    baudrate = cfg[device_type].getint('baudrate')
    serial_timeout = cfg[device_type].getint('timeout')
    bytesize = cfg[device_type].getint('bytesize')
    parity = cfg[device_type]['parity']
    stopbits = cfg[device_type].getint('stopbits')
    separator = cfg[device_type]['separator']
    external_gps = eval(cfg[device_type]['external_gps'])

    gps_buffer = collections.deque(maxlen=timelag)

    while not event.is_set():
        try:
            with opencom(
                    port=port_path,
                    baudrate=baudrate,
                    timeout=serial_timeout,
                    bytesize=bytesize,
                    parity=parity,
                    stopbits=stopbits
            ) as devicecom:

                devicecom.reset_input_buffer()

                while not event.is_set():
                    try:
                        raw_data = devicecom.readline()
                        data = raw_data.decode('utf-8', errors='ignore').strip()

                        if separator is None:
                            data = data.split()  # split on whitespace
                        else:
                            data = data.split(separator)

                        # ---------------------
                        # GPS handling
                        # ---------------------
                        if queue:
                            gpsdata = queue[-1]
                        # print(f'gpsdata {gpsdata}')
                        gps_buffer.appendleft(gpsdata)

                        if len(gps_buffer) < timelag:
                            continue

                        delayed_gps = gps_buffer.pop()
                        # print(f'gps_buffer {gps_buffer}')
                        # print(f'delayed_gps {delayed_gps}')
                        latest_gps = gpsdata

                        measnum += 1

                        # ---------------------
                        # FORMAT OUTPUT
                        # ---------------------
                        # outstr, flightstr = formatter(
                        #     cfg, data, delayed_gps, latest_gps, measnum
                        # )

                        if external_gps:
                            outstr_list = [
                                '  '.join(data),
                                '  '.join(delayed_gps[:3]),
                                str(measnum), '\n'
                            ]
                        elif not external_gps:
                            dummy_gps = ['00:00:00.000', '+000.00000', '+0000.00000', '00000']
                            outstr_list = [
                                '  '.join(data),
                                *dummy_gps[1:3],
                                str(measnum),
                                '\n'
                            ]
                        else:
                            raise ValueError(f'external_gps is either "True" or "False", currently {external_gps}')

                        outstr = '  '.join(outstr_list)

                        time.sleep(1)
                        print(f'outstr {outstr}')
                        # ---------------------
                        # WRITE FILES
                        # ---------------------
                        timestamp = datetime.datetime.now().strftime('%y%m%dt%H%M%S')

                        logfile_path = (
                            f"{cfg['Paths']['maindir']}/Logfiles_{date}/"
                            f"{timestamp}_{device_type}.dat"
                        )

                        with open(logfile_path, 'a') as f:
                            f.write(outstr)

                        with open(f"{cfg['Paths']['maindir']}/Buffer/{timestamp}_{device_type}.dat", 'w') as f:
                            f.write(outstr)

                        # console
                        sys.stdout.write(outstr)
                        # sys.stdout.write(flightstr)
                        sys.stdout.flush()

                    except serial.SerialException as e:
                        print(f"Serial read error, reopening device port: {e}")
                        break

                    except (ValueError, AttributeError):
                        continue

                    except Exception as e:
                        print(f"Unexpected device error: {e}")
                        continue

        except serial.SerialException as e:
            print(f"Could not open device port {port_path}: {e}, retrying in 5s...")
            time.sleep(5)

        time.sleep(1)


def runlogging():
    """
    Start the logging of the Device.
    This has to be run in a folder containing the .cfg file.
    Function will generate folder structure for saving based on [PATHS] in the .cfg file.
    """

    coordqueue = collections.deque(maxlen=1)
    stopevent = threading.Event()

    cfg = getconfig()

    date = datetime.datetime.now().strftime('%y%m%d')
    try:
        os.mkdir(cfg['Paths']['maindir'])
    except FileExistsError:
        print('Folder exists already')

    try:
        os.mkdir(cfg['Paths']['maindir'] + '/Logfiles_{0}'.format(date))
    except FileExistsError:
        print('Folder exists already')

    os.makedirs(cfg['Paths']['maindir'] + '/Buffer', exist_ok=True)

    gpsthread = threading.Thread(target=readgps, name='GPSthread', args=[cfg, coordqueue, stopevent])
    devicethread = threading.Thread(target=read_device, args=[cfg, coordqueue, stopevent, date])

    gpsthread.start()
    devicethread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stopevent.set()
        gpsthread.join(5)
        devicethread.join(5)
        print('threads terminated (gps, device):')
        print(not gpsthread.is_alive(), not devicethread.is_alive())
    finally:
        stopevent.set()
        print('threads terminated (gps, device):')
        print(not gpsthread.is_alive(), not devicethread.is_alive())


if __name__ == '__main__':
    runlogging()
