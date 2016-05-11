#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  ble_bff.py
#
#  Copyright 2016 Spencer McIntyre <zeroSteiner@gmail.com>
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the  nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import argparse
import atexit
import logging
import os
import readline
import sys
import time

import serial

__version__ = '1.0'

DESCRIPTION = """\
A command line interface with completion support and general utility for
Adafruit's Bluefruit LE Friend, https://www.adafruit.com/products/2267. Ensure
that the device's hardware switch is set to CMD mode and not UART.
"""

HIST_FILE = os.path.join(os.path.expanduser('~'), '.ble-bff-history')

class BLEBFF(object):
	def __init__(self, device, timeout=0.5, encoding='utf-8'):
		self.encoding = encoding
		self.logger = logging.getLogger('BLEBFF')
		self._conn = serial.Serial(
			device,
			baudrate=9600,
			bytesize=serial.EIGHTBITS,
			parity=serial.PARITY_NONE,
			stopbits=serial.STOPBITS_ONE,
			timeout=timeout,
			rtscts=True,
			dsrdtr=True
		)
		at_resp = self.command('AT')
		if at_resp == 'AT\r\nOK':
			self.command('ATE=0')
		elif at_resp != 'OK':
			raise RuntimeError('device not responding as expected')

	def command(self, command):
		self.logger.info("running command: '{0}'".format(command))
		command = command.encode(self.encoding)
		command += b'\n'
		self._conn.write(command)
		resp = b''
		while not (resp.endswith(b'OK\r\n') or resp.endswith(b'ERROR\r\n')):
			chunk = self._conn.read(2 ** 8)
			if not chunk:
				break
			resp += chunk
		return resp.decode(self.encoding).rstrip()

	@property
	def commands(self):
		return tuple(c for c in self.command('AT+HELP').split(',') if c)

	def close(self):
		self._conn.close()

class BLEBFFConsoleCompleter(object):
	options = [
		'AT',
		'AT+BLEBEACON',
		'AT+BLEGETADDR',
		'AT+BLEGETADDRTYPE',
		'AT+BLEGETPEERADDR',
		'AT+BLEGETRSSI',
		'AT+BLEHIDCONTROLKEY',
		'AT+BLEHIDEN',
		'AT+BLEHIDMOUSEBUTTON',
		'AT+BLEHIDMOUSEMOVE',
		'AT+BLEKEYBOARD',
		'AT+BLEKEYBOARDCODE',
		'AT+BLEKEYBOARDEN',
		'AT+BLEPOWERLEVEL',
		'AT+BLEUARTFIFO',
		'AT+BLEUARTRX',
		'AT+BLEUARTTX',
		'AT+BLEURIBEACON',
		'AT+DBGMEMRD',
		'AT+DBGNVMREAD',
		'AT+DBGSTACKDUMP',
		'AT+DBGSTACKSIZE',
		'AT+DFU',
		'AT+EDDYSTONECONFIGEN',
		'AT+EDDYSTONEENABLE',
		'AT+EDDYSTONEURL',
		'AT+FACTORYRESET',
		'AT+GAPDELBONDS',
		'AT+GAPDEVNAME',
		'AT+GAPDISCONNECT',
		'AT+GAPGETCONN',
		'AT+GAPINTERVALS',
		'AT+GAPSETADVDATA',
		'AT+GAPSTARTADV',
		'AT+GAPSTOPADV',
		'AT+GATTADDCHAR',
		'AT+GATTADDSERVICE',
		'AT+GATTCHAR',
		'AT+GATTCLEAR',
		'AT+GATTLIST',
		'AT+HELP',
		'AT+HWADC',
		'AT+HWGETDIETEMP',
		'AT+HWGPIO',
		'AT+HWGPIOMODE',
		'AT+HWI2CSCAN',
		'AT+HWMODELED',
		'AT+HWRANDOM',
		'AT+HWVBAT',
		'ATE',
		'ATI',
		'ATZ'
	]
	def __call__(self, *args, **kwargs):
		return self.complete(*args, **kwargs)

	def complete(self, text, state):
		response = None
		if not state:
			self.matches = [s for s in self.options if s and s.startswith(text)] if text else self.options[:]

		if state <= len(self.matches):
			response = self.matches[state]
		else:
			response = None
		return response

def main():
	parser = argparse.ArgumentParser(description='It\'s your BLE-BFF!', conflict_handler='resolve')
	parser.add_argument('-L', '--log', dest='loglvl', choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'), default='WARNING', help='set the logging level')
	parser.add_argument('-r', '--rc-file', dest='resource_file', type=argparse.FileType('r'), help='an rc file to run commands from')
	parser.add_argument('-v', '--version', action='version', version='%(prog)s Version: ' + __version__)
	parser.add_argument('device', help='the device to use')
	parser.description = DESCRIPTION
	arguments = parser.parse_args()

	logging.getLogger('').setLevel(logging.DEBUG)
	console_log_handler = logging.StreamHandler()
	console_log_handler.setLevel(getattr(logging, arguments.loglvl))
	console_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s"))
	logging.getLogger('').addHandler(console_log_handler)

	bff = BLEBFF(arguments.device)

	if arguments.resource_file:
		for command in arguments.resource_file:
			command = command.rstrip()
			if not command:
				continue
			if command.startswith('#'):
				continue
			print('running command: ' + command)
			if command == 'exit':
				bff.close()
				return
			readline.add_history(command)
			print(bff.command(command))
		arguments.resource_file.close()

	while True:
		try:
			command = input(' > ')
			if command == 'exit':
				break
			print(bff.command(command))
		except (EOFError, KeyboardInterrupt):
			print('')
			break
		except UnicodeDecodeError as error:
			print('UnicodeDecodeError: ' + error.reason)
		except Exception:
			print('Use \'exit\' to exit the command loop')
	bff.close()

if __name__ == '__main__':
	readline.set_completer(BLEBFFConsoleCompleter())
	readline.parse_and_bind('tab: complete')
	readline.set_completer_delims(' \t\n`@#$%^&*()=[{]}\\|;:\'",<>?')
	readline.set_history_length(500)

	if os.access(HIST_FILE, os.R_OK):
		readline.read_history_file(HIST_FILE)
	main()
	readline.write_history_file(HIST_FILE)
