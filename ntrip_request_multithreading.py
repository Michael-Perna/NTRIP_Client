#  
#!/usr/bin/env python
"""
Created on Sat Dec 12 14:20:40 2020

@author: Daniel
"""
import socket
# import sys
import base64
import serial
# import pynmea2
import queue
import threading
import time

SERIALPORT = '/dev/ttyAMA1'

HOST = 'www.swipos.ch'  # NTRIP Caster
PORT = 2101             # Port used by the NTRIP caster
MOUNTPOINT = 'MSM_GISGEO_LV95LHN95'
USER = 'swisstopoMobility2'
PASSWORD = 'wabern3084'
USERAGENT = 'RTKraspberry'

BAUDRATE = 115200
ggaString = '$GPGGA,082904.398,4655.677,N,00727.100,E,1,12,1.0,0.0,M,0.0,M,,*6C\r\n'

# Global variables (queues for the messages)
rtcm_queue = queue.Queue()
gga_queue = queue.Queue()

# Server reading class
class NtripSocket(threading.Thread):
    def __init__(self):
        print("Thread initialized")
        threading.Thread.__init__(self)
        self.is_connected = False
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.counter = 0
        
    def run(self):
        # Starting infinite loop
        while True:
            self.counter = self.counter + 1
            print(self.counter)
            # if self.counter > 300:
                # break
            ## if we are not connected, connect
            if not self.is_connected:
                # socket might be open already
                try:
                    remote_ip = socket.gethostbyname(HOST)
                except socket.gaierror:
                    print('Hostname could not be resolved. Exiting')
                    time.sleep(0.05)
                    continue
                
                error_indicator = self.s.connect_ex((remote_ip , PORT))
                if not error_indicator == 0:
                    continue
                
                userpswd = USER + ':' + PASSWORD    # Prepare the authentification string for the NTRIP caster
                access = base64.b64encode(userpswd.encode('utf-8')) # Encode the user name and password 4 security
                
                # SERVER REQUEST
                server_request =\
                    'GET /{} HTTP/1.0\r\n'.format(MOUNTPOINT) +\
                    'User-Agent: NTRIP {}\r\n'.format(USERAGENT) +\
                    'Authorization: Basic {}\r\n'.format(access.decode('utf-8')) +\
                    'Accept: */*\r\n\r\n' +\
                    '{}\r\n'.format(ggaString)
                
                self.s.sendall(server_request.encode('utf-8'))   # Send the request
                casterResponse = self.s.recv(1024)                 # Listen the answer
                
                if ("ICY 200 OK").encode('utf-8') in casterResponse:
                    print('Connected')
                    self.is_connected = True
                    
            ## Listen
            rtcm_line = self.s.recv(1000000)
            print(rtcm_line)
            # add the rtcm_line to the queue
            rtcm_queue.put(rtcm_line)
            
            # in case of disconnection, set flag accordingly
            if len(rtcm_line) < 3:
                self.is_connected = False
            
            # send a new GGA message from time to time
            if round(self.counter/50.0) == self.counter / 50.0:
                self.s.send(ggaString.encode('utf-8'))
            
class UbxSerial(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.serialPort = serial.Serial(SERIALPORT, baudrate = BAUDRATE, timeout = 0.5)
        
    def checksum(nmea):
        try:    
            cksumdata, cksum = nmea.split('*')
            # remove first charachter '$'
            empty, cksumdata = cksumdata.split('$')
            
        # block raising an exception
        except:
            print('exception')
            return False # doing nothing on exception
        
        # Consider invalid all line with cksum with more than two digit
        if len(cksum) > 3:
            print( cksum)
            return False
        
        # Initializing first XOR value
        csum = 0 
        for c in cksumdata:
            # XOR'ing value of csum against the next char in line
            # and storing the new XOR value in csum
           csum ^= ord(c)
           
        if hex(csum) == hex(int(cksum, 16)):
            return True
        else:
            return False
        
    def run(self):
        if not rtcm_queue.empty():
            try:
                rtcm_msg = rtcm_queue.get()
                self.serialPort.write(rtcm_msg)
            except:
                pass
            
            try:
                my_str = self.serialPort.readline()
                if my_str.find('GNGGA') > 0 and self.checksum(my_str):
                    gga_queue.put(my_str)
            except:
                pass
            

my_ntrip_socket = NtripSocket()
my_ntrip_socket.start()

my_ubx_serial = UbxSerial()
my_ubx_serial.start()



    