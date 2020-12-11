# NTRIP_Client
NTRIP client for Swisspos,


swipos_Michael.py:        This Script does the connection between a serial port and a ntrip caster. It find the GGA message from the NMEA output of a GNSS receiver and send it to  the ntrip caster. Once it receive the RTCM message it send it back to the GNSS receiver. 
swipos_Michael_Test.py:   This Script send a fixe NMEA string to the ntrip caster Swipos. It work indipendently of a GNSS receiver. Therefore it can be used to test the connection. 
swipos_Michael_backup.py: This script is a junk script. 
