#!/usr/bin/env python

"""
Created on Sat Dec 12 14:20:40 2020.

@author: Daniel
"""
import socket
import sys
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
USER = 'swisstopo***'
PASSWORD = '********'
USERAGENT = 'RTKraspberry'
LOG_FOLDER = '/home/pi/swipos_nmea/'
LOG_REAPEAT = 1200  # Interval of time in second to save into new log file

BAUDRATE = 115200
# Global variables (queues for the messages)
rtcm_queue = queue.Queue()
gga_queue = queue.Queue()
ser_queue = queue.Queue()


class NtripSocket(threading.Thread):
    """Establish NTRIPClient server (1st Thread)."""

    def __init__(self):
        """Initialize NtripSocket class."""
        print("NTRIP socket initialized")

        # Initialize Thread
        threading.Thread.__init__(self)

        # Initialize socket 'self.s'
        socket.setdefaulttimeout(5)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Initialize class parameters
        self.is_connected = False
        self.is_listening = False
        self.counter = 0

    def reset(self):
        """NtripSocket() class reinitialization."""
        print("NTRIP socket re-initialized")

        # Close previous socket
        self.s.shutdown(2)
        self.s.close()

        # Open new socket
        socket.setdefaulttimeout(5)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        """Establish socket connection and send NTRIPCaster server request."""
        # Test the socsocket might be open already
        try:
            remote_ip = socket.gethostbyname(HOST)
            error_indicator = self.s.connect_ex((remote_ip, PORT))
            print('Connection error indicator : ', error_indicator)

            if error_indicator == 0:
                # Prepare the authentification string for the NTRIP caster
                userpswd = USER + ':' + PASSWORD
                # Encode the user name and password 4 security
                access = base64.b64encode(userpswd.encode('utf-8'))

                # SERVER REQUEST
                server_request =\
                    'GET /{} HTTP/1.0\r\n'.format(MOUNTPOINT) +\
                    'User-Agent: NTRIP {}\r\n'.format(USERAGENT) +\
                    'Authorization: Basic {}\r\n'.format(
                        access.decode('utf-8')) +\
                    'Accept: */*\r\n\r\n' +\
                    '{}\r\n'.format(gga_queue.get())

                print('server request : ', server_request)
                print('\r\nConnection to server')

                # Send the request
                self.s.sendall(server_request.encode('utf-8'))

                # Listen the answer
                casterResponse = self.s.recv(1024)
                print('Caster response : ', casterResponse)

                # TODO: Uniform all differents error messages
                # HINT: insert inside except socket.error as err
                if ("ICY 200 OK").encode('utf-8') in casterResponse:
                    print('Connected')
                    self.is_connected = True

                elif ("401 Unauthorized").encode('utf-8') in casterResponse:
                    print('401 Unauthorized')
                    # Reset connection
                    self.is_connected = False
                    self.reset()
                    # Wait before reattempt a server connection
                    time.sleep(0.5)
                else:
                    print('Caster response (repeat) : ', casterResponse)
            else:
                self.reset()
                print('Connection error indicator (repeat) : ',
                      error_indicator)

                # Wait before reattempt a server connection
                time.sleep(0.5)

        except socket.error as err:
            print('Hostname could not be resolved. %s. Exiting', err)

            # Reset connection
            self.is_connected = False
            self.reset()

            # Pause the code before reatempt a server connection
            time.sleep(0.5)

    def run(self):
        """Run Threadfunction() or restablish connection after Excpetion."""
        while True:
            try:
                self.threadfunction()
            except Exception as err:
                print('Disconnection %s', err)
                print('Restarting thread')
                self.is_connected = False
            else:
                print('Exited normally, bad thread; restarting')

    def threadfunction(self):
        """Infinite loop starting when the first NMEA-GGA message arrives."""
        while gga_queue.empty():
            time.sleep(0.05)

        while True:
            # Count number of received RTCM messages
            self.counter = self.counter + 1

            # if there is connection attempt a connection
            if not self.is_connected:
                self.connect()
                # reset counter
                self.counter = 0

            if self.is_connected:
                # Listen to the NTRIPCaster answer
                try:
                    self.s.settimeout(4)
                    rtcm_line = self.s.recv(1000000)
                    print('RTCM message received.'
                          f'\t\tCounter : {self.counter}')

                    # In case of disconnection, set flag accordingly
                    if len(rtcm_line) < 3:
                        print('RTCM smaller than 3 charachters')
                        self.is_connected = False

                # FIXME: apply the right Exception
                except Exception as err:
                    print('No message from NTRIP caster', err)
                    self.is_connected = False

                # Add RTCM to the queue
                try:
                    # add the rtcm_line to the queue
                    rtcm_queue.put(rtcm_line)

                except Exception as err:
                    # In case of disconnection, set flag accordingly
                    print(f'Disconnection, {err}')
                    self.is_connected = False

                # send a new GGA message from time to time
                if not gga_queue.empty() and self.is_connected:
                    print('Queue size : ', gga_queue.qsize())

                    # Always get the most recent gga
                    # FIXME: Flush all the queues (RTCM & gga) when ?
                    # FIXME: Improve try .. except structure
                    try:
                        if gga_queue.qsize() > 1:
                            my_str = gga_queue.queue[-1]
                            print('A NMEA message is send to the NTRIPCaster:'
                                  f' \n {my_str}\n')
                            with gga_queue.mutex:
                                gga_queue.queue.clear()
                        else:
                            my_str = gga_queue.get()
                            print('A NMEA message is send to the NTRIP caster:'
                                  f' \n {my_str}\n')

                    except Exception as err:
                        print('Queue flush didn''t worked')
                        print(err)

                    try:
                        self.s.send(my_str.encode('utf-8'))
                    except Exception as err:
                        """When the internet connection is not wroking
                        socket.send() raise an exception"""
                        print('Couldn''t send gga message')
                        print(err)
                        self.is_connected = False

                # Re-connect after disconnection
                if not self.is_connected:
                    print('Disconnection (38)')
                    self.reset()


class NmeaSerial(threading.Thread):
    """Establish serial connection (2nd and 3th threads).

    Principal functions:
    read_nmea():        Receipt valid NMEA messages from self.serialPort and it
                        identifies the GGA messages which is put to the
                        gga_queue(). Infinite loop
    send_rtcm():        It send the rtcm messages receipt from the NTRIPCaster
                        server (queue_rtcm()) and it trasnmit them to the
                        self.serialPort
    """

    def __init__(self):
        """NmeaSerial() class initialization."""
        print("Nmea Serial initialized")

        # Initialize Thread
        threading.Thread.__init__(self)

        # Initialize serial connection
        self.serialPort = serial.Serial(SERIALPORT,
                                        baudrate=BAUDRATE,
                                        timeout=0.5)

        # Initialize class parameters
        self.is_open = False
        self.filename = 'This is not a file name'
        self.log_file = None
        self.count = 0

    def checksum(self, nmea):
        """
        Checksum the NMEA messages.

            Parameters:
                nmea (str):     A NMEA string message (utf-8)

            Returns:
                valid (str):    True  if the NMEA message is valid
                                False if the NMEA message is not valid
        """
        try:
            cksumdata, cksum = nmea.split('*')
            # remove first charachter '$'
            empty, cksumdata = cksumdata.split('$')

        except: # TODO: apply right exception
            print('Checksum exception')
            valid = False
            return valid

        # Consider invalid all line with cksum with more than two digit
        # BUG: ISSUES ALL NMEA ARE SKIPED BECAUSE OF THIS CONTROL
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
            valid = True
            return valid
        else:
            valid = False
            return valid

    def read_nmea(self):
        """Listen continuosly to self.serialPort."""
        print('Read_nmea function start')

        while True:
            try:
                try:
                    # Read one line from the port
                    ser = self.serialPort.readline()
                    # Add entire line to the queue
                    ser_queue.put(ser.decode('utf-8'))

                    # print(f'port message {ser}')
                    if ser.decode('utf-8').find('GNGGA') > 0 and self.checksum(
                            ser.decode('utf-8')):
                        gga_queue.put(ser.decode('utf-8'))
                        print('A NMEA message was read from the serial port:'
                              f'\n {ser}\n')

                # TODO: apply right exception
                except:
                    print('Failed to read from dev/tty')
                    self.count = self.count + 1
                    pass

                if self.count > 50:
                    # Attempt new reconnaction
                    self.serialPort.close()
                    self.serialPort = serial.Serial(SERIALPORT,
                                                    baudrate=BAUDRATE,
                                                    timeout=0.5)

            # TODO: apply right exception
            except :
                print('read_nmea() function has failed ')
            time.sleep(0.5)

    def send_rtcm(self):
        """Continously send RTCM message to the self.serialPort."""
        # TODO: reduce branches
        try:
            print('read rtcm start')
             # Start infinite Loop
            while True:
                if not rtcm_queue.empty():
                    try:
                        rtcm_msg = rtcm_queue.get()
                        self.serialPort.write(rtcm_msg)

                    # TODO: apply excplicit  exception
                    except:
                        print('Failed to write from /dev/tty')
                        pass

        # TODO: apply excplicit  exception
        except :
            print('read_nmea() function has failed (repeat)')

    def threading_nmea(self):
        """Initialize and run read_nmea() thread."""
        threading.Thread(target=self.read_nmea).start()
        print("NMEA thread initialized")

    def threading_rtcm(self):
        """Initialize and run send_rtcm() thread."""
        threading.Thread(target=self.send_rtcm).start()
        print("RTCM thread initialized")


class Watchdog(threading.Thread):
    """Control that NtripSocket() thread is alive (4th thread)."""

    def __init__(self):
        """Initialize Watchdog class thread."""
        print("Watchdog initialized")

        # Initialize Thread
        threading.Thread.__init__(self)

    def run(self):
        """Continously control if NtripSocket() thread is alive."""
        while True:
            print(' Is it ''my_ntrip_socket'' thread alive? ',
                  my_ntrip_socket.isAlive())
            time.sleep(5)
            if not my_ntrip_socket.isAlive():
                pass


my_ntrip_socket = NtripSocket()
my_ntrip_socket.start()

my_watchdog = Watchdog()
my_watchdog.start()
my_nmea_serial = NmeaSerial()
my_nmea_serial.threading_nmea()
my_nmea_serial.threading_rtcm()
