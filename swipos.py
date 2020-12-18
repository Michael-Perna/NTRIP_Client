  
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

SERIALPORT = '/dev/ttyAMA1'

HOST = 'www.swipos.ch'  # NTRIP Caster
PORT = 2101             # Port used by the NTRIP caster
MOUNTPOINT = 'MSM_GISGEO_LV95LHN95'
USER = 'swisstopoMobility2'
PASSWORD = 'wabern3084'
USERAGENT = 'RTKraspberry'
LOG_FOLDER = '/home/pi/swipos_nmea/'
LOG_REAPEAT = 720 # Interval of time in second to save into new log file

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
        
        
    def run(self):
        # Starting infinite loop when the first NMEA message arrive
        while gga_queue.empty():
            time.sleep(0.05)
        # print(gga_queue.get())
        
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
                
                self.s.sendall(server_request.encode('utf-8'))   # Send the request
                casterResponse = self.s.recv(1024)                 # Listen the answer
                
                if ("ICY 200 OK").encode('utf-8') in casterResponse:
                    print('Connected')
                    self.is_connected = True
                
                # reset counter 
                self.counter = 0

            ## Listen to NTRIP caster (Swipos)
            try:
                rtcm_line = self.s.recv(1000000)
                print(rtcm_line)
                self.is_listening = True
            except:
                print('No message from NTRIP caster')
                pass
            
            # Add RTCM to the queue
            if self.is_listening:
                try: 
                    # add the rtcm_line to the queue
                    rtcm_queue.put(rtcm_line)
                except:
                    print('')
                    # In case of disconnection, set flag accordingly
                    if len(rtcm_line) < 3:
                        self.is_connected = False
                
                self.is_listening = False
                
                
            # send a new GGA message from time to time
            
            ###### REPLACE THIS BY A MESSAGE FROM THE QUEUE
            # if round(self.counter/50.0) == self.counter / 50.0:
            #     self.s.send(ggaString.encode('utf-8'))
                
            ###### FOR INSTANCE
            if not gga_queue.empty():
                my_str = gga_queue.get()
                self.s.send(my_str.encode('utf-8'))
            
class UbxSerial(threading.Thread):
    def __init__(self):
        print("UBX Serial initialized")
        threading.Thread.__init__(self)
        self.serialPort = serial.Serial(SERIALPORT, baudrate = BAUDRATE, timeout = 0.5)
        # self.time_thread = None
        self.is_open = False
        
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
        # Each 12 min create new log file
        # threading.Timer(720, self.save_log).start()
        self.save_log()
        while True:
            time.sleep(LOG_REAPEAT)
            self.save_log()
    def save_log(self):
        print('save log started')
        
        # First time is ingored then it will close the file before to open a new one
        print(f'file is open: {self.is_open}')
        if self.is_open:
            #Close the opened files
            log_file.close()
            self.is_open = False
        
        # Start infinite Loop 
        while True:

            if not self.is_open:
                print(f'ser_queue : {ser_queue.get()}')
                try:
                    # Get current time as string
                    #date and time format: dd/mm/YYYY-H:M:S
                    time_format="%d-%m-%Y_%H%M%S"
                    current_time = datetime.datetime.now().strftime(time_format)

                    # Give name to log file
                    # IN FUTURE AS FUNCTION INPUT
                    extension = '.txt'
                    file_name = LOG_FOLDER + current_time + extension
               
                    # Open/Create new file 
                    log_file = open(file_name, 'w')
                    print(f'Log file created: {file_name}')
                    
                    self.is_open = True
                except:
                    print(f'Could not create log file: {file_name}')
                    pass

            if not ser_queue.empty():
                # Write in the log file
                try:
                    # Get messages from queue
                    log_line = ser_queue.get()
                    
                    # Wirte in the file 
                    log_file.write(log_line)

                except:
                    print('Could not write into the log file: ')
                    pass
                
            time.sleep(0.5)

    def read_nmea(self):
        # Start infinity loop
        print('Read_nmea function start')
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
                pass
            
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
        
    def threading_log(self):
        threading.Thread(target = self.cron_log).start()
        # self.time_thread = threading.Timer(720, self.save_log, args=self).start()
        print('New log threading')

my_ntrip_socket = NtripSocket()
my_ntrip_socket.start()

my_ubx_serial = UbxSerial()
my_ubx_serial.threading_nmea()
my_ubx_serial.threading_rtcm()
my_ubx_serial.threading_log()