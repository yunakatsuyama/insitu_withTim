#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 17 14:46:43 2025

@author: mamap
"""


'''
Verbesserungsvorschläge:
    - serial kram in eigene klasse auslagern
    - bei erstkontakt mit aeris einmal dessen zeit ausgeben lassen zur kontrolle
    - timeout!!
'''


#from nclib import Netcat
import csv
import datetime as dt
import numpy as np
#import geopandas as gpd
import pandas as pd
#from shapely.geometry import Point
from threading import Thread
import glob #for checking serial device path
import serial

def array_shift(arr, val):
    """
    small shitty function to shift an array by one index and adding the newest on the bottom 
    """
    arr=np.append(arr, val)
    arr=arr[1:]
    return arr



#device class: all settings and routines

# class aeris_methane_ethene():
#     def __init__(self, tube_delay=3):

#         #init variables
        
#         self.df = pd.DataFrame(columns=["date", "p", "T", "ch4", "c2h6", "h2o", "lat", "lon"
#                                             # , "ch4_backgr", "ch4_norm"
#                                             ])
#         #for shifting coordinates wrt. methane due to lag of tube
        
#         self.lat_arr=np.array(np.zeros(tube_delay))
#         self.lon_arr=np.array(np.zeros(tube_delay))
    
#         # settings for qgis layer visualisation
#         self.device_name="aeris_methane_ethene" 
#         self.layer_name=f"Aeris methane / Ethene  RealTimeData "
#         self.layer_style="/Routines/multidevice-live-data-plottin/src/qgis_realtime/aeris_stil.qml"
#         #self.layer_style="/home/jthoboell/local/Data/dMamap/dRoutines/dVisualisierung/multidevice-live-data-plottin/src/qgis_realtime/aeris_stil.qml"
#         self.attribute_String=f"Point?crs=EPSG:4326&field=ch4:double&field=c2h6:double&field=datetime:string"
#         self.updating_classes=True
        
#         #settings for time series plots
#         self.plot_ts=True
#         self.y_vars = ["ch4", "c2h6"]
#         #self.plot_y1_name = "ch4"
#         self.ylabel ="Concentration in ppm"
#         #settings for csv-writing
#         self.csv_data_name_lst = ["date", "p", "T", "ch4", "c2h6", "h2o", "lat","lon"]
        
        
#         #init netcat-contact, pathes hard coded to mamap RT-computer
        
        
#         try:    
#             self.nc=Netcat(('192.168.17.205', 50000)) # Mamap Retriever
#             #self.nc=Netcat(('172.16.112.22', 50000)) #for testing at Jakobs desk
#             self.nc.recv(timeout=0.1)
#             print("")
#             print("netcat AERIS connected")
#         except:
#             print("Error, netcat AERIS Output at 192.168.17.205:50000")
#             exit()

#     def decode_AERIS(self, ser_bytes): #decodes the raw serial data 
#         decoded=list(csv.reader([ser_bytes[0:len(ser_bytes)-2].decode("utf-8")]))[0]
#         date=dt.datetime.strptime(decoded[0][:-4], '%m/%d/%Y %H:%M:%S' )
#         p=float(decoded[2]) #system pressure
#         T=float(decoded[3]) #gas temperature
#         ch4=float(decoded[6]) #concentration dry ppm
#         c2h6=float(decoded[8]) #concentration dry ppb
#         h2o=float(decoded[7]) #ppm
#         lat=float(decoded[15])
#         lon=float(decoded[16])
        
#         #FOR TESTING PURPOSES:
#         #creates a Line of coordinates, relative to the current time (for kalibrating color gradient):    
       
#         #lat=53.10547+dt.datetime.today().minute*0.009+dt.datetime.today().second*0.0001 
#         #lon=8.85044+dt.datetime.today().minute*0.009+dt.datetime.today().second*0.0001
        
#         #creates a random field of coordinates around the Uni Bremen
        
#        # lat=53.10547+np.random.rand()*0.01
#        # lon=8.85044+np.random.rand()*0.01
        
#         return date, p, T, ch4, c2h6, h2o, lat, lon
        
#     def readndecode(self):
#         #read
        
#         byteline = self.nc.recv(timeout=0.1)
#         #decode
#         if byteline:
#             try: 
#                 return self.decode_AERIS(byteline)
#             except: 
#                 return ''
#         else:
#             return ''
        
#     def update(self):
#         data = self.readndecode()
#         if data:
#         #delay
#             self.lat_arr = array_shift(self.lat_arr, data[6])
#             self.lon_arr = array_shift(self.lon_arr, data[7])
    
        
#             self.df.loc[len(self.df)] = list(data[0:-2])+[self.lat_arr[0], self.lon_arr[0]]

        
#             newln = self.df.loc[len(self.df)-1] 
#             newln_dict= newln.to_dict()
#             self.lat=newln_dict["lat"]
#             self.lon=newln_dict["lon"]
#             time_str = newln_dict["date"].strftime("%H:%M:%S")
#             self.qgis_attributes=[newln_dict["ch4"] ]+[newln_dict["c2h6"] ] + [time_str]
#             return newln_dict
#         else:
#             return  ''
        
        
        
        
class aeris_methane_ethene_serial():
    def __init__(self, port_path, tube_delay=3):

        #init variables
        
        self.df = pd.DataFrame(columns=["date", "p", "T", "ch4", "c2h6", "h2o", "lat", "lon"
                                            # , "ch4_backgr", "ch4_norm"
                                            ])
        #for shifting coordinates wrt. methane due to lag of tube
        
        self.lat_arr=np.array(np.zeros(tube_delay))
        self.lon_arr=np.array(np.zeros(tube_delay))
    
        # settings for qgis layer visualisation
        self.device_name="aeris_methane_ethene" 
        self.layer_name=f"Aeris methane / Ethene  RealTimeData "
        self.layer_style="/Routines/multidevice-live-data-plottin/src/qgis_realtime/aeris_stil.qml"
        #self.layer_style="/home/jthoboell/local/Data/dMamap/dRoutines/dVisualisierung/multidevice-live-data-plottin/src/qgis_realtime/aeris_stil.qml"
        self.attribute_String=f"Point?crs=EPSG:4326&field=ch4:double&field=c2h6:double&field=datetime:string"
        self.updating_classes=True
        
        #settings for time series plots
        self.plot_ts=True
        self.y_vars = ["ch4", "c2h6"]
        #self.plot_y1_name = "ch4"
        self.ylabel ="Concentration in ppm"
        #settings for csv-writing
        self.csv_data_name_lst = ["date", "p", "T", "ch4", "c2h6", "h2o", "lat","lon"]
        
        
        #init netcat-contact, pathes hard coded to mamap RT-computer
        self.path = port_path
        try:    
            self.ser = serial.Serial(self.path)
            print("")
            print("--serial port", self.path, "connected")
        except serial.serialutil.SerialException:
            print("Error: serial port", self.path, "not found")
            print("   Maybe you need", glob.glob('/dev/ttyUSB?'))
            exit()
        self.ser.flushInput()
        self.ser.flushOutput()      
        
    
    def decode_AERIS(self, ser_bytes): #decodes the raw serial data 
        decoded=list(csv.reader([ser_bytes[0:len(ser_bytes)-2].decode("utf-8")]))[0]
        date=dt.datetime.strptime(decoded[0][:-4], '%m/%d/%Y %H:%M:%S' )
        p=float(decoded[2]) #system pressure
        T=float(decoded[3]) #gas temperature
        ch4=float(decoded[6]) #concentration dry ppm
        c2h6=float(decoded[8]) #concentration dry ppb
        h2o=float(decoded[7]) #ppm
        lat=float(decoded[15])
        lon=float(decoded[16])
        # alt =float(decoded[17])        
        
        #FOR TESTING PURPOSES:
        #creates a Line of coordinates, relative to the current time (for kalibrating color gradient):    
       
        #lat=53.10547+dt.datetime.today().minute*0.009+dt.datetime.today().second*0.0001 
        #lon=8.85044+dt.datetime.today().minute*0.009+dt.datetime.today().second*0.0001
        
        #creates a random field of coordinates around the Uni Bremen
        
       # lat=53.10547+np.random.rand()*0.01
       # lon=8.85044+np.random.rand()*0.01
        
        return date, p, T, ch4, c2h6, h2o, lat, lon 
 
    def readndecode(self):
        #read
        self.ser.flushOutput()
        byteline = self.ser.readline()
        #decode
        return self.decode_AERIS(byteline)

        
    def update(self):
        
        data = self.readndecode()
        if data:
        #delay
            self.lat_arr = array_shift(self.lat_arr, data[6])
            self.lon_arr = array_shift(self.lon_arr, data[7])
            
            #self.alt_arr = array_shift(self.alt_arr, data[8])
            # print('alt', data[8])
    
        
            self.df.loc[len(self.df)] = list(data[0:-2])+[self.lat_arr[0], self.lon_arr[0]]

        
            newln = self.df.loc[len(self.df)-1] 
            newln_dict= newln.to_dict()
            self.lat=newln_dict["lat"]
            self.lon=newln_dict["lon"]
            time_str = newln_dict["date"].strftime("%H:%M:%S")
            self.qgis_attributes=[newln_dict["ch4"] ]+[newln_dict["c2h6"] ] + [time_str]
            return newln_dict
        else:
            return  ''
        
  
    
  
    
 