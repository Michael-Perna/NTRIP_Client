# -*- coding: utf-8 -*-
"""
Created on Fri Dec  4 07:51:10 2020

@author: Michael
"""
#  
#!/usr/bin/env python
"""
Created on Wed Dec  2 14:52:44 2020

@author: Michael
"""
import socket
import sys
import base64
import serial
import pynmea2
import time
import codecs


SERIALPORT = '/dev/ttyAMA1'

HOST = 'www.swipos.ch'  # NTRIP Caster
PORT = 2101             # Port used by the NTRIP caster
MOUNTPOINT = 'MSM_GISGEO_LV95LHN95'
USER = 'swisstopoMobility2'
PASSWORD = 'wabern3084'
USERAGENT = 'RTKraspberry'
BAUDRATE = 115200
ggaString = '$GPGGA,082904.398,4655.677,N,00727.100,E,1,12,1.0,0.0,M,0.0,M,,*6C\r\n'

    
# CREATE SOCKET
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    # s.UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # s.UDP_socket.bind(('', 0))
    # s.UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
except socket.error:
    print('Failed to create socket')
    sys.exit()

# Check IP adress validity
print('# Getting remote IP address') 
try:
    remote_ip = socket.gethostbyname(HOST)

except socket.gaierror:
    print('Hostname could not be resolved. Exiting')
    sys.exit()

# CONNECT TO REMOTE SERVER IP AND PORT
print('# Connecting to server, ' + HOST + ' (' + remote_ip + ')\n')
error_indicator = s.connect_ex((remote_ip , PORT))


# IF THE CONNECTION IS SUCESSUFULLY, IT DOES HTTP REQUEST
if error_indicator==0:
    print('Successfully opened socket\n')
    userpswd = USER + ':' + PASSWORD    # Prepare the authentification string for the NTRIP caster
    access = base64.b64encode(userpswd.encode('utf-8')) # Encode the user name and password 4 security
    
    # SERVER REQUEST
    server_request =\
        'GET /{} HTTP/1.0\r\n'.format(MOUNTPOINT) +\
        'User-Agent: NTRIP {}\r\n'.format(USERAGENT) +\
        'Authorization: Basic {}\r\n'.format(access.decode('utf-8')) +\
        'Accept: */*\r\n\r\n' +\
        '{}\r\n'.format(ggaString)

    print('server request :\r\n{}'.format(server_request))
    s.sendall(server_request.encode('utf-8'))   # Send the request
    casterResponse=s.recv(1024)                 # Listen the answer
    header_lines = casterResponse.decode('utf-8').split("\r\n")

    # CHECK SERVER ANSWER
    for line in header_lines:
        if line.find("SOURCETABLE")>=0:
            sys.stderr.write("Mount point does not exist")
            sys.exit(1)
        elif line.find("401 Unauthorized")>=0:
            sys.stderr.write("Unauthorized request\n")
            sys.exit(1)
        elif line.find("404 Not Found")>=0:
            sys.stderr.write("Mount Point does not exist\n")
            sys.exit(2)
        elif line.find("ICY 200 OK")>=0:
            #Request was valid
            print('Successfully connected to NTRIP caster')
            print(line)
        elif line.find("HTTP/1.0 200 OK")>=0:
            #Request was valid
            print(line)
        elif line.find("HTTP/1.1 200 OK")>=0:
            #Request was valid
            print(line)

    rtcm_line = True
    rtcm_msg = bytearray()
    c=0
    
    while rtcm_line:
        rtcm_line = s.recv(1048576)
        print(rtcm_line)
        # print(bytes.fromhex(rtcm_line))
        # print(rtcm_line)
        print(c)
        c = c + 1

    server_request =\
    'GET /{} HTTP/1.0\r\n'.format(MOUNTPOINT) +\
    'User-Agent: NTRIP {}\r\n'.format(USERAGENT) +\
    'Authorization: Basic {}\r\n'.format(access.decode('utf-8')) +\
    'Accept: */*\r\n\r\n' +\
    '{}\r\n'.format(ggaString)
    print('server request :\r\n{}'.format(server_request))
    s.sendall(server_request.encode('utf-8'))   # Send the request
    casterResponse=s.recv(1024)                 # Listen the answer
    header_lines = casterResponse.decode('utf-8').split("\r\n")

    rtcm_line = True
    rtcm_msg = bytearray()
    while rtcm_line:
        rtcm_line = s.recv(1048576)
        rtcm_msg += rtcm_line
    time.sleep(30)
    print('rtcm_msg is empty')
    print(rtcm_msg)    # SERVER REQUEST


