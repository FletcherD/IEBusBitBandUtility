# IEBus Bit-Bang Utility

A Python toolkit for debugging and testing IEBus protocol decoder implementations through bit-banging on hardware like Raspberry Pi.

## Purpose

This utility generates valid IEBus messages by bit-banging the protocol on devices with SPI interfaces. It's designed to help developers test and debug their IEBus protocol decoders by providing known-good reference signals. The toolkit can create messages from scratch, extract them from logic analyzer captures, or reproduce exact captured signals with precise timing.

## What is IEBus?

IEBus (Inter Equipment Bus) is a 1MHz serial communication protocol commonly used in Toyota/Lexus automotive systems. It features:
- Master/slave addressing with broadcast support
- Odd parity checking on all fields
- Built-in ACK/NAK responses
- Bit-level encoding with specific timing requirements

## Features

### Three Operating Modes

1. **Manual Message Definition** - Construct messages from command-line strings
2. **Sigrok Capture Decoding** - Extract and retransmit messages from logic analyzer captures
3. **Exact Replay** - Reproduce captured signals with precise timing

### Testing Capabilities

- **Simulation Mode** - View bit sequences without hardware
- **Speed Control** - Slow down or speed up transmission for debugging
- **Glitch Injection** - Add leading bits to test decoder robustness
- **Regular Intervals** - Replay messages with fixed spacing to prevent collisions
- **Channel Selection** - Process specific channels from multi-channel captures

## Installation

### Prerequisites

BitBangUtility.py is a uv script with automatic dependency management. Just install uv:

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# External tools (for logic analyzer support)
sudo apt-get install sigrok-cli
```

For other Python scripts (SigrokUtil.py, etc.), manual installation:
```bash
pip3 install spidev matplotlib tabulate
```

### Hardware Setup

- **Raspberry Pi** (or similar) with SPI enabled
- **Logic Analyzer** (optional, for capture mode) - any Sigrok-compatible device
- **Target IEBus device** or test circuit

Enable SPI on Raspberry Pi:
```bash
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable
```

## Usage

### Mode 1: Manual Message Definition

Define messages using the IEBus string format: `[B|-] <master_hex> <slave_hex> <ctrl_hex> <len> <data_hex>...`

- `B` = broadcast message, `-` = unicast message
- `master_hex` = 12-bit master address (3 hex digits)
- `slave_hex` = 12-bit slave address (3 hex digits)
- `ctrl_hex` = 4-bit control field (1 hex digit)
- `len` = data length in bytes (decimal)
- `data_hex` = data bytes (2 hex digits each)

```bash
# Transmit a unicast message
./BitBangUtility.py --message "- 190 1d0 f 2 60 01"

# Transmit a broadcast message
./BitBangUtility.py --message "B 1ff 000 f 1 45"

# Simulate without hardware (just print bit sequence)
./BitBangUtility.py --message "- 190 1d0 f 2 60 01" --simulate

# Transmit at half speed for debugging
./BitBangUtility.py --message "- 190 1d0 f 2 60 01" --slowdown 2.0

# Add 100 glitch bits to test decoder robustness
./BitBangUtility.py --message "- 190 440 f 2 60 01" --glitch 100
```

### Mode 2: Sigrok Capture Decoding

Extract messages from logic analyzer captures and retransmit them with IEBus protocol decoding.

```bash
# Decode and retransmit messages from capture files
./BitBangUtility.py --files capture1.sr capture2.sr

# Process specific channel (default: RX)
./BitBangUtility.py --files capture.sr --channel TX

# Replay with fixed 50000-bit intervals (prevents message collisions)
./BitBangUtility.py --files captures.sr --regular 50000

# Simulate to see what would be transmitted
./BitBangUtility.py --files capture.sr --simulate
```

### Mode 3: Exact Replay

Reproduce the exact signal from a capture, preserving all timing and signal characteristics.

```bash
# Reproduce exact signal timing from raw capture data
./BitBangUtility.py --filesRaw capture.sr --channel RX

# Slow down the replay for debugging
./BitBangUtility.py --filesRaw capture.sr --channel RX --slowdown 2.0

# Simulate exact replay without hardware
./BitBangUtility.py --filesRaw capture.sr --channel RX --simulate
```

### Message Extraction Only

Use the stand-alone utility to extract and display messages from captures:

```bash
# Extract messages from capture files
python3 SigrokUtil.py capture1.sr capture2.sr
```

## Command-Line Options

### BitBangUtility.py

| Option | Description |
|--------|-------------|
| `--message STRING` | Single IEBus message to transmit |
| `--files FILE [FILE ...]` | Sigrok captures to process with protocol decoding |
| `--filesRaw FILE [FILE ...]` | Raw Sigrok captures for exact replay |
| `--simulate` | Print bit sequence instead of transmitting |
| `--slowdown FLOAT` | Speed multiplier (2.0 = half speed, 0.5 = double speed) |
| `--glitch INT` | Number of leading "1" bits for robustness testing |
| `--regular INT` | Fixed interval in bit times between replayed messages |
| `--channel STRING` | Channel name to process from Sigrok files (default: RX) |

### SigrokUtil.py

```bash
python3 SigrokUtil.py <capture_files...>
```

Extracts and displays IEBus messages from Sigrok capture files.

## Use Cases

### Decoder Validation

Generate known-good test vectors for your IEBus decoder:

```bash
# Test basic message parsing
./BitBangUtility.py --message "- 190 1d0 f 2 60 01"

# Test broadcast handling
./BitBangUtility.py --message "B 1ff 000 f 1 45"
```

### Edge Case Testing

Test decoder robustness with glitch injection:

```bash
# Add leading glitch bits
./BitBangUtility.py --message "- 190 1d0 f 2 60 01" --glitch 100
```

### Timing Debug

Slow down signals to debug timing-sensitive code:

```bash
# Half-speed transmission
./BitBangUtility.py --filesRaw capture.sr --slowdown 2.0
```

### Regression Testing

Replay captured bus traffic to ensure decoder consistency:

```bash
# Replay exact capture
./BitBangUtility.py --filesRaw production_capture.sr
```

## IEBus Message Structure

Each IEBus message consists of:

```
[Start Bit] [Broadcast] [Master Addr + Parity + ACK] [Slave Addr + Parity + ACK]
[Control + Parity + ACK] [Length + Parity + ACK] [Data Bytes + Parity + ACK] ...
```

- **Broadcast**: 1 bit (1 = broadcast, 0 = unicast)
- **Master Address**: 12 bits + parity + ACK
- **Slave Address**: 12 bits + parity + ACK
- **Control**: 4 bits + parity + ACK
- **Length**: 8 bits + parity + ACK (number of data bytes)
- **Data**: N × (8 bits + parity + ACK)

**Timing**: 1MHz bit rate, T_Bit = 40.7μs

**Parity**: Odd parity across data bits

## Architecture

- **IEBusMessage.py** - Message parsing, construction, and validation
- **IEBusBitBang.py** - Bit sequence generation and timing
- **SPIBitBang.py** - Hardware interface via SPI
- **SigrokUtil.py** - Logic analyzer capture processing
- **BitBangUtility.py** - Main command-line utility

## Troubleshooting

### SPI Permission Denied

Add your user to the `spi` group:
```bash
sudo usermod -a -G spi $USER
# Log out and back in
```

### Sigrok Not Found

Install Sigrok:
```bash
sudo apt-get install sigrok-cli
```

### Wrong Baud Rate

The bit-bang timing is calibrated for 1MHz IEBus. If signals appear incorrect, verify:
- SPI clock configuration
- Hardware connections
- Logic analyzer sample rate (should be ≥10MHz)

## Contributing

This is a specialized tool for IEBus development. When contributing:
- Preserve backward compatibility with existing message formats
- Test against real hardware captures
- Document protocol deviations or extensions

## License

See repository for license information.

## References

- IEBus Protocol Specification
- Toyota/Lexus automotive bus documentation
- Sigrok Protocol Decoder Documentation
