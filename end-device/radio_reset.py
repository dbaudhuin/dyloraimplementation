#!/usr/bin/env python3
# filepath: /home/dbaudhuin/Documents/Code/dyloraimplementation/reset_lora.py
import serial
import time

# Configure the serial port
PORT = '/dev/ttyUSB0'  # Update if using a different port
BAUDRATE = 57600


def send_cmd(ser, cmd, delay=0.5):
    """Send a command to the RN2903 module."""
    ser.write((cmd + '\r\n').encode())
    time.sleep(delay)
    response = ser.read(ser.in_waiting).decode(errors='ignore')
    print(f"CMD: {cmd} -> {response.strip()}")


def reset_lora_module():
    """Reset and reconfigure the RN2903 module."""
    try:
        # Open serial connection
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
        time.sleep(1)

        # Reset and reinitialize the module
        send_cmd(ser, 'sys reset', delay=1.5)
        send_cmd(ser, 'mac pause')
        send_cmd(ser, 'radio set sf sf12')  # Set spreading factor to SF12
        send_cmd(ser, 'radio set pwr 20')  # Set power to 20 dBm
        send_cmd(ser, 'radio set freq 904100000')  # Set frequency to 904.1 MHz
        send_cmd(ser, 'radio set cr 4/5')  # Set coding rate to 4/5
        send_cmd(ser, 'radio rx 0')  # Return to RX mode

        print("RN2903 module reset and reconfigured successfully.")
        ser.close()

    except Exception as e:
        print(f"Error resetting module: {e}")


if __name__ == "__main__":
    reset_lora_module()
