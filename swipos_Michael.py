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
ggaString = '$GPGGA,082904.398,4655.677,N,00727.100,E,1,12,1.0,0.0,M,0.0,M,,*6C\r\n'

def parseGPS(str):
    if str.find('GNGGA') > 0:
        msg = pynmea2.parse(str)
        print (msg)
        return msg
    
# def parseNMEA(file_name, msg):

#     count = 0
#     for line in nmea_file:
#         # we can process file line by line here, for simplicity I am taking count of lines
#         if str.find('GNGGA') > 0 and checksum(line):
#             output_file.write(line)
#         count += 1
    
#     #Close the opened files
#     nmea_file.close()
#     output_file.close()
    
#     # End of Process
#     print(f'Number of Lines in the file is {count}')

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
        # print('in')
        return True

    else:
        print('out')
        return False
       

serialPort = serial.Serial(SERIALPORT, baudrate = BAUDRATE, timeout = 0.5)

# Wait for GNGGA message
GNGGA_found = 0
while GNGGA_found==0:
    str = serialPort.readline()
    
    if str.find('GNGGA') > 0 and checksum(str):
        ggaString = str
        print (ggaString)
        GNGGA_found = 1
    
# CREATE SOCKET
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
print('# Connecting to server, ' + HOST + ' (' + remote_ip + ')')
error_indicator = s.connect_ex((remote_ip , PORT))
        
while True:
    # IF THE CONNECTION IS SUCESSUFULLY, IT DOES HTTP REQUEST
    if error_indicator==0:
        print('Successfully opened socket')
        userpswd = USER + ':' + PASSWORD    # Prepare the authentification string for the NTRIP caster
        access = base64.b64encode(userpswd.encode('utf-8')) # Encode the user name and password 4 security
        
        # SERVER REQUEST
        server_request =\
            'GET /{} HTTP/1.0\r\n'.format(MOUNTPOINT) +\
            'User-Agent: NTRIP {}\r\n'.format(USERAGENT) +\
            'Authorization: Basic {}\r\n'.format(access.decode('utf-8')) +\
            'Accept: */*\r\n' +\
            'Connection: close\r\n\r\n' +\
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

        rtcmString = True
        while rtcmString:
            rtcmString = s.recv(1024)
            serialPort.write(rtcmString)
            print(rtcmString)
        print('rtcm_msg is empty')
        print('\r\n\r\n\r\n\r\n\r\n\r\n\r\n\r\n')



# while True:
#     str = serialPort.readline()
    
#     if str.find('GNGGA') > 0:
#         ggaString = pynmea2.parse(str)
#         print (ggaString)
#         # ggaString = ggaString.encode('utf-8')
#         s.sendall(ggaString)
#         rtcm_msg = s.recv(100000)
        
        