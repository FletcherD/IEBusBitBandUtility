#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "spidev",
# ]
# ///
"""
IEBus BitBang Utility

A command-line tool for generating, processing, and transmitting IEBus messages
using bit-banging techniques. Supports message construction from strings,
Sigrok capture file processing, and hardware transmission via SPI.

Created on Wed Sep  6 02:00:13 2023
@author: fletcher
"""

import argparse
import IEBusBitBang
from IEBusMessage import IEBusMessage

if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(
		description='IEBus BitBang Utility - Generate, process, and transmit IEBus messages',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  # Transmit a single message
  python3 BitBangUtility.py --message "- 190 440 f 5 00 25 74 9C 04"

  # Simulate transmission (print bits instead of sending)
  python3 BitBangUtility.py --message "B 1ff 000 f 1 45" --simulate

  # Transmit at half speed for debugging
  python3 BitBangUtility.py --message "- 190 440 f 2 60 01" --slowdown 2.0

  # Process Sigrok capture files with protocol decoding
  python3 BitBangUtility.py --files capture1.sr capture2.sr

  # Process raw Sigrok data
  python3 BitBangUtility.py --filesRaw raw1.sr --channel RX

  # Add glitch bits for driver robustness testing
  python3 BitBangUtility.py --message "- 190 440 f 2 60 01" --glitch 100

  # Replay messages with regular timing (prevents collisions)
  python3 BitBangUtility.py --files captures.sr --regular 50000
		""")
	
	parser.add_argument('--message',
						action='store',
						type=str,
						help='Single IEBus message string to transmit. Format: "[B|-] <master_hex> <slave_hex> <ctrl_hex> <len> <data_hex>..."')
	
	parser.add_argument('--glitch', 
						action='store', 
						type=int, 
						default=0,
						help='Number of leading "1" bits to add for driver robustness testing (default: 0)')
	
	parser.add_argument('--regular', 
						action='store', 
						type=int, 
						default=0,
						help='Fixed interval in bit times between replayed messages to prevent collisions (default: 0 = use original timing)')
	
	parser.add_argument('--channel', 
						action='store', 
						type=str, 
						default='RX',
						help='Channel name to process from Sigrok files (default: RX)')
	
	parser.add_argument('--filesRaw', 
						action='store', 
						type=str, 
						nargs='*',
						help='Raw Sigrok capture files to process without protocol decoding')
	
	parser.add_argument('--files',
						action='store',
						type=str,
						nargs='*',
						help='Sigrok capture files to process with IEBus protocol decoding')
	
	parser.add_argument('--simulate', 
						action='store_true',
						help='Print bit sequence instead of transmitting to hardware')
	
	parser.add_argument('--slowdown', 
						action='store', 
						type=float, 
						default=1.0,
						help='Transmission speed multiplier (e.g., 2.0 = half speed, 0.5 = double speed, default: 1.0)')
	
	args = parser.parse_args()
	
	# Process single message string
	if args.message:
		print(f"Processing single message: {args.message}")
		msg = IEBusMessage(message_string=args.message)
		buf = IEBusBitBang.make_output_from_iebus_message(msg)
		
	# Process raw Sigrok files (no protocol decoding)
	elif args.filesRaw:
		print(f"Processing raw Sigrok files: {args.filesRaw}")
		buf = IEBusBitBang.make_output_from_sigrok_data(args.filesRaw, args.channel)
		
	# Process Sigrok files with IEBus protocol decoding
	else:
		print(f"Processing Sigrok files with protocol decoding: {args.files}")
		import SigrokUtil

		# Extract messages from all capture files
		messageLists = [SigrokUtil.getIEBus(file) for file in args.files]
		messages = []
		for messageList in messageLists:
			messages += messageList

		# Filter for specified channel and normalize timestamps
		messages = [row for row in messages if row[1] == args.channel]
		startTime = messages[0][0]
		messages = [(row[0] - startTime, row[1], row[2]) for row in messages]

		# Convert message strings to IEBus messages and generate bit sequences
		ieBusMessages = [IEBusMessage(message_string=row[2]) for row in messages]
		messageSignals = [IEBusBitBang.make_output_from_iebus_message(msg) for msg in ieBusMessages]
		
		# Calculate total signal length based on timing mode
		if args.regular != 0:
			# Fixed interval mode - prevents message collisions during replay
			totalLength = args.regular * len(ieBusMessages)
		else:
			# Original timing mode - preserves captured timing
			totalLength = messages[-1][0] + len(messageSignals[-1])

		# Build complete signal with proper timing
		signal = ['1'] * totalLength  # Initialize with idle state
		for i, ieBusMessage in enumerate(ieBusMessages):
			if args.regular != 0:
				time = i * args.regular  # Fixed spacing
			else:
				time = messages[i][0]  # Original timing
			messageOutput = list(IEBusBitBang.make_output_from_iebus_message(ieBusMessage))
			messageLen = len(messageOutput)
			signal[time:time+messageLen] = messageOutput

		buf = ''.join(signal)

	# Add idle bits either side
	buf = buf.strip('1')
	buf = '1' * 10000 + buf + '1' * 10000
	
	# Add glitch bits for driver robustness testing
	if args.glitch != 0:
		print(f"Adding {args.glitch} glitch bits for robustness testing")
		buf = '1' * args.glitch + buf

	# Output or transmit the signal
	if args.simulate:
		print(f"Simulation mode - bit sequence length: {len(buf)}")
		if args.slowdown != 1.0:
			print(f"Note: --slowdown {args.slowdown} would be applied during actual transmission")
		print(buf)
	else:
		print(f"Transmitting via SPI bit-bang (slowdown factor: {args.slowdown}x)...")
		import SPIBitBang
		buf = IEBusBitBang.bits_to_bytes(buf)
		SPIBitBang.bit_bang(buf, slowdown=args.slowdown)
