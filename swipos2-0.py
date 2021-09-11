  
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
        print('1')
        self.is_listening = False
        print('2')
        socket.setdefaulttimeout(5)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print('3')
        self.counter = 0
        
    def reset(self):
        print("NTRIP socket re-initialized")
        # Close previous socket
        self.s.shutdown(2)
        print('4')
        self.s.close()
        # Open new socket
        print('5')
        socket.setdefaulttimeout(5)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    def connect(self):
        # socket might be open already
        try:
            print('6')
            remote_ip = socket.gethostbyname(HOST)
            print('7')
            error_indicator = self.s.connect_ex((remote_ip , PORT))
            print('Connection error indicator : ', error_indicator)
            
            if error_indicator == 0:
                # Prepare the authentification string for the NTRIP caster
                print('8')
                userpswd = USER + ':' + PASSWORD
                # Encode the user name and password 4 security
                print('9')
                access = base64.b64encode(userpswd.encode('utf-8')) 
                
                # SERVER REQUEST
                print('10')
                server_request =\
                    'GET /{} HTTP/1.0\r\n'.format(MOUNTPOINT) +\
                    'User-Agent: NTRIP {}\r\n'.format(USERAGENT) +\
                    'Authorization: Basic {}\r\n'.format(access.decode('utf-8')) +\
                    'Accept: */*\r\n\r\n' +\
                    '{}\r\n'.format(gga_queue.get())
                
                print('server request : ', server_request)
                
                print('\r\nConnection to server')
                self.s.sendall(server_request.encode('utf-8'))   # Send the request
                print('11')
                casterResponse = self.s.recv(1024)               # Listen the answer
                
                print('Caster response : ', casterResponse)
                
                if ("ICY 200 OK").encode('utf-8') in casterResponse:
                    print('Connected')
                    self.is_connected = True
                
                elif ("401 Unauthorized").encode('utf-8') in casterResponse:
                    print('401 Unauthorized')
                    self.is_connected = False
                    print('12')
                    self.reset()
                    # time.sleep(0.5)
                else:
                    print('Caster response (repeat) : ', casterResponse)
            else:
                self.reset()
                print('Connection error indicator (repeat) : ', error_indicator)
                time.sleep(0.5)
                
                            
        except:
            print('Hostname could not be resolved. Exiting')
            self.is_connected = False
            print('13')
            self.reset()
            print('14')
            time.sleep(0.5)
            
    # Thread wrap function, solution taken from StackOveriuew 
    # This after the encounter of a an exception "restard" the thread function
    def run(self):
        print('15')
        while True:
            print('15b')
            try:
                print('16')
                self.threadfunction()
                print('17')
            except:
                print('17b')
                print('disconnection (17c)')
                # self.reset()
                self.is_connected=False
                print('Restarting thread')
            else:
                print('exited normally, bad thread; restarting')
                
    def threadfunction(self):
        # Starting infinite loop when the first NMEA message arrive
        print('18')
        while gga_queue.empty():
            time.sleep(0.05)
        
        print('19')
        while True:
            print('20')
            self.counter = self.counter + 1
            
            ## if we are not connected, connect
            print('21')
            if not self.is_connected:
               print('22')
               self.connect()
               # reset counter 
               print('23')
               self.counter = 0
            
            print('24')
            if self.is_connected:
                ## Listen to NTRIP caster (Swipos)
                print('25')
                try:
                    print('26')
                    self.s.settimeout(4)
                    rtcm_line = self.s.recv(1000000)
                    #print(rtcm_line)
                    print(f'RTCM message received.      Counter : {self.counter}')
                    
                    # In case of disconnection, set flag accordingly
                    if len(rtcm_line) < 3:
                        print('RTCM smaller than 3 charachters')
                        self.is_connected = False
                except:

                    print('No message from NTRIP caster')
                    self.is_connected = False
                
                print('27')
                # Add RTCM to the queue
                try: 
                    print('28')    
                    # add the rtcm_line to the queue
                    rtcm_queue.put(rtcm_line)
                    print('29')
                except:
                    print('30')
                    # In case of disconnection, set flag accordingly
                    self.is_connected = False
                    print('31')
                    
                # send a new GGA message from time to time
                print('32')
                if not gga_queue.empty() and self.is_connected:
                    print('33, queue size : ', gga_queue.qsize() )
                    # Always get the most recent gga
                    try:
                        if gga_queue.qsize() > 1:
                            print('33a')
                            my_str = gga_queue.queue[-1]
                            print(f'A NMEA message is send to the NTRIP caster: \n {my_str}\n')
                            print('33b')
                            with gga_queue.mutex:
                                print('33c')
                                gga_queue.queue.clear()
                                print('33cc')
                        else:
                            print('33d')
                            my_str = gga_queue.get()
                            print(f'A NMEA message is send to the NTRIP caster: \n {my_str}\n')
                            print('33e')
                    except:
                        print('Queue flush didn''t worked')
                    print('34')
                    try:
                        print('35')
                        self.s.send(my_str.encode('utf-8'))
                        print('36')
                    except:
                        # when the connection is not wroking this raise an exception with send
                        print('Couldn''t send gga message')
                        self.is_connected = False
                        print('37')
                # Re-connect after disconnection
                print('38')
                if not self.is_connected:
                    print('disconnection (38)')
                    self.reset()
                    print('39')
                
                    
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
        print('a')
        try:    
            print('b')
            cksumdata, cksum = nmea.split('*')
            # remove first charachter '$'
            print('c')
            empty, cksumdata = cksumdata.split('$')
            print('d')
        # block raising an exception
        except:
            print('Checksum exception')
            return False # doing nothing on exception
        print('e')
        # Consider invalid all line with cksum with more than two digit
        #ISSUES ALL NMEA ARE SKIPED BECAUSE OF THIS CONTROL
        # if len(cksum) > 3:
        #     print(cksum)
        #     return False
        
        # Initializing first XOR value
        csum = 0 
        print('f')
        for c in cksumdata:
            # XOR'ing value of csum against the next char in line
            # and storing the new XOR value in csum
           # print('g')
           # print('g', c)
           csum ^= ord(c)
           # print('h')
           # print('checksum : ', csum)
        print('i')
        if hex(csum) == hex(int(cksum, 16)):
            print('j')
            return True
        else:
            print('k')
            return False
            
    def read_nmea(self):
        # Start infinity loop
        print('Read_nmea function start')
        
        #Add test if port is open otherwise try to open 
        while True:
            print('l')
            try:
                print('m')
                try:
                    # Read one line from the port
                    print('n')
                    ser = self.serialPort.readline()
                    # Add entire line to the queue
                    print('o')
                    ser_queue.put(ser.decode('utf-8'))
                    
                    # print(f'port message {ser}')
                    print('p')
                    if ser.decode('utf-8').find('GNGGA') > 0 and self.checksum(ser.decode('utf-8')):
                        print('q')
                        gga_queue.put(ser.decode('utf-8'))
                        print(f'A NMEA message was read from the serial port: \n {ser}\n')
                    # else:
                        # print(ser.decode('utf-8'))
                except:
                    print('Failed to read from dev/tty')
                    self.count = self.count + 1
                    print('r')
                    pass
                
                print('s')
                if self.count > 50 :
                    print('t')
                    # Attempt new reconnaction
                    self.serialPort.close()
                    print('u')
                    self.serialPort = serial.Serial(SERIALPORT, baudrate = BAUDRATE, timeout = 0.5)
                    print('v')
                    
            except :
                print('w')
                # print('read_nmea() function has failed ')
            time.sleep(0.5)
    
    def send_rtcm(self):
        print('x')
        try:
            print('read rtcm start')
             # Start infinite Loop
            while True:
                if not rtcm_queue.empty():
                    print('A')
                    try:
                        print('B')
                        rtcm_msg = rtcm_queue.get()
                        print('C')
                        self.serialPort.write(rtcm_msg)
                        print('C2')
                    except:
                        print('Failed to write from /dev/tty')
                        pass
        except :
            print('D')
            # print('read_nmea() function has failed (repeat)')

    def threading_nmea(self):
        threading.Thread(target = self.read_nmea).start()
        print("NMEA thread initialized")

    def threading_rtcm(self):
        threading.Thread(target = self.send_rtcm).start()
        print("RTCM thread initialized")
        
class Watchdog(threading.Thread):
    def __init__(self):
        print("Watchdog initialized")
        threading.Thread.__init__(self)

    def run(self):
        while True:
            print('Is thread alive :', my_ntrip_socket.isAlive())
            time.sleep(5)
            print('F')
            if not my_ntrip_socket.isAlive():
                print('G')
                pass

my_ntrip_socket = NtripSocket()
my_ntrip_socket.start()

my_watchdog = Watchdog()
my_watchdog.start()
my_nmea_serial = NmeaSerial()
my_nmea_serial.threading_nmea()
my_nmea_serial.threading_rtcm()
