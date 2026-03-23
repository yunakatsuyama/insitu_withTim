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
# from aeris_device import aeris_methane_ethene_serial
from aeris_scripts.aeris_device import aeris_methane_ethene_serial


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
            except (serial.SerialException, ValueError, AttributeError):
                continue
            
# def readaeris(cfg, queue, event, date):
    
#     gpsdata = ['{0:+09.5f}'.format(0.0),
#             '{0:+010.5f}'.format(0.0),
#             '{0:05d}'.format(0),
#             '00:00:00.000']
#     measnum = cfg['LogParams'].getint('startnum')        
#     timelag = cfg['AERIS'].getint('timelag', fallback=3)
#     # initialize aeris device
#     device = aeris_methane_ethene_serial(
#         port_path=cfg['AERIS']['port'],
#         tube_delay=timelag   #if GPS is internal, the delay is considered inside the class   
#     )
#     gps_delay_buffer = collections.deque(maxlen=timelag)
  
#     while not event.is_set():

#         logfile_path = (
#             cfg['Paths']['maindir']
#             + '/Logfiles_{0}/'.format(date)
#             + datetime.datetime.now().strftime(
#                 '%y%m%dt%H%M%S_GPS_AERIS_logfile.dat'
#             )
#         )
        
#         flightlog_path = (
#             cfg['Paths']['maindir']
#             + '/Logfiles_{0}/'.format(date)
#             + datetime.datetime.now().strftime(
#                 '%y%m%dt%H%M%S_FLIGHTTRACK_logfile.dat'
#             )
#         )

#         with open(logfile_path, 'w') as file, open(flightlog_path, 'w') as flightfile:

#             # file.write('# GPS_TIME WINDOWS_TIME AERIS_TIME CO2 XCO2 CH4 XCH4 H2O GPS_LAT GPS_LON GPS_ALT\n')

#             measnum += 1       
                     
#             while not event.is_set():
#                 # format obtained from .update is 
#                 # aeris data is dictionaly
#                 # self.csv_data_name_lst = ["date", "p", "T", "ch4", "c2h6", "h2o", "lat","lon"]    
#                 aerisdata = device.update()
            
#                 print(aerisdata)

#                 if not aerisdata:
#                     continue

#                 try:
#                     gpsdata = queue.pop()
#                     print(gpsdata)
#                 except IndexError:
#                     pass  # keep last gpsdata   
                
#                 # --------------------------------------------------
#                 # TIMELAG
#                 # --------------------------------------------------

#                 gps_delay_buffer.appendleft(gpsdata)

#                 if len(gps_delay_buffer) < timelag:
#                     continue

#                 delayed_gps = gps_delay_buffer.pop()
                
#                 # -----------------------------------------------------------------------------------
#                 # This is for logfiles containing external gps and aeris lon lat
#                 # If the gps data is from external mous, consider the timelag
#                 # ----------------------------------------------------------------------------------
#                 if cfg['AERIS']['GPSTyp'] == 'ext':
#                     outstrlog = '  '.join([(delayed_gps[3])[:10],  # gps time
#                                                     datetime.datetime.now().strftime('%H:%M:%S.%f')[:10],  # pc time
#                                                     f"{aerisdata['p']:.3f}",
#                                                     f"{aerisdata['T']:.3f}",
#                                                     f"{aerisdata['ch4']:.6f}",
#                                                     f"{aerisdata['c2h6']:.6f}",
#                                                     f"{aerisdata['h2o']:.6f}",  # concentrations
#                                                     ' '.join(delayed_gps[:3]),  # lat lon alt
#                                                     str(measnum),  # measurement number
#                                                     '\n'])
#                 elif cfg['AERIS']['GPSTyp'] == 'int':
#                     outstrlog = '  '.join([(aerisdata["date"].strftime('%H:%M:%S.%f')[:10]),  # aeris time
#                                                     datetime.datetime.now().strftime('%H:%M:%S.%f')[:10],  # pc time
#                                                     f"{aerisdata['p']:.3f}",
#                                                     f"{aerisdata['T']:.3f}",
#                                                     f"{aerisdata['ch4']:.6f}",
#                                                     f"{aerisdata['c2h6']:.6f}",
#                                                     f"{aerisdata['h2o']:.6f}",  # concentrations
#                                                     f"{aerisdata['lat']:.6f}",  # lat lon alt
#                                                     f"{aerisdata['lon']:.6f}",
#                                                     f"{aerisdata['alt']:.6f}",  # currently not implemented in aeris_device
#                                                     str(measnum),  # measurement number
#                                                     '\n'])
#                 else:
#                     print(f'cfg device gpstyp should be ext or int')
                     
#                 file.write(outstrlog)
#                 # --------------------------------------------------
#                 # LATEST GPS -> flight track
#                 # --------------------------------------------------

#                 latest_gps = gpsdata

#                 flightstr = '  '.join([
#                     latest_gps[3],
#                     latest_gps[0],
#                     latest_gps[1],
#                     latest_gps[2],
#                     str(measnum),
#                     '\n'
#                 ])

#                 flightfile.write(flightstr)
#                 flightfile.flush()
                
#                 # --------------------------------------------------------------
#                 # From here, buffer (currenyly the same format as the logfolder)
#                 # --------------------------------------------------------------
#                 # Concentrations
#                 outstrbuf = outstrlog
#                 with open(cfg['Paths']['maindir'] + '/Buffer/' + '{0:05d}'.format(measnum) +
#                                         datetime.datetime.now().strftime(
#                                         '_%y%m%dt%H%M%S_GPS_AERIS_buffile.dat'
#                                         ), 'w') as buffile:
#                     buffile.write(outstrbuf)
#                 sys.stdout.write(outstrbuf)
#                 sys.stdout.flush()
                
#                 # flight track
#                 flightstrbuf = flightstr
#                 with open(cfg['Paths']['maindir'] + '/Buffer_flighttrack/' + '{0:05d}'.format(measnum) +
#                                         datetime.datetime.now().strftime(
#                                         '_%y%m%dt%H%M%S_extGPS_FLIGHTTRACK.dat'
#                                         ), 'w') as buffile_flighttrack:
#                     buffile_flighttrack.write(flightstrbuf)
#                 sys.stdout.write(flightstrbuf)
#                 sys.stdout.flush()
#                 break
                
#             if event.is_set():
#                 break

# def readlosgatos(cfg, queue, event, date):
#     """Reads LosGatos Data from serial port and combines it with GPS data

#     Parameters
#     ----------
#     cfg : :class:`dict <python:dict>`
#         Configuration dictionary. Must contain the following sections and
#         fields:

#             - GGA: all configuration parameters for serial connection to GGA
#             - Paths: `maindir` path to main storage folder
#             - LogParams: `startnum` first measurement number, `loglen` number
#                 of entries per logfile

#     queue : :class:`collections.deque <python:collections.deque>`
#         queue from which the gps coordinates are read.
#     event : :class:`threading.event <python:threading.event>`
#         Event to stop the execution of this routine.

#     """

#     deviceoutput = {'UGGABerlin': 'CH4 CH4_se H2O H2O_se CO2 CO2_se GasP_torr' +
#                     'GasP_torr_se GasT_C GasT_C_se AmbT_C AmbT_se RD0_us' +
#                     'RD0_us_se RD1_us RD1_us_se Fit_Flag',
#                     'UGGAHella': 'CH4 CH4_se H2O H2O_se CO2 CO2_se CO CO_se' +
#                     'CH4d CH4d_se CO2d CO2d_se COd COd_se GasP_torr' +
#                     'GasP_torr_se GasT_C GasT_C_se AmbT_C AmbT_se RD0_us' +
#                     'RD0_us_se RD1_us RD1_us_se LTC0_v LTC0_v_se LTC1_v ' +
#                     'LTC1_v_se Fit_Flag MIU_VALVE MIU_DESC',
# 					'UGGAEOS': 'CH4 CH4_sd H2O H2O_sd CO2 CO2_sd CO CO_sd CH4d CH4d_sd CO2d CO2d_sd COd COd_sd GasP_torr ' + 
# 					'GasP_torr_sd GasT_C GasT_C_sd AmbT_C AmbT_C_sd RD0_us RD0_us_sd RD1_us RD1_us_sd ' + 
# 					'Temp_Status Temp_Status_sd Analyzer_Status_mA,Analyzer_Status_mA_sd,       Fit_Flag,      MIU_VALVE,       MIU_DESC, GPS Time Stamp (hr), Latitude (deg), Longitude (deg), Altitude (m), Geodial Separation (m), GPS Fit, Nr of Satellites, horizontal dillution, units altitude, units separation'}
#     # for when GPS cannot have any data soon after thread starts
#     # meands dummy GPS filled with 0.  
#     gpsdata = ['{0:+09.5f}'.format(0.0),
#                '{0:+010.5f}'.format(0.0),
#                '{0:05d}'.format(0),
#                '00:00:00.000']
#     measnum = cfg['LogParams'].getint('startnum')

#     # open loagatos port and the serial object is in ggacom
#     with opencom(cfg['GGA']['port'], cfg['GGA'].getint('baudrate'),
#                  cfg['GGA'].getint('timeout'),
#                  **{'bytesize': cfg['GGA'].getint('bytesize'),
#                   'parity': cfg['GGA']['parity'],
#                   'stopbits': cfg['GGA'].getinst('stopbits')}
#                  ) as ggacom:
#         ggacom.reset_input_buffer()

#         # until finish, read and wrtie data
#         while not event.is_set():
#             with open(cfg['Paths']['maindir'] + '/Logfiles_{0}/'.format(date) +
#                       datetime.datetime.now().strftime(
#                       '%y%m%dt%H%M%S_GPS_Picarro_logfile.dat'), 'w'
#                       ) as file:
#                 file.write('# GPS_TIME WINDOWS_TIME LOSGATOS_TIME' + deviceoutput[cfg['GGA']['devicename']] +' GPS_LAT GPS_LON GPS_ALT MEAS_NUM\n')
                
#                 #while True :  # I need to think about the condition here, it is for entire measurement 
#                 measnum += 1
#                 while True:
#                     if ggacom.in_waiting > 1:
#                         ggadata = ggacom.readline().decode()
#                         if len(ggadata) >= 298:
#                             try:
#                                 gpsdata = queue.pop()   # get the lastest GPS data (in queue, all data is stored (updated))
#                             except IndexError:
#                                 pass
#                             # this string is one line that has both GPS and losgatos, also time
#                             outstrlog = ', '.join([(gpsdata[3])[:10],  # gps time
#                                                 datetime.datetime.now().strftime('%H:%M:%S.%f')[:10],  # pc time
#                                                 ggadata[:-2],  # concentrations
#                                                 ', '.join(gpsdata[:3]),  # lat lon alt
#                                                 str(measnum),  # measurement number
#                                                 '\n'])
#                             file.write(outstrlog)
#                             outbuf = [col.strip() for col in outstrlog.split(sep=',')]
#                             # For write in Buffer file,  change the order of info    
#                             if cfg['GGA']['devicename'] in ['UGGAHella']:
#                                 outstrbuf = '  '.join(['  '.join(outbuf[0:3]), outbuf[7], outbuf[13],
#                                                         outbuf[3], outbuf[11], outbuf[5],
#                                                         outbuf[9], outbuf[15],
#                                                         '  '.join(gpsdata[:3]),
#                                                         str(measnum), '\n'])
#                             else:
#                                 outstrbuf = '  '.join(['  '.join(outbuf[0:3]), outbuf[7], '0.000000e+00',
#                                                         outbuf[3], '0.000000e+00', outbuf[5],
#                                                         '  '.join(gpsdata[:3]),
#                                                         str(measnum), '\n'])
#                             with open(cfg['Paths']['maindir'] + '/Buffer/' + '{0:05d}'.format(measnum) +
#                                         datetime.datetime.now().strftime(
#                                         '_%y%m%dt%H%M%S_GPS_LosGatos_buffile.dat'
#                                         ), 'w') as buffile:
#                                 buffile.write(outstrbuf)
#                             sys.stdout.write(outstrbuf)
#                             sys.stdout.flush()
#                             break
#                     if event.is_set():
#                         break

#                 if event.is_set():
#                     break
def format_losgatos(cfg, ggadata, delayed_gps, latest_gps, measnum):

    # concentration (DELAYED GPS)
    outstr = ', '.join([
        delayed_gps[3][:10],
        datetime.datetime.now().strftime('%H:%M:%S.%f')[:10],
        ggadata.strip(),
        ', '.join(delayed_gps[:3]),
        str(measnum),
        '\n'
    ])

    # flighttrack (NO DELAY)
    flightstr = '  '.join([
        latest_gps[3],
        latest_gps[0],
        latest_gps[1],
        latest_gps[2],
        str(measnum),
        '\n'
    ])

    return outstr, flightstr


def format_aeris(cfg, aerisdata, delayed_gps, latest_gps, measnum):

    if cfg['AERIS']['GPSTyp'] == 'ext':
        outstr = '  '.join([
            delayed_gps[3][:10],
            datetime.datetime.now().strftime('%H:%M:%S.%f')[:10],
            f"{aerisdata['p']:.3f}",
            f"{aerisdata['T']:.3f}",
            f"{aerisdata['ch4']:.6f}",
            f"{aerisdata['c2h6']:.6f}",
            f"{aerisdata['h2o']:.6f}",
            ' '.join(delayed_gps[:3]),
            str(measnum),
            '\n'
        ])
    else:
        outstr = '  '.join([
            aerisdata["date"].strftime('%H:%M:%S.%f')[:10],
            datetime.datetime.now().strftime('%H:%M:%S.%f')[:10],
            f"{aerisdata['p']:.3f}",
            f"{aerisdata['T']:.3f}",
            f"{aerisdata['ch4']:.6f}",
            f"{aerisdata['c2h6']:.6f}",
            f"{aerisdata['h2o']:.6f}",
            f"{aerisdata['lat']:.6f}",
            f"{aerisdata['lon']:.6f}",
            f"{aerisdata.get('alt', 0.0):.6f}",
            str(measnum),
            '\n'
        ])

    flightstr = '  '.join([
        latest_gps[3],
        latest_gps[0],
        latest_gps[1],
        latest_gps[2],
        str(measnum),
        '\n'
    ])

    return outstr, flightstr                
                
def read_device(cfg, queue, event, date):

    device_type = cfg['Default']['device']
    measnum = cfg['LogParams'].getint('startnum')

    gpsdata = ['+000.00000', '+0000.00000', '00000', '00:00:00.000']

    # -------------------------
    # DEVICE SETUP
    # -------------------------
    if device_type == 'aeris':

        timelag = cfg['AERIS'].getint('timelag', fallback=3)

        device = aeris_methane_ethene_serial(
            port_path=cfg['AERIS']['port'],
            tube_delay=timelag
        )

        formatter = format_aeris

    elif device_type == 'losgatos':

        timelag = cfg['GGA'].getint('timelag', fallback=3)

        ggacom = opencom(
            cfg['GGA']['port'],
            cfg['GGA'].getint('baudrate'),
            cfg['GGA'].getint('timeout'),
            bytesize=cfg['GGA'].getint('bytesize'),
            parity=cfg['GGA']['parity'],
            stopbits=cfg['GGA'].getint('stopbits')
        )

        ggacom = ggacom.__enter__()  # manually enter context
        ggacom.reset_input_buffer()

        device = ggacom
        formatter = format_losgatos

    else:
        raise ValueError("Unknown device")

    gps_buffer = collections.deque(maxlen=timelag)

    # -------------------------
    # MAIN LOOP
    # -------------------------
    while not event.is_set():

        # ---------------------
        # READ DATA
        # ---------------------
        if device_type == 'aeris':
            data = device.update()
            if not data:
                continue

        else:  # losgatos
            if device.in_waiting <= 1:
                continue

            data = device.readline().decode()
            if not data.strip():
                continue

        # ---------------------
        # GPS handling
        # ---------------------
        if queue:
            gpsdata = queue[-1]

        gps_buffer.appendleft(gpsdata)

        if len(gps_buffer) < timelag:
            continue

        delayed_gps = gps_buffer.pop()
        latest_gps = gpsdata

        measnum += 1

        # ---------------------
        # FORMAT OUTPUT
        # ---------------------
        outstr, flightstr = formatter(
            cfg, data, delayed_gps, latest_gps, measnum
        )

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