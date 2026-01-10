#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IEBus Message Implementation

Provides classes and functions for creating, parsing, and validating IEBus messages.
Handles bit-level field manipulation with automatic parity calculation and validation.

The IEBus message format consists of:
- 1 bit: Broadcast flag
- 12 bits: Master address + parity + ACK
- 12 bits: Slave address + parity + ACK
- 4 bits: Control field + parity + ACK
- 8 bits: Data length + parity + ACK
- N×8 bits: Data fields, each with parity + ACK

Created on Sun Aug  6 20:47:10 2023
@author: fletcher
"""
import struct
from enum import IntEnum


class IEBusMessageField:
	"""
	Represents a field within an IEBus message with bit-level positioning.
	
	Used to define the layout of various fields (addresses, control, data)
	within the bit-packed message structure.
	"""
	def __init__(self, BitOffset, LengthBits):
		"""
		Initialize a message field definition.
		
		Args:
			BitOffset (int): Starting bit position within the message
			LengthBits (int): Number of bits for this field
		"""
		self.BitOffset = BitOffset
		self.LengthBits = LengthBits
		
	
class IEBusMessage:
	"""
	IEBus Message Implementation

	This class handles the creation, parsing, and validation of IEBus messages.
	Each message contains addresses, control information, and data with automatic
	parity checking.

	Message Structure (bit-level):
	- Broadcast (1 bit): 0=broadcast, 1=unicast
	- Master Address (12 bits) + Parity (1 bit)
	- Slave Address (12 bits) + Parity (1 bit) + ACK (1 bit)
	- Control (4 bits) + Parity (1 bit) + ACK (1 bit)
	- Data Length (8 bits) + Parity (1 bit) + ACK (1 bit)
	- Data Fields: N × (8 bits + Parity (1 bit) + ACK (1 bit))

	Protocol Notes:
	- First data byte is often 0x00 for unicast messages (common convention)
	- Second and third data bytes may contain source and destination device IDs
	- Remaining bytes contain the actual protocol data
	"""
	
	# Message field definitions (bit positions and lengths)
	Broadcast =       IEBusMessageField(0, 1)
	MasterAddress=    IEBusMessageField(1, 12)
	MasterAddress_P = IEBusMessageField(13, 1)
	SlaveAddress =    IEBusMessageField(14, 12)
	SlaveAddress_P =  IEBusMessageField(26, 1)
	SlaveAddress_A =  IEBusMessageField(27, 1)
	Control =         IEBusMessageField(28, 4)
	Control_P =       IEBusMessageField(32, 1)
	Control_A =       IEBusMessageField(33, 1)
	DataLength =      IEBusMessageField(34, 8)
	DataLength_P =    IEBusMessageField(42, 1)
	DataLength_A =    IEBusMessageField(43, 1)
	DataFieldLength = 10  # 8 data bits + 1 parity + 1 ACK
	
	@staticmethod
	def Data(n):
		"""Get data field definition for the nth data byte."""
		return IEBusMessageField(44 + (IEBusMessage.DataFieldLength * n), 8)
	
	@staticmethod
	def Data_P(n):
		"""Get parity field definition for the nth data byte."""
		return IEBusMessageField(44 + 8 + (IEBusMessage.DataFieldLength * n), 1)
	
	@staticmethod
	def Data_A(n):
		"""Get ACK field definition for the nth data byte."""
		return IEBusMessageField(44 + 9 + (IEBusMessage.DataFieldLength * n), 1)
	
	class BroadcastValue(IntEnum):
		UNICAST = 1,
		BROADCAST = 0
		
	class AckValue(IntEnum):
		NAK = 1,
		ACK = 0
		
	MaxMessageLenBytes = 64
	DefaultAckVal = AckValue.NAK
	
	def __init__(self, message_bytes=None, message_string=None,
				 broadcast=None, master_address=None, slave_address=None, control=None, data=None):
		"""
		Initialize an IEBus message from various input formats.

		Args:
			message_bytes (bytes, optional): Raw message bytes to parse
			message_string (str, optional): IEBus format string (e.g., "- 190 440 f 5 00 25 74 9C 04")
			broadcast (int, optional): Broadcast flag (0=broadcast, 1=unicast)
			master_address (int, optional): 12-bit master address
			slave_address (int, optional): 12-bit slave address
			control (int, optional): 4-bit control field
			data (list, optional): List of data bytes

		Examples:
			# From IEBus string format
			msg = IEBusMessage(message_string="- 190 440 f 5 00 25 74 9C 04")

			# From individual fields
			msg = IEBusMessage(broadcast=1, master_address=0x190, slave_address=0x440,
							   control=0xf, data=[0x00, 0x25, 0x74, 0x9C, 0x04])
		"""
		if message_bytes:
			self.message_bytes = message_bytes.ljust(IEBusMessage.MaxMessageLenBytes + 4)
			self.unpackFields()
			self.isValid()
			return

		if message_string:
			message_parts = message_string.replace(':', '').split()
			broadcast = (IEBusMessage.BroadcastValue.BROADCAST if message_parts[0] == 'B' else IEBusMessage.BroadcastValue.UNICAST)
			master_address = int(message_parts[1], 16)
			slave_address = int(message_parts[2], 16)
			control = 0xF
			data = [int(dStr, 16) for dStr in message_parts[3:]]

		# Extra bytes are to ensure we can unpack a value from the very end
		self.message_bytes = bytearray(IEBusMessage.MaxMessageLenBytes + 4)
		if broadcast:
			self.setField(IEBusMessage.Broadcast, broadcast)
		if master_address:
			self.setField(IEBusMessage.MasterAddress, master_address)
			self.setField(IEBusMessage.MasterAddress_P, calculateParity(master_address))
		if slave_address:
			self.setField(IEBusMessage.SlaveAddress, slave_address)
			self.setField(IEBusMessage.SlaveAddress_P, calculateParity(slave_address))
			self.setField(IEBusMessage.SlaveAddress_A, IEBusMessage.DefaultAckVal)
		if control:
			self.setField(IEBusMessage.Control, control)
			self.setField(IEBusMessage.Control_P, calculateParity(control))
			self.setField(IEBusMessage.Control_A, IEBusMessage.DefaultAckVal)
		if data:
			self.setField(IEBusMessage.DataLength, len(data))
			self.setField(IEBusMessage.DataLength_P, calculateParity(len(data)))
			self.setField(IEBusMessage.DataLength_A, IEBusMessage.DefaultAckVal)
			for i, val in enumerate(data):
				self.setField(IEBusMessage.Data(i), val)
				self.setField(IEBusMessage.Data_P(i), calculateParity(val))
				self.setField(IEBusMessage.Data_A(i), IEBusMessage.DefaultAckVal)
				

	def __str__(self):
		dataLen = self.getField(IEBusMessage.DataLength)
		messageStr = "{} {:03x} {:03x} {:01x} {:2d} : ".format(
			('B' if self.getField(IEBusMessage.Broadcast) == IEBusMessage.BroadcastValue.BROADCAST else '-'),
			self.getField(IEBusMessage.MasterAddress),
			self.getField(IEBusMessage.SlaveAddress),
			self.getField(IEBusMessage.Control),
			dataLen)
		for i in range(dataLen):
			messageStr += "{:02x} ".format(self.getField(IEBusMessage.Data(i)))
		return messageStr
				
				
	def getAsBytes(self):
		length_in_bits = self.getLengthInBits()
		length_in_bytes = int((length_in_bits - 1)/8)+1
		return self.message_bytes[:length_in_bytes]
		
		
	def getField(self, field):
		startByte = int(field.BitOffset/8)
		lenBytes = 4
		bitMask = (1 << field.LengthBits) - 1
		bitShift = (lenBytes*8) - field.LengthBits - (field.BitOffset%8)
			
		value = struct.unpack_from('>L', self.message_bytes, startByte)[0]
		value = (value >> bitShift) & bitMask
		return value


	def setField(self, field, value):
		startByte = int(field.BitOffset/8)
		lenBytes = 4
		bitMask = (1<<(field.LengthBits))-1
		bitShift = (lenBytes*8) - field.LengthBits - (field.BitOffset%8)
			
		bitMask = bitMask << bitShift
		value = value << bitShift
		
		valuePtr = struct.unpack_from('>L', self.message_bytes, startByte)[0]
		valuePtr = valuePtr & ~(bitMask)
		valuePtr = valuePtr | value
		struct.pack_into('>L', self.message_bytes, startByte, valuePtr)
		
		
	def getData(self):		
		dataLen = self.getField(IEBusMessage.DataLength)
		return bytearray([self.getField(IEBusMessage.Data(i)) for i in range(dataLen)])
		
	
	def isValid(self):
		isValid=True
		if self.getField(IEBusMessage.MasterAddress_P) != calculateParity(self.getField(IEBusMessage.MasterAddress)):
			print("Bad parity! MasterAddress")
			isValid=False
		if self.getField(IEBusMessage.SlaveAddress_P) != calculateParity(self.getField(IEBusMessage.SlaveAddress)):
			print("Bad parity! SlaveAddress")
			isValid=False
		if self.getField(IEBusMessage.Control_P) != calculateParity(self.getField(IEBusMessage.Control)):
			print("Bad parity! Control")
			isValid=False
		dataLength = self.getField(IEBusMessage.DataLength)
		if self.getField(IEBusMessage.DataLength_P) != calculateParity(dataLength):
			print("Bad parity! DataLength")
			isValid=False
		for i in range(dataLength):
			if self.getField(IEBusMessage.Data_P(i)) != calculateParity(self.getField(IEBusMessage.Data(i))):
				print("Bad parity! Data {}".format(i))
				isValid=False
		return isValid
	
	
	def getLengthInBits(self):
		dataLen = self.getField(IEBusMessage.DataLength)
		return IEBusMessage.Data(0).BitOffset + (IEBusMessage.DataFieldLength * dataLen)
	
	
	def unpackFields(self):
		"""
		Extract and parse IEBus message fields.

		This method parses the message and extracts:
		- Basic IEBus fields (addresses, control, data)
		- Removes leading 0x00 byte from unicast messages (common convention)
		- Identifies source and destination device IDs from first two data bytes

		Sets the following instance attributes:
			broadcast, master_address, slave_address, data_len, data, src_device, dst_device
		"""
		self.broadcast = self.getField(IEBusMessage.Broadcast)
		self.master_address = self.getField(IEBusMessage.MasterAddress)
		self.slave_address = self.getField(IEBusMessage.SlaveAddress)
		self.data_len = self.getField(IEBusMessage.DataLength)
		self.data = [self.getField(IEBusMessage.Data(i)) for i in range(self.data_len)]

		# Common convention: remove leading 0x00 from unicast messages
		if self.broadcast == IEBusMessage.BroadcastValue.UNICAST:
			self.data = self.data[1:]

		# Common convention: first two data bytes are device IDs
		self.src_device = self.data[0] if len(self.data) > 0 else 0
		self.dst_device = self.data[1] if len(self.data) > 1 else 0

		
def calculateParity(value):
	"""
	Calculate odd parity for a given value.
	
	IEBus uses odd parity, where the parity bit is set such that
	the total number of '1' bits (including parity) is odd.
	
	Args:
		value (int): Value to calculate parity for
		
	Returns:
		bool: Parity bit value (True=1, False=0)
	"""
	p = False
	while value != 0:
		if value & 0x1:
			p = not p
		value = value >> 1
	return p