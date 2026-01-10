#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IEBus Sigrok Utility

A tool for processing Sigrok logic analyzer capture files and extracting
IEBus messages using protocol decoders. Supports automatic channel
detection and message filtering/deduplication.

Created on Thu Sep  7 19:18:57 2023
@author: fletcher
"""
import subprocess
import csv
import json
import argparse

def getChannels(file, rx_channel=None, tx_channel=None):
	"""
	Detect available logic channels in a Sigrok file and return channel mapping.
	
	Args:
		file (str): Path to Sigrok capture file
		rx_channel (str, optional): Specific RX channel name to use
		tx_channel (str, optional): Specific TX channel name to use
		
	Returns:
		str: Channel mapping string for sigrok-cli (e.g., "RX,TX" or "D6=RX,D4=TX")
	"""
	command = ['sigrok-cli', '-i', file, '--show']
	output = subprocess.check_output(command, stderr=subprocess.DEVNULL).decode()
	output = output.split('\n')
	channels = []
	
	# Extract available logic channels
	for row in output:
		if len(row) == 0:
			continue
		row = row.split(':')
		if row[1].strip() == 'logic':
			channel = row[0].replace('-','').strip()
			channels.append(channel)
	
	# Use explicitly specified channels if provided
	if rx_channel and tx_channel:
		return f"{rx_channel},{tx_channel}"
	elif rx_channel:
		return f"{rx_channel}"
	
	# Auto-detect based on available channels
	if 'RX' in channels:
		return 'RX,TX'
	else:
		# Fallback for generic digital channels
		return 'D6=RX,D4=TX'

def getIEBus(file, rx_channel=None, tx_channel=None):
	"""
	Extract IEBus messages from a Sigrok capture file using protocol decoders.

	Args:
		file (str): Path to Sigrok capture file
		rx_channel (str, optional): Specific RX channel name
		tx_channel (str, optional): Specific TX channel name

	Returns:
		list: List of tuples (timestamp, channel, message_string)
			  where message_string is in IEBus format
	"""
	channels = getChannels(file, rx_channel, tx_channel)
	
	# Run sigrok-cli with IEBus protocol decoder
	command = ['sigrok-cli', '-i', file, '-C', channels,
			'-P', 'iebus:bus=RX:bus_polarity=idle-high:ignore_nak=Enabled',
			'-P', 'iebus:bus=TX:bus_polarity=idle-high:ignore_nak=Enabled',
			'-A', 'iebus=fields', '--protocol-decoder-jsontrace']
	output = subprocess.check_output(command, stderr=subprocess.DEVNULL).decode()
	output = json.loads(output)
	output = output['traceEvents']
	
	# Filter for begin events only
	output = [row for row in output if row['ph']=='B']
	outputRx = [row for row in output if row['pid']=='iebus-1']
	outputTx = [row for row in output if row['pid']=='iebus-2']

	def processOutput(output):
		"""
		Convert sigrok protocol decoder output into IEBus message strings.

		Args:
			output (list): Raw protocol decoder events

		Returns:
			list: Tuples of (timestamp, message_string)
		"""
		mList = []
		message = []
		messageTime = 0
		
		for row in output:
			field = row['name'].strip()
			if field == 'Broadcast':
				if len(message) != 0:
					mList.append((messageTime, ''.join(message)))
				message = []
				messageTime = int(row['ts'])
				message.append('B')
			elif field == 'Unicast':
				if len(message) != 0:
					mList.append((messageTime, ''.join(message)))
				message = []
				messageTime = int(row['ts'])
				message.append('-')
			else:
				[field, value] = field.split(':')
				if field in ['Master', 'Slave', 'Data']:
					value = value.replace('0x', '')
					message.append(value)
					
		if len(message) != 0:
			mList.append((messageTime, ''.join(message)))
		return mList

	def roundTime(row):
		"""Round timestamp to nearest millisecond for deduplication."""
		return int(row[0]/1000)

	# Process RX and TX channels
	outputRx = processOutput(outputRx)
	outputTx = processOutput(outputTx)

	# Remove RX messages that match TX messages (deduplication)
	# This removes our own transmitted messages from the capture
	outputTxRounded = [roundTime(row) for row in outputTx]
	outputRx = [row for row in outputRx if roundTime(row) not in outputTxRounded]
	
	# Format output with channel labels
	outputRx = [(row[0], 'RX', row[1]) for row in outputRx]
	outputTx = [(row[0], 'TX', row[1]) for row in outputTx]

	# Combine and sort by timestamp
	messages = sorted(outputRx + outputTx, key=lambda row: row[0])

	return messages

def areStringsEqual(sList):
	"""
	Check if all strings in a list are identical.
	
	Args:
		sList (list): List of strings to compare
		
	Returns:
		bool: True if all strings are equal, False otherwise
	"""
	for i in range(len(sList)-1):
		if sList[i] != sList[i+1]:
			return False
	return True

if __name__ == '__main__':
	from tabulate import tabulate
	
	parser = argparse.ArgumentParser(
		description='Extract and display IEBus messages from Sigrok capture files',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  # Process single capture file
  python3 SigrokUtil.py capture.sr

  # Process multiple related captures
  python3 SigrokUtil.py session_001.sr session_002.sr session_003.sr

  # Use specific channels
  python3 SigrokUtil.py --rx-channel CH1 --tx-channel CH2 capture.sr
		""")
	
	parser.add_argument('files', 
						type=str, 
						nargs='*',
						help='Sigrok capture files to process')
	
	parser.add_argument('--rx-channel',
						type=str,
						help='Specific RX channel name to use (overrides auto-detection)')
	
	parser.add_argument('--tx-channel', 
						type=str,
						help='Specific TX channel name to use (overrides auto-detection)')
	
	args = parser.parse_args()
	files = args.files

	# Generate output filename from common prefix of input files
	if files:
		baseFileNameLen = len(files[0])
		baseFileNames = [s[:baseFileNameLen] for s in files]
		while not areStringsEqual(baseFileNames):
			baseFileNameLen -= 1
			baseFileNames = [s[:baseFileNameLen] for s in files]
		outFileName = baseFileNames[0] + '.txt'

		# Process all files and extract messages
		messages = []
		for file in files:
			messages += getIEBus(file, args.rx_channel, args.tx_channel)
		
		# Output results to console and file
		with open(outFileName, 'w') as fOut:
			messagesStr = tabulate(messages, headers=['Timestamp', 'Channel', 'Message'])
			print(messagesStr)
			fOut.write(messagesStr + '\n')
			print(f"\nResults saved to: {outFileName}")
	else:
		parser.print_help()
