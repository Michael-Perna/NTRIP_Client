  
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
import datetime
import os

SERIALPORT = '/dev/ttyAMA1'

HOST = 'www.swipos.ch'  # NTRIP Caster
PORT = 2101             # Port used by the NTRIP caster
MOUNTPOINT = 'MSM_GISGEO_LV95LHN95'
USER = 'swisstopo****'
PASSWORD = '******'
USERAGENT = 'RTKraspberry'
LOG_FOLDER = '/home/pi/swipos_nmea/'
LOG_REAPEAT = 1200 # Interval of time in second to save into new log file

BAUDRATE = 115200
# ggaString = '$GPGGA,082904.398,4655.677,N,00727.100,E,1,12,1.0,0.0,M,0.0,M,,*6C\r\n'

# Global variables (queues for the messages)
rtcm_queue = queue.Queue()
gga_queue = queue.Queue()
ser_queue = queue.Queue()

# Server reading class
class NtripSocket(threading.Thread):
    def __init__(self):
        print("NTRIP socket initialized")
        threading.Thread.__init__(self)
        self.is_connected = False
        self.is_listening = False
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.counter = 0
        
    def reset(self):
        print("NTRIP socket re-initialized")
        # # Close previous socket
        # self.s.close()
        # Open new socket
        self.s.shutdown(2)
        self.s.close()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        
    def connect(self):
         # socket might be open already
        try:
            remote_ip = socket.gethostbyname(HOST)
            error_indicator = self.s.connect_ex((remote_ip , PORT))
            # print(error_indicator)
            
            if error_indicator == 0:
                # Prepare the authentification string for the NTRIP caster
                userpswd = USER + ':' + PASSWORD
                # Encode the user name and password 4 security
                access = base64.b64encode(userpswd.encode('utf-8')) 
                
                # SERVER REQUEST
                server_request =\
                    'GET /{} HTTP/1.0\r\n'.format(MOUNTPOINT) +\
                    'User-Agent: NTRIP {}\r\n'.format(USERAGENT) +\
                    'Authorization: Basic {}\r\n'.format(access.decode('utf-8')) +\
                    'Accept: */*\r\n\r\n' +\
                    '{}\r\n'.format(gga_queue.get())
                
                # print(server_request)
                
                print('\r\nConnection to server')
                self.s.sendall(server_request.encode('utf-8'))   # Send the request
                casterResponse = self.s.recv(1024)               # Listen the answer
                
                # print(casterResponse)
                
                if ("ICY 200 OK").encode('utf-8') in casterResponse:
                    print('Connected')
                    self.is_connected = True
                
                if ("401 Unauthorized").encode('utf-8') in casterResponse:
                    print('401 Unauthorized')
                    self.is_connected = False
                    self.reset()
                    # time.sleep(0.5)
            else:
                self.reset()
                print(error_indicator)
                time.sleep(0.5)
                
                            
        except socket.gaierror:
            print('Hostname could not be resolved. Exiting')
            time.sleep(0.5)

    def run(self):
        # Starting infinite loop when the first NMEA message arrive
        while gga_queue.empty():
            time.sleep(0.05)
        # print(gga_queue.get())
        
        while True:
            self.counter = self.counter + 1
            
            ## if we are not connected, connect
            if not self.is_connected:
               self.connect()
               # reset counter 
               self.counter = 0

            if self.is_connected:
                ## Listen to NTRIP caster (Swipos)
                try:
                    rtcm_line = self.s.recv(1000000)
                    # print(rtcm_line)
                    print(f'RTCM message received.      Counter : {self.counter}')
                    
                    # In case of disconnection, set flag accordingly
                    if len(rtcm_line) < 3:
                       self.is_connected = False
                except:
                    print('\r\nNo message from NTRIP caster')
                    self.is_connected = False
                    pass
                
                # Add RTCM to the queue
                try: 
                    # add the rtcm_line to the queue
                    rtcm_queue.put(rtcm_line)
                except:
                    # In case of disconnection, set flag accordingly
                    self.is_connected = False
                    
                    
                # send a new GGA message from time to time
                if not gga_queue.empty() and self.is_connected:
                    my_str = gga_queue.get()
                    try:
                        self.s.send(my_str.encode('utf-8'))
                    except:
                        # when the connection is not wroking this raise an exception with send
                        self.is_connected = False
                
                # Re-connect after disconnection
                if not self.is_connected:
                    print('disconnection')
                    # self.reset()
                    
class NmeaSerial(threading.Thread):
    def __init__(self):
        print("Nmea Serial initialized")
        threading.Thread.__init__(self)
        self.serialPort = serial.Serial(SERIALPORT, baudrate = BAUDRATE, timeout = 0.5)
        # self.time_thread = None
        self.is_open = False
        self.filename = 'This is not a file name'
        self.log_file = None
        self.count = 0
        
    def checksum(self, nmea):
        try:    
            cksumdata, cksum = nmea.split('*')
            # remove first charachter '$'
            empty, cksumdata = cksumdata.split('$')
            
        # block raising an exception
        except:
            print('Checksum exception')
            return False # doing nothing on exception
        
        # Consider invalid all line with cksum with more than two digit
        #ISSUES ALL NMEA ARE SKIPED BECAUSE OF THIS CONTROL
        # if len(cksum) > 3:
        #     print(cksum)
        #     return False
        
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
        
    
    def cron_log(self):
        
        # Create file once
        self.create_file()
        
        while True:
            time.sleep(LOG_REAPEAT)
            try:
                # Create new file each X second
                self.create_file()
            except:
                pass
            
            
    def create_file(self):
        try:
            # Get current time as string
            #date and time format: dd/mm/YYYY-H:M:S
            time_format="%Y-%m-%d_%H-%M-%S"
            current_time = datetime.datetime.now().strftime(time_format)

            # Give name to log file
            # IN FUTURE AS FUNCTION INPUT
            extension = '.txt'
            self.filename = LOG_FOLDER + current_time + extension
       
            # Open/Create new file 
            self.log_file = open(self.filename, 'w')
            print(f'Log file created: {self.filename}')
            
            self.is_open = True
        except:
            print(f'Could not create log file: {self.filename}')
            pass
                
    def save_log(self):

        # Start infinite Loop 
        while True:
            # this is in case of ncftput delete the actual file
            if not os.path.isfile(self.filename):
                self.create_file()
                
            if not ser_queue.empty():
                
                try:
                    # Get messages from queue
                    log_line = ser_queue.get()
                    
                    # Wirte in the file 
                    self.log_file.write(log_line)

                except:
                    print('Could not write into the log file: ')
                    pass
                
            time.sleep(0.5)

    def read_nmea(self):
        # Start infinity loop
        print('Read_nmea function start')
        
        #Add test if port is open otherwise try to open 

        while True:
            try:
                # Read one line from the port
                ser = self.serialPort.readline()
                # Add entire line to the queue
                ser_queue.put(ser.decode('utf-8'))
                
                # print(f'port message {ser}')
                if ser.decode('utf-8').find('GNGGA') > 0 and self.checksum(ser.decode('utf-8')):
                    gga_queue.put(ser.decode('utf-8'))
                    print(f'A NMEA message was read from the serial port: \n {ser}\n')
                # else:
                    # print(ser.decode('utf-8'))
            except:
                print('Failed to read from dev/tty')
                self.count = self.count + 1
                pass
            if self.count > 50 :
                # Attempt new reconnaction
                self.serialPort.close()
                
                self.serialPort = serial.Serial(SERIALPORT, baudrate = BAUDRATE, timeout = 0.5)
            
    def send_rtcm(self):
        print('read rtcm start')
         # Start infinite Loop
        while True:
            if not rtcm_queue.empty():
                try:
                    rtcm_msg = rtcm_queue.get()
                    self.serialPort.write(rtcm_msg)
                except:
                    print('Failed to write from /dev/tty')
                    pass

    def threading_nmea(self):
        threading.Thread(target = self.read_nmea).start()
        print("Thread initialized")

    def threading_rtcm(self):
        threading.Thread(target = self.send_rtcm).start()
        print("Thread initialized")
        
    def threading_cron(self):
        threading.Thread(target = self.cron_log).start()
        # self.time_thread = threading.Timer(720, self.save_log, args=self).start()
        print('New log threading')

    def threading_save(self):
        threading.Thread(target = self.save_log).start()
        # self.time_thread = threading.Timer(720, self.save_log, args=self).start()
        print('New log threading')
        
my_ntrip_socket = NtripSocket()
my_ntrip_socket.start()

my_nmea_serial = NmeaSerial()
my_nmea_serial.threading_nmea()
my_nmea_serial.threading_rtcm()
#my_nmea_serial.threading_cron()
#my_nmea_serial.threading_save()
