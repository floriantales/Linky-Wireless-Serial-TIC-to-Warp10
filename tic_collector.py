#!/usr/bin/env python3
#
# Purpose :
# This project goals to read TIC frames from serial port and publish them to warp10 websocket
#   - automatic websocket reconnection
#   - automatic serial device reconnection (usb key accidentally removed)
#   - catch APP
# 
# Credits :
# https://github.com/pyserial/pyserial/blob/master/examples/tcp_serial_redirect.py
#
# Project :
# http://doku.floriantales.fr/electronique/numerique/linky_tic
#
# Python dependencies :
# sudo pip install pyserial
# sudo pip install ws4py

#imports
import sys
import logging
import argparse
import serial
#imports_websockets
from ws4py.client.threadedclient import WebSocketClient
import time, socket

#global_vars
ws_connected = False  # State of ws connection
ws_connecting = False  # State of ws connection
ws_waitingforresponse = True # State of ws connection

#classes
class Warp10Client(WebSocketClient):
    def setup(self, timeout=2):
        globals()["ws_connecting"] = True
        try:
            self.__init__(self.url)
            self.connect()
        except:
            try:
                logging.error('Unable to connect. Retrying in %s second(s) ...',timeout)
                time.sleep(timeout)
                self.setup()
            except KeyboardInterrupt:
                logging.info('User interrupt')
                sys.exit(1)

    def received_message(self, msg):
        logging.info('Message received from Warp10 : %s', msg)
        globals()["ws_waitingforresponse"] = False

    def closed(self, code, reason=None):
        # Set flag connection to false
        globals()["ws_connected"] = False
        logging.error("Closed down (code=%s , reason=%s)", code, reason)
        
    def opened(self):
        logging.info('Connected to warp10')
        logging.info('Sending Token')
        globals()["ws_waitingforresponse"] = True
        self.send("TOKEN AP_8QdbvhyjFJuuOoohNyHJClJd7ODr.vP5GMt.Y6irthsyFdeaZt_vx2CeCrQfpF465ADT1RKD5e488pteN2MhfVomQbEHAPX8Ra3foeYo")
        while not globals()["ws_waitingforresponse"]:
            time.sleep(0.1)
        logging.info('Sending OnError directive')
        globals()["ws_waitingforresponse"] = True
        self.send("ONERROR MESSAGE")
        while not globals()["ws_waitingforresponse"]:
            time.sleep(0.1)
        # Set flags connection
        globals()["ws_connected"] = True
        globals()["ws_connecting"] = False

def serial_opendevice(self, timeout=2, retry=5):
    logging.info('Opening serial port')
    i = 0
    while not self.is_open and i < retry:
        try:
            i = (i + 1)
            self.open()
        except serial.SerialException as e:
            logging.error('Could not open serial port {}: {}'.format(self.name, e))
            logging.info('Retrying in {}s (attempt {}/{})'.format(timeout, i, retry))
            try :
                time.sleep(timeout)
            except KeyboardInterrupt:
                logging.info('User interrupt')
                sys.exit(1)
    
    if not self.is_open:
        logging.info('Unable to open serial port {})'.format(self.name))
        sys.exit(1)

    logging.info('Serial port opened')

def push_to_warp10(self, name, value):
    gts = "// " + name + "{} " + str(value)
    logging.info("GTS to send is : \"%s\"", gts)
    try:
        self.send(gts)
    except:
        globals()["ws_connected"] = False
        logging.error('Unable to send data to warp10. Websocket will be reconnected')


def main():

#conf_parser
    parser = argparse.ArgumentParser(
    description='Serial to Warp10 WebSocket redirector.',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""\
 TIC args example :
 -d /dev/ttyUSB0 -r 1200 --bytesize 7 --parity=E --stopbits=1 --loglevel=INFO
 """)

    parser.add_argument(
    '-q', '--quiet',
    action='store_true',
    help='mute',
    default=False)

    parser.add_argument(
    '--loglevel',
    choices=["ERROR", "INFO", "DEBUG"],
    help='set logging level',
    default="ERROR")

    group = parser.add_argument_group('serial port')

    group.add_argument(
    '-d','--device',
    help="serial port name, example : /dev/ttyUSB0")

    group.add_argument(
    '-r','--baud-rate',
    choices=[1200, 2400, 4800, 9600],
    type=int,
    help='set baud rate, default: %(default)s',
    default=9600)

    group.add_argument(
    "--bytesize",
    choices=[5, 6, 7, 8],
    type=int,
    help="set bytesize, one of {5 6 7 8}, default: 8",
    default=8)

    group.add_argument(
    "--parity",
    choices=['N', 'E', 'O', 'S', 'M'],
    type=lambda c: c.upper(),
    help="set parity, one of {N E O S M}, default: N",
    default='N')

    group.add_argument(
    "--stopbits",
    choices=[1, 1.5, 2],
    type=float,
    help="set stopbits, one of {1 1.5 2}, default: 1",
    default=1)

    group.add_argument(
    '--rtscts',
    action='store_true',
    help='enable RTS/CTS flow control (default off)',
    default=False)

    group.add_argument(
    '--xonxoff',
    action='store_true',
    help='enable software flow control (default off)',
    default=False)

    group.add_argument(
    '--rts',
    type=int,
    help='set initial RTS line state (possible values: 0, 1)',
    default=None)

    group.add_argument(
    '--dtr',
    type=int,
    help='set initial DTR line state (possible values: 0, 1)',
    default=None)

    group = parser.add_argument_group('network settings')

    exclusive_group = group.add_mutually_exclusive_group()

    exclusive_group.add_argument(
    '-P', '--warp10port',
    type=int,
    help='Warp10 WebSocket port',
    default=80)

    exclusive_group.add_argument(
    '-H', '--warp10host',
    help='Warp10 WebSocket host',
    default="localhost")

    args = parser.parse_args()

#conf_logger
    # Configure logging (https://docs.python.org/fr/3/howto/logging.html)
    loglevel_as_string = args.loglevel
    loglevel_as_numeric = getattr(logging, loglevel_as_string, None)
    if not args.quiet:
        #logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=loglevel_as_numeric, filename='SerialTic_to_Warp10.log', encoding='utf-8')
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=loglevel_as_numeric)

#conf_serial
    # Configure serial port
    ser = serial.serial_for_url(args.device, do_not_open=True)
    ser.baudrate = args.baud_rate
    ser.bytesize = args.bytesize
    ser.parity = args.parity
    ser.stopbits = args.stopbits
    ser.rtscts = args.rtscts
    ser.xonxoff = args.xonxoff
    if args.rts is not None:
        ser.rts = args.rts
    if args.dtr is not None:
        ser.dtr = args.dtr

#conf_warp10
    # Configure Warp10
    warp10_url = "ws://" + args.warp10host + ":" + str(args.warp10port) + "/api/v0/streamupdate"

#main
    logging.info('Serial to Warp10 Started')
    logging.info('Serial configuration is : {p.name}  {p.baudrate},{p.bytesize},{p.parity},{p.stopbits}'.format(p=ser))
    logging.info('Warp10 configuration is : %s',  warp10_url)

    # Open WS
    logging.info('Connecting to warp10 websocket')
    ws = Warp10Client(warp10_url)
    ws.setup()
    while not globals()["ws_connected"]:
        time.sleep(0.1)

    # Open serial
    serial_opendevice(ser, 2, 1)

    # Read TIC and push to Warp10
    logging.info('Starting to read TIC datas')
    try:
        #ser.reset_input_buffer() # Trash buffer before starting
        while True:
            if globals()["ws_connected"]: # Are we connected to websocket?
                # Try to read lines (\n) and decode (Python > 3)
                try:
                    line = ser.readline().decode('utf-8')
                except serial.SerialException as e:
                    logging.error('Exception on serial port {}: {}'.format(ser.name, e))
                    logging.info('Closing device')
                    ser.close()
                    logging.info('Trying to reconnect')
                    serial_opendevice(ser, 10, 99999)
                # Success
                logging.debug('New TIC line collected : %s', line.rstrip("\n"))
                words = line.split()

                # Try to read datas
                try:
                    TIC_data_type = words[0]
                except:
                    logging.error('Tic data type not formatted correctly -> skip')
                    pass
                else:
                    if TIC_data_type == 'PAPP':
                        TIC_data_value = int(words[1])
                        logging.debug('Apparent Power (PAPP) = %i VA', TIC_data_value)
                        push_to_warp10(ws, "tic.apparentpower.va", TIC_data_value)
                    elif TIC_data_type == 'BASE':
                        TIC_data_value = int(words[1])
                        logging.debug('Index (BASE) = %i Wh', TIC_data_value)
                        push_to_warp10(ws, "tic.index.wh", TIC_data_value)
            # If not connected and not allready connecting to websocket : reconnect            
            elif not globals()["ws_connecting"]:
                ws.close()
                logging.info('Reconnecting ...')
                ws.setup()
                ser.reset_input_buffer()
            # Else (if connecting .. ): wait
            else:
                time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info('User interrupt')
        pass

    # Epilog
    logging.debug('Closing Warp10 websocket')
    ws.close()
    logging.debug('Closing serial')
    ser.close()
    logging.info('Collector stopped')

if __name__ == '__main__': 
    main()
