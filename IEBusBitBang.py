#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IEBus Bit-Bang Implementation

Provides functions for converting IEBus messages into bit sequences
suitable for transmission, and processing captured signals from logic analyzers.
Handles the specific timing requirements of the IEBus protocol.

Based on IEBus Mode 2 timing specifications:
- Bit rate: 1MHz (T_Bit = 40.7μs)
- Start bit: 170μs
- Logic 0: 4/5 * T_Bit high, 1/5 * T_Bit low
- Logic 1: 1/2 * T_Bit high, 1/2 * T_Bit low
"""
import subprocess

bitRate = 1000000

# IEBus timing constants (based on 1MHz bit rate)
T_Bit_uS = (256 / 6.291456)  # Approximately 40.7 microseconds

# Line state mapping for bit representation
lineState = { False: '1', True: '0' }

def uS_to_bits(time):
	"""Convert microseconds to number of bits at current bit rate."""
	return round(1e-6 * bitRate * time)

# Timing constants in bit units
T_StartBit		= uS_to_bits( 170 )      # Extended start bit duration
T_Bit			= uS_to_bits( T_Bit_uS ) # Standard bit duration
T_Bit_1			= uS_to_bits( T_Bit_uS / 2. )        # Logic 1 high duration
T_Bit_0			= uS_to_bits( 4. * T_Bit_uS / 5. )   # Logic 0 high duration
T_BitMeasure	= (T_Bit_1 + T_Bit_0) / 2            # Measurement threshold
T_TxWait		= uS_to_bits( 88 )       # Wait time after transmission
T_Timeout		= uS_to_bits( 2000 )     # Timeout duration

def make_output_segment(state, timeBits):
	"""
	Create a bit sequence for a given line state and duration.
	
	Args:
		state (bool): Line state (True=low, False=high)
		timeBits (int): Duration in bit times
		
	Returns:
		str: String of '0' or '1' characters representing the signal
	"""
	return lineState[state] * timeBits


def make_output_from_bit(bitVal):
	"""
	Convert a single data bit into an IEBus bit sequence.
	
	IEBus uses a preparation-sync-data encoding where each bit consists of:
	- High period (preparation): varies by bit value
	- Low period (remaining time): completes the bit duration
	
	Args:
		bitVal (int): 0 or 1 data bit
		
	Returns:
		str: Bit sequence string for transmission
	"""
	if bitVal == 0:
		return make_output_segment(True, T_Bit_0) + make_output_segment(False, (T_Bit - T_Bit_0))
	else:
		return make_output_segment(True, T_Bit_1) + make_output_segment(False, (T_Bit - T_Bit_1))


def make_output_from_iebus_bits(messageBits):
	"""
	Convert a sequence of message bits into a complete IEBus transmission.
	
	Adds proper start bit, sync period, and transmission wait time according
	to IEBus protocol requirements.
	
	Args:
		messageBits (list): List of boolean values representing message bits
		
	Returns:
		str: Complete transmission bit sequence
	"""
	bitStr = ''
	bitStr += make_output_segment(True, T_StartBit)  # Extended start bit
	bitStr += make_output_segment(False, T_Bit_1)    # Sync period
	for bitVal in messageBits:
		bitStr += make_output_from_bit(bitVal)
	bitStr += make_output_segment(False, T_TxWait)   # Post-transmission wait
	return bitStr


def make_output_from_iebus_message(message):
	"""
	Convert an IEBusMessage object into a bit sequence for transmission.

	Args:
		message (IEBusMessage): IEBus message object

	Returns:
		str: Bit sequence ready for hardware transmission
	"""
	msgBytes = message.getAsBytes()
	msgBits = bytes_to_bits(msgBytes)
	msgBits = msgBits[:message.getLengthInBits()]
	lineOutputBits = make_output_from_iebus_bits(msgBits)
	return lineOutputBits

	
def bytes_to_bits(messageBytes):
	"""
	Convert byte array to list of boolean bit values.
	
	Args:
		messageBytes (bytes): Raw message bytes
		
	Returns:
		list: List of boolean values (True=1, False=0)
	"""
	bitStr = ''.join(['{:08b}'.format(b) for b in messageBytes])
	bits = [c=='1' for c in bitStr]
	return bits


def bits_to_bytes(bitStr):
	"""
	Convert bit string to byte array, padding incomplete bytes with '1'.
	
	Args:
		bitStr (str): String of '0' and '1' characters
		
	Returns:
		bytes: Packed byte array suitable for SPI transmission
	"""
	byteStrings = [bitStr[i:i+8].ljust(8,'1') for i in range(0, len(bitStr), 8)]
	return bytes([int(byteStr,2) for byteStr in byteStrings])


def plot_output(lineOutputBits):
	"""
	Plot the bit sequence using matplotlib for visualization.
	
	Args:
		lineOutputBits (str): Bit sequence string to plot
	"""
	import matplotlib
	outputVals = [int(c) for c in lineOutputBits]
	matplotlib.pyplot.step(range(len(outputVals)), outputVals)


def make_output_from_sigrok_data(file, channel_to_read, file_sample_rate):
	"""
	Extract bit sequence from raw Sigrok capture data.
	
	Processes Sigrok capture files directly without protocol decoding,
	downsampling to match the target bit rate.
	
	Args:
		file (str or list): Sigrok file path(s) to process
		channel_to_read (str): Channel name to extract
		file_sample_rate (int): Original sample rate of the capture
		
	Returns:
		str: Downsampled bit sequence string
	"""
	if type(file) is list:
		return ''.join([make_output_from_sigrok_data(f, channel_to_read, file_sample_rate) for f in file])

	sampleN = round(file_sample_rate / bitRate)

	output_bits = ''
	command= ['sigrok-cli', '-i', file, '-O', 'bits']
	output = subprocess.check_output(command, stderr=subprocess.DEVNULL).decode()
	for line in output.split('\n'):
		try:
			channel, bitStr = line.split(':')
			if channel == channel_to_read:
				bitStr = bitStr.replace(' ', '').strip()
				output_bits += bitStr
		except:
			pass
	return output_bits[0::sampleN]

	

