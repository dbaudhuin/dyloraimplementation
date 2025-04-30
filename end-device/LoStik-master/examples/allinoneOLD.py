#!/usr/bin/env python3
# filepath: /home/dbaudhuin/Documents/Code/dyloraimplementation/pi/LoStik-master/examples/aakash/LoStik/examples/allinoneIP.py
import time
import serial
import argparse
import threading
import binascii
from datetime import datetime

from serial.threaded import LineReader, ReaderThread

# Parse command-line arguments
parser = argparse.ArgumentParser(description='LoRa Radio node with automatic parameter adaptation.')
parser.add_argument('--port', default='/dev/ttyUSB0', help="Serial port descriptor")
parser.add_argument('--interval', type=int, default=5, help="Interval between transmissions in seconds")
parser.add_argument('--node-id', type=int, default=10, help="Node ID (1-15)")
args = parser.parse_args()

# Constants
NODE_ID = args.node_id
GATEWAY_ID = 0
PACKET_SIZE = 60  # Base packet size
MAX_RETRIES = 3   # Maximum retries before considering gateway unreachable

# Define parameter ranges and mappings
SF_VALUES = {
    7: 'sf7',
    8: 'sf8',
    9: 'sf9',
    10: 'sf10',
    11: 'sf11',
    12: 'sf12'
}

TP_VALUES = [5, 10, 15, 20]
CRs = ['4/5', '4/6', '4/7', '4/8']
CF = 904.1  # Use a fixed center frequency of 904.1 MHz

# Create a log file name
current_time = datetime.utcnow().strftime("%Y-%m-%d_%H.%M.%S")
log_filename = f"node_{NODE_ID}_{current_time}.csv"

# Node state variables
current_sf = 12
current_tp = 20
sequence_number = 0
last_ack_sequence = -1
ack_received = True
retries = 0
tx_lock = threading.Lock()  # Lock to prevent concurrent radio transmissions

# Create and initialize the log file
with open(log_filename, 'w') as log_file:
    log_file.write("timestamp,tx_sequence,rx_sequence,sf,tp,ack_received,retry_count,command\n")

def log_event(tx_seq=None, rx_seq=None, ack=None, retry_count=None, command=None):
    with open(log_filename, 'a') as log_file:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        tx_seq_str = str(tx_seq) if tx_seq is not None else ""
        rx_seq_str = str(rx_seq) if rx_seq is not None else ""
        ack_str = str(ack) if ack is not None else ""
        retries_str = str(retry_count) if retry_count is not None else ""
        command_str = str(command) if command is not None else ""
        
        log_file.write(f"{timestamp},{tx_seq_str},{rx_seq_str},{current_sf},{current_tp},{ack_str},{retries_str},{command_str}\n")

# Create packet with proper format for DyLoRa implementation
def make_packet(sequence_number, reset=False):
    payload_size = PACKET_SIZE - 5
    
    first_byte = (NODE_ID << 4) | GATEWAY_ID
    sequence_bytes = sequence_number.to_bytes(2, byteorder='big')
    
    # SF and TP encoding in fourth byte
    sf_idx = 5
    for i, sf in enumerate([7, 8, 9, 10, 11, 12]):
        if sf == current_sf:
            sf_idx = i
            break
    tp_idx = 3 
    for i, tp in enumerate([5, 10, 15, 20]):
        if tp == current_tp:
            tp_idx = i
            break
    
    frequency_idx = 0
    fourth_byte = (frequency_idx << 5) | (sf_idx << 2) | tp_idx
    crc_idx = 0
    fifth_byte = (crc_idx << 6) | (63 if reset else 0)
    
    packet = bytes([first_byte] + list(sequence_bytes) + [fourth_byte, fifth_byte]) + b'\x00' * payload_size
    return binascii.hexlify(packet).decode('ascii').upper()

class LoRaHandler(LineReader):
    def connection_made(self, transport):
        print("Connection established to LoRa module")
        self.transport = transport
        self.send_cmd('sys get ver')
        
        self.send_cmd('mac pause')
        time.sleep(.2)
        # Set radio parameters safely!
        self.send_cmd(f'radio set sf sf12')
        self.send_cmd(f'radio set pwr 20')
        self.send_cmd(f'radio set freq {int(CF * 1e6)}')
        self.send_cmd(f'radio set cr {CRs[0]}')
        self.send_cmd(f'radio get prlen')
        self.send_cmd('sys set pindig GPIO10 1')
        self.send_cmd('sys set pindig GPIO11 0')
        
        self.send_cmd('radio rx 0') # set to receive mode
        time.sleep(.2)
        self.send_cmd('mac resume')
        time.sleep(1)


    def handle_line(self, data):
        global current_sf, current_tp, ack_received, last_ack_sequence, retries
        print(f"RECV: {data}")

        if data == "ok" or data == 'busy':
            return
            
        if data == "radio_err":
            # If we're not transmitting, restart receive mode
            if not tx_lock.locked():
                # self.send_cmd('mac pause')
                # time.sleep(.2)
                self.send_cmd('radio rx 0')
                time.sleep(.2)
                # self.send_cmd('mac resume')
                # time.sleep(1)
            return
            
        if data.startswith("radio_rx"):
            try:
                print("RECV: %s!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" % data)
                hex_data = data.split(" ")[1]
                binary_data = binascii.unhexlify(hex_data)
                
                self.send_cmd("sys set pindig GPIO10 0", delay=0)
                self.send_cmd("sys set pindig GPIO10 1", delay=0)
                
                if len(binary_data) >= 6: # if the size of a command packet
                    if binary_data[0] == 0xAA: # if its a command packet
                        new_sf = binary_data[1]
                        new_tp = binary_data[2]
                        target_node = binary_data[3] & 0x0F
                        seq_number = binary_data[4] | (binary_data[5] << 8)
                        
                        if target_node == NODE_ID: # is it ours?
                            if 7 <= new_sf <= 12:
                                current_sf = new_sf
                            if new_tp in TP_VALUES:
                                current_tp = new_tp
                            print(f"Received command: SF={new_sf}, TP={new_tp}, Target={target_node}, Seq={seq_number}")
                                
                            # since its ours we want to note we got an ack
                            # TODO: check if the seq number is the same as the last one we sent
                            if seq_number == last_ack_sequence:
                                ack_received = True
                                last_ack_sequence = seq_number
                                retries = 0
                            
                            log_event(rx_seq=seq_number, ack=ack_received, command="UPDATE")
                            # TODO: actually send commands to change the parameters.
                            print(f"Parameters updated: SF={current_sf}, TP={current_tp}")
                    
                    elif binary_data[0] == 0xFF: # ack only
                        target_node = binary_data[3] & 0x0F
                        seq_number = binary_data[4] | (binary_data[5] << 8)
                        
                        print(f"Received ACK for sequence {seq_number}, Target={target_node}")
                        
                        # Verify this ack is for us
                        if target_node == NODE_ID:
                            ack_received = True
                            last_ack_sequence = seq_number
                            retries = 0
                            
                            log_event(rx_seq=seq_number, ack=True, command="ACK")
            
            except Exception as e:
                print(f"Error processing received data: {e}")
            finally:
                if not tx_lock.locked():
                    self.send_cmd('radio rx 0')
        else:
            print(f"RECV: {data}")

    def connection_lost(self, exc):
        print("Connection to LoRa module lost")
        if exc:
            print(f"Error: {exc}")

    def send_cmd(self, cmd, delay=0.5):
        print(f"SEND: {cmd}")
        self.write_line(cmd)
        time.sleep(delay)

def transmit_thread(protocol):
    global sequence_number, ack_received, retries
    
    print("Transmit thread started")
    time.sleep(2)
    
    while True:
        with tx_lock: # stops receive command conflicts
            if not ack_received: # retransmit?
                print(f"Retransmitting packet sequence {sequence_number}, retry {retries}")
                # We would retransmit here but the data is fake so it doesnt matter
                retries += 1
            
            if ack_received:
                sequence_number = (sequence_number + 1) % 65536
                ack_received = False
                retries = 0
            
            # Configure radio parameters
            sf_str = SF_VALUES.get(current_sf, 'sf12')
            protocol.send_cmd('mac pause') # apparently dont do this
            time.sleep(.2)
            protocol.send_cmd(f'radio set sf {sf_str}')
            protocol.send_cmd(f'radio set freq {int(CF * 1e6)}')
            protocol.send_cmd(f'radio set pwr {current_tp}')
            protocol.send_cmd(f'radio set cr {CRs[0]}')  # Use 4/5 coding rate really only (this is what the paper did).
            protocol.send_cmd('radio rx 1') # Ensure we are able to transmit
            time.sleep(.2)
            # protocol.send_cmd('mac resume')

            # Create and send packet
            # protocol.send_cmd('mac pause') 

            payload = make_packet(sequence_number)
            protocol.send_cmd('sys set pindig GPIO11 1')
            protocol.send_cmd(f'radio tx {payload}')
            time.sleep(2) # Plenty of time
            log_event(tx_seq=sequence_number, retry_count=retries)
            print(f"Sent packet with sequence {sequence_number}, SF={current_sf}, TP={current_tp}")
            protocol.send_cmd('sys set pindig GPIO11 0')        
            protocol.send_cmd('radio rx 0') # receive mode
            time.sleep(.2)
            protocol.send_cmd('mac resume')
        
        # Can be configured launch arguments or changing the default.
        time.sleep(args.interval)

def main():
    print(f"Starting LoRa node with ID: {NODE_ID}")
    print(f"Initial parameters: SF={current_sf}, TP={current_tp}")
    print(f"Logging to file: {log_filename}")
    
    try:
        ser = serial.Serial(args.port, baudrate=57600)
        
        with ReaderThread(ser, LoRaHandler) as protocol:
            tx_thread = threading.Thread(target=transmit_thread, args=(protocol,), daemon=True)
            tx_thread.start()
            
            while True:
                time.sleep(1)
            
    except KeyboardInterrupt:
        print("Program terminated by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Shutting down LoRa node")
        
if __name__ == "__main__":
    main()