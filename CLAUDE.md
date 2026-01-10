# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an IEBus bit-banging toolkit designed to help debug and test IEBus protocol decoder implementations. The utility generates valid IEBus messages through bit-banging on devices like Raspberry Pi using SPI, allowing developers to test their decoders with known-good signals.

The toolkit supports three operating modes:
1. **Manual message definition** - Construct and transmit messages via command-line strings
2. **Sigrok capture decoding** - Extract messages from logic analyzer captures and retransmit them
3. **Exact replay** - Reproduce captured IEBus signals on SPI with precise timing

## Architecture

### Core Components

- **IEBusMessage.py**: Message parsing and construction
  - `IEBusMessage` class: Handles bit-level message fields with parity
  - Message fields: broadcast, addresses, control, data with parity/ack bits
  - Supports both byte array and string construction
  - Built-in parity validation

- **IEBusBitBang.py**: Signal generation and timing
  - Converts messages to bit sequences for transmission
  - Timing constants: T_StartBit, T_Bit_0, T_Bit_1, T_TxWait
  - Sigrok data processing for captured signals
  - Bit rate: 1MHz (T_Bit_uS = 40.7μs)

- **SPIBitBang.py**: Hardware interface via SPI
  - Uses spidev library for Raspberry Pi SPI communication
  - Direct bit-banging to automotive bus

- **SigrokUtil.py**: Logic analyzer integration
  - Processes Sigrok capture files
  - Protocol decoder integration for IEBus
  - Message extraction and formatting

- **BitBangUtility.py**: Main command-line utility (uv script)
  - Implemented as a uv script with inline dependency management
  - Three operation modes: manual messages, decoded captures, exact replay
  - Message transmission via SPI or simulation output
  - Signal timing manipulation (slowdown, glitch injection, regular intervals)
  - Sigrok capture file processing
  - Automatically installs spidev dependency when run

## Development Commands

BitBangUtility.py is a uv script with inline dependency management. It automatically installs required dependencies when run.

### Running BitBangUtility.py

The main utility supports three operating modes:

**Mode 1: Manual Message Definition**
```bash
# Construct and transmit a single message
./BitBangUtility.py --message "- 190 1d0 f 2 60 01"

# Simulate without hardware (print bit sequence)
./BitBangUtility.py --message "B 1ff 000 f 1 45" --simulate

# Transmit at half speed for debugging
./BitBangUtility.py --message "- 190 1d0 f 2 60 01" --slowdown 2.0

# Add glitch bits for robustness testing
./BitBangUtility.py --message "- 190 440 f 2 60 01" --glitch 100
```

**Mode 2: Sigrok Capture Decoding**
```bash
# Decode and retransmit messages from capture files
./BitBangUtility.py --files capture1.sr capture2.sr

# Use fixed intervals to prevent message collisions during replay
./BitBangUtility.py --files captures.sr --regular 50000

# Specify channel to decode (default: RX)
./BitBangUtility.py --files capture.sr --channel TX
```

**Mode 3: Exact Replay**
```bash
# Reproduce exact signal timing from raw capture data
./BitBangUtility.py --filesRaw capture.sr --channel RX

# Combine with slowdown for debugging
./BitBangUtility.py --filesRaw capture.sr --channel RX --slowdown 2.0
```

### Running SigrokUtil.py

Stand-alone utility for message extraction:
```bash
# Extract and display messages from capture files
python3 SigrokUtil.py capture1.sr capture2.sr
```

### Dependencies

BitBangUtility.py uses uv for automatic dependency management - no manual installation required.

For other scripts, manual installation:
```bash
pip3 install spidev matplotlib tabulate
```

External tools:
- `uv` - Package manager (install via `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- `sigrok-cli` - For logic analyzer data processing

## Hardware Requirements

- Raspberry Pi (or similar device) with SPI enabled for bit-bang transmission
- Logic analyzer compatible with Sigrok for capture analysis (optional)
- Target IEBus hardware for testing decoder implementations

## Message Format

IEBus messages use this bit-level structure:
- 1-bit broadcast flag
- 12-bit master address + parity + ack
- 12-bit slave address + parity + ack  
- 4-bit control + parity + ack
- 8-bit data length + parity + ack
- N×8-bit data bytes, each with parity + ack

String format: `[B|-] <master_hex> <slave_hex> <ctrl_hex> <len> : <data_hex>...`

Example: `- 190 1d0 f 2 60 01` represents a unicast message from master 0x190 to slave 0x1d0 with control 0xF, length 2, and data bytes 0x60 0x01

## Protocol Notes

- Bus operates at 1MHz bit rate (T_Bit_uS = 40.7μs)
- Odd parity calculated across data bits for each field
- ACK/NAK responses built into message structure
- Broadcast vs unicast addressing (broadcast uses addresses like 0x1FF, 0xFFF)
- Common in Toyota/Lexus automotive systems

## Primary Use Case

This toolkit is designed for **testing and debugging IEBus protocol decoders**. By generating known-good IEBus signals through bit-banging, developers can:

- Validate decoder implementations against reference messages
- Test edge cases and error handling (via glitch injection)
- Reproduce captured bus traffic for regression testing
- Debug timing-sensitive decoder logic (via slowdown mode)
