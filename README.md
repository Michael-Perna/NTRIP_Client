# NTRIP_Client

# Description 
NTRIP client for Swisspos,


- **swipos.py**:        This Script does the connection between a serial port and a ntrip caster. It find the GGA message from the NMEA output of a GNSS receiver and send it to  the ntrip caster. Once it receive the RTCM message it send it back to the GNSS receiver. This is à fully working version of NTRIPCaster which however suffer of a known bug: after a brak in the internet conncetion or between the NTRIP Caster and the NTRIP server the NTRIP Client does not reinitilize correctly. 

- **swipos2-0.py**:   This script solve the knowned bug of swipos.py and sucessufully reinitilize the NTRIP-Caster after a internet deconnection. However un minor bug has appear : the distance between the base station and the receiver position tend to grow with time ater it expereince interent deconnection. This issues has not enough be study but it doesn't had degrade the solution to be visible on our results. To fix this problem I suggest to flush the threading list of gga nmea message after each decconnation.

- **swipos_fixgga.py**:   This Script send a fixe NMEA string to the ntrip caster Swipos. It work indipendently of a GNSS receiver. Therefore it can be used to test the connection messages.

# Table-of-Content
# Installation
# Usage
# Contributing
# Credits & References
This code is heavly inspirated from the following code: 
- https://ozzmaker.com/using-python-with-a-gps-receiver-on-a-raspberry-pi/

- https://github.com/jcmb/NTRIP/blob/master/NTRIP%20Client/NtripClient.py

- https://github.com/tridge/pyUblox/blob/master/ntrip.py
- https://github.com/aortner/rtcmserver/blob/master/ntripserver.c

- https://docs.ros.org/en/api/oxford_gps_eth/html/ntrip__forwarding_8py_source.html

# License

# News:
- **swipos.py**: 
- debug multithreating ntripcaster. Resolved bug with UbxSerail when using with a serial port
- Separete read_nmea and send_rtcm proccesses into two separeted thread
- Added a new thread that log all the NMEA messages into a tesxt file. The process restart each 12 minutes

# Next step
- Lunch the script as a command with the global variables as parameters
- **multithreafind**: https://www.geeksforgeeks.org/multithreading-python-set-1/
