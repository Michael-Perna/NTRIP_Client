# NTRIP_Client

# Description 
NTRIP client tested with a u-blox ZED-F9P receiver working for swipos RTK service. The NTRIPClient is located on a Raspberry Pi 4 and the connection through the u-blox receiver throuch UART. 


## **swipos2-0.py**
This script solve the knowned bug of the previous version swipos.py and sucessufully reinitilize the NTRIP-Caster after a internet deconnection. However un minor bug has appear : the distance between the base station and the receiver position tend to grow with time ater it expereince interent deconnection. This issues has not enough be study but it doesn't had degrade the solution to be visible on our results. To fix this problem I suggest to flush the threading list of gga nmea message after each decconnation.

## **swipos_fixgga.py**
This Script send a fixe NMEA string to the ntrip caster Swipos. It work indipendently of a GNSS receiver. Therefore it can be used to test the connection messages.

# Credits & References
This code is heavly inspirated from the following code: 
- https://ozzmaker.com/using-python-with-a-gps-receiver-on-a-raspberry-pi/

- https://github.com/jcmb/NTRIP/blob/master/NTRIP%20Client/NtripClient.py

- https://github.com/tridge/pyUblox/blob/master/ntrip.py
- https://github.com/aortner/rtcmserver/blob/master/ntripserver.c

- https://docs.ros.org/en/api/oxford_gps_eth/html/ntrip__forwarding_8py_source.html

# Known Bug
- The distance between the base station and the receiver position tend to grow with time ater it expereince interent deconnection.

# Next step
- Merge second branch : make a realease of swipos2-0.py --> CUI
- Fix known bug 

