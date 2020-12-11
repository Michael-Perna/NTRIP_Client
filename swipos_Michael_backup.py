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

SERIALPORT = '/dev/ttyAMA1'

HOST = 'www.swipos.ch'  # NTRIP Caster
PORT = 2101             # Port used by the NTRIP caster
MOUNTPOINT = 'MSM_GISGEO_LV95LHN95'
USER = 'swisstopoMobility2'
PASSWORD = 'wabern3084'
USERAGENT = 'RTKraspberry'
BAUDRATE = 115200
#ggaString = '$GPGGA,082904.398,4655.677,N,00727.100,E,1,12,1.0,0.0,M,0.0,M,,*6C\r\n'

# =============================================================================
# def parseGPS(str):
#     if str.find('GNGGA') > 0:
#         msg = pynmea2.parse(str)
#         print (msg)
#         return msg
#  
# 
# def getGGAString():
#     
#     ggaString = '$GPGGA,082904.398,4655.677,N,00727.100,E,1,12,1.0,0.0,M,0.0,M,,*6C\r\n'
#     #now = datetime.datetime.utcnow()
#     #ggaString= "GPGGA,%02d%02d%04.2f,%02d%011.8f,%1s,%03d%011.8f,%1s,1,05,0.19,+00400,M,%5.3f,M,," % \
#     #    (now.hour,now.minute,now.second,latDeg,latMin,flagN,lonDeg,lonMin,self.flagE,self.height)
#     checksum = calcultateCheckSum(ggaString)
#     print("$%s*%s\r\n" % (ggaString, checksum))
#     
#     return "$%s*%s\r\n" % (ggaString, checksum)
# 
# def calcultateCheckSum(stringToCheck):
#     xsum_calc = 0
#     for char in stringToCheck:
#         xsum_calc = xsum_calc ^ ord(char)
#     return "%02X" % xsum_calc
#     
# =============================================================================
def getRTCM(ggaString):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print('Failed to create socket')
        sys.exit()
    
    print('# Getting remote IP address') 
    try:
        remote_ip = socket.gethostbyname(HOST)
    
    except socket.gaierror:
        print('Hostname could not be resolved. Exiting')
        sys.exit()
    
    # Connect to remote server
    print('# Connecting to server, ' + HOST + ' (' + remote_ip + ')')
    error_indicator = s.connect_ex((remote_ip , PORT))
    print(error_indicator)
    
    if error_indicator==0:
        userpswd = USER + ':' + PASSWORD
        access = base64.b64encode(userpswd.encode('utf-8'))
        
        
        header =\
            'GET /{} HTTP/1.1\r\n'.format(MOUNTPOINT) +\
            'User-Agent: NTRIP {}\r\n'.format(USERAGENT) +\
            'Authorization: Basic {}\r\n'.format(access.decode('utf-8')) +\
            'Accept:rtk/rtcm\r\n\r\n' +\
            '{}'.format(ggaString)
        hostString = "Host: %s:%i\r\n" % (HOST,PORT)
        #print(mountPointString + hostString)
        print(header)
        s.sendall(header.encode('utf-8'))
        casterResponse=s.recv(1024) #All the data
        header_lines = casterResponse.decode('utf-8').split("\r\n")
    
    
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
                print(line)
                rtcmString = s.recv(4096)
                print(rtcmString)
                
            elif line.find("HTTP/1.0 200 OK")>=0:
                #Request was valid
                print(line)
                rtcmString = s.recv(4096)
                print(rtcmString)
            elif line.find("HTTP/1.1 200 OK")>=0:
                #Request was valid
                print(line)
                rtcmString = s.recv(4096)
                print(rtcmString)
    return rtcmString


serialPort = serial.Serial(SERIALPORT, baudrate = BAUDRATE, timeout = 0.5)
while True:
    str = serialPort.readline()
         
    if str.find('GNGGA') > 0:
        ggaString = pynmea2.parse(str)
        print (ggaString)
        rtcmString = getRTCM(ggaString)
        print(rtcmString)
        serialPort.write(rtcmString)
        
        