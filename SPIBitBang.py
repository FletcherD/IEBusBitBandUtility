#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPI Bit-Bang Hardware Interface

Provides hardware transmission capabilities for IEBus messages using
Raspberry Pi SPI interface. Converts bit sequences into SPI transmissions
at the appropriate bit rate for IEBus communication.
"""

import spidev

# Initialize SPI interface
spi = spidev.SpiDev()
spi.open(0, 0)  # Bus 0, Device 0
spi.max_speed_hz = 1000000  # 1MHz to match IEBus bit rate
spi.bits_per_word = 8

bitRate = spi.max_speed_hz
print(f"SPI bit rate configured: {bitRate} Hz")

def bit_bang(output_as_bytes, slowdown=1.0):
	"""
	Transmit byte array via SPI at configured bit rate.
	
	This function sends the bit sequence to the IEBus using the
	Raspberry Pi's SPI interface. The SPI clock rate can be adjusted
	for debugging or compatibility purposes.

	Args:
		output_as_bytes (bytes): Byte array containing the bit sequence
		slowdown (float): Speed multiplier (2.0 = half speed, 0.5 = double speed)

	Note:
		Requires proper hardware connection between SPI MOSI and IEBus.
		Bus must be properly terminated and isolated for automotive use.
	"""
	# Adjust SPI speed based on slowdown factor
	original_speed = spi.max_speed_hz
	adjusted_speed = int(original_speed / slowdown)
	
	# Clamp speed to reasonable limits
	adjusted_speed = max(1000, min(adjusted_speed, 10000000))  # 1kHz to 10MHz
	
	if slowdown != 1.0:
		print(f"Adjusting SPI speed from {original_speed}Hz to {adjusted_speed}Hz (slowdown factor: {slowdown}x)")
		spi.max_speed_hz = adjusted_speed
	
	try:
		spi.writebytes2(output_as_bytes)
	finally:
		# Restore original speed
		if slowdown != 1.0:
			spi.max_speed_hz = original_speed
