# add yuna branch comment
# rewrite from log_losgatos.py

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
        Name of the config file. Defaults to 'losgatos.cfg'

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

    Parameters
    ----------
    cfg : dict
        Configuration dictionary containing 'GPS' section
    queue : collections.deque
        Queue to store GPS coordinates
    event : threading.Event
        Event to stop the thread
    """
    with opencom(cfg['GPS']['port'], cfg['GPS'].getint('baudrate'),
                 cfg['GPS'].getint('timeout'),
                 **{'bytesize': cfg['GPS'].getint('bytesize'),
                    'parity': cfg['GPS']['parity'],
                    'stopbits': cfg['GPS'].getint('stopbits')}
                 ) as gpscom:

        nmr = NMEAReader(gpscom)
        
        while not event.is_set():
            try:
                (raw_data, parsed_msg) = nmr.read()
                if parsed_msg:
                    # Only process GGA messages (GPS fix data)
                    if parsed_msg.msgID == 'GGA':
                        coordarr = [
                            '{0:+09.5f}'.format(round(parsed_msg.lat, 5)),
                            '{0:+010.5f}'.format(round(parsed_msg.lon, 5)),
                            '{0:05d}'.format(round(parsed_msg.alt)),
                            parsed_msg.time.strftime('%H:%M:%S.%f')
                        ]
                        queue.append(coordarr)
                        print(f'readgpd {coordarr}')
            except (serial.SerialException, ValueError, AttributeError):
                continue
            
                             
def read_device(cfg, queue, event, date):

    device_type = cfg['Default']['device']
    measnum = cfg['LogParams'].getint('startnum')

    gpsdata = ['+000.00000', '+0000.00000', '00000', '00:00:00.000']
    

    # -------------------------
    # DEVICE SETUP
    # -------------------------


    timelag = cfg[device_type].getint('timelag', fallback=3)
    port_path=cfg[device_type]['port']
    baudrate = cfg[device_type].getint('baudrate')
    serial_timeout= cfg[device_type].getint('timeout')
    bytesize=cfg[device_type].getint('bytesize')
    parity=cfg[device_type]['parity']
    stopbits=cfg[device_type].getint('stopbits')
    separator = cfg[device_type]['separator']
    
    gps_buffer = collections.deque(maxlen=timelag)

    with opencom(
        port=port_path,
        baudrate=baudrate,
        timeout=serial_timeout,
        bytesize = bytesize,
        parity = parity,
        stopbits = stopbits 
    ) as devicecom:
        
        devicecom.reset_input_buffer()

    # -------------------------
    # MAIN LOOP
    # -------------------------
        while not event.is_set():    
            data = devicecom.readline().decode('utf-8', errors='ignore').strip()
            
            if separator is None:
                data = data.split()        # split on whitespace
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
            
            outstr = '  '.join(['  '.join(data),
                                '  '.join(delayed_gps[:3]),
                                str(measnum), '\n'])
            
            flightstr = '  '.join([
            latest_gps[3], # time
            latest_gps[0], # lat
            latest_gps[1], # lon
            latest_gps[2], # alt
            str(measnum),
            '\n'
            ])
            print(f'outstr {outstr}')
            print(f'flightstr {flightstr}')
            # ---------------------
            # WRITE FILES
            # ---------------------
            timestamp = datetime.datetime.now().strftime('%y%m%dt%H%M%S')

            logfile_path = (
                f"{cfg['Paths']['maindir']}/Logfiles_{date}/"
                f"{timestamp}_{device_type}.dat"
            )

            flightlog_path = (
                f"{cfg['Paths']['maindir']}/Logfiles_{date}/"
                f"{timestamp}_{device_type}_FLIGHT.dat"
            )

            with open(logfile_path, 'a') as f:
                f.write(outstr)

            with open(flightlog_path, 'a') as f:
                f.write(flightstr)

            # buffer
            with open(f"{cfg['Paths']['maindir']}/Buffer/{measnum:05d}_{timestamp}_{device_type}.dat", 'w') as f:
                f.write(outstr)

            with open(f"{cfg['Paths']['maindir']}/Buffer_flighttrack/{measnum:05d}_{timestamp}_{device_type}.dat", 'w') as f:
                f.write(flightstr)

            # console
            sys.stdout.write(outstr)
            sys.stdout.write(flightstr)
            sys.stdout.flush()
            
            
        
def runlogging():
    """Start the logging of the LosGatos GGA

    This has to be run in a set up runtime folder with a Buffer and a Logfiles
    directory. This directory must also contain a :obj:`losgatos.cfg` file.

    """

    coordqueue = collections.deque(maxlen=1)
    stopevent = threading.Event()

    cfg = getconfig()
    # if cfg['Default']['device'] == 'aeris':
    #     from aeris_scripts.aeris_device import aeris_methane_ethene_serial
#    cfg['Paths']['maindir'] = (cfg['Paths']['maindir'] + '/'
#                               + datetime.datetime.now().strftime('%y%m%d_LosGatos'))

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
    os.makedirs(cfg['Paths']['maindir'] + '/Buffer_flighttrack', exist_ok=True)
    
    gpsthread = threading.Thread(target=readgps, name='GPSthread',
                                 args=[cfg, coordqueue, stopevent])
    devicethread = threading.Thread(
            target=read_device,
            args=[cfg, coordqueue, stopevent, date]
        )

    gpsthread.start()
    devicethread.start()

    try:
        while(True):
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