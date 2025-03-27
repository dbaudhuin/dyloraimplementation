#!/usr/bin/env python3
import time
import serial
import argparse
from datetime import datetime

from serial.threaded import LineReader, ReaderThread

# Updated argument parser to include iterations
parser = argparse.ArgumentParser(description='LoRa Radio mode sender.')
parser.add_argument('--port', default='/dev/ttyUSB0', help="Serial port descriptor")
parser.add_argument('--interval', type=int, default=2, help="Interval between transmissions in seconds")
parser.add_argument('--iterations', type=int, default=100, help="Number of iterations for all combinations")
args = parser.parse_args()

# Define parameter ranges
SFs = ['sf7', 'sf8', 'sf9', 'sf10']
CRs = ['4/5', '4/7', '4/8']
CFs = [903.9, 904.1, 904.3, 904.5, 904.7, 904.9, 905.1, 905.3]  

TXPowers = [5, 10, 15, 20]  
PL= [60, 120, 180, 240] 
NODE_ID = 1
GATEWAY_ID = 0
SENT_SUCESS =0

#Time to generate distinct output file names
filetime = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
filetime = filetime.replace(':', '.') #Some OS do not support ':' in file name declaration
filename = f"{filetime[0:10]}_{filetime[11:19]}.csv"


def make_pack(source, destination, sequence_number, frequency, spreading_factor, power, crc, reset):
    first_byte = (source << 4) | destination
    sequence_bytes = sequence_number.to_bytes(2, byteorder='big')
    fourth_byte = (frequency << 5) | (spreading_factor << 2) | power
    


    fifth_byte = (crc << 6) | (63 if reset else 0)
    packet = bytes([first_byte] + list(sequence_bytes) + [fourth_byte, fifth_byte])
    return packet.hex()




class PrintLines(LineReader):
    def connection_made(self, transport):
        super(PrintLines, self).connection_made(transport)
        print("connection made")
        self.transport = transport

    def handle_line(self, data):
        if data == "ok":
            return
        print(f"RECV: {data}")

    def connection_lost(self, exc):
        if exc:
            print(exc)
        print("port closed")

    def send_cmd(self, cmd, delay=0.5):
        print(f"SEND: {cmd}")
        self.write_line(cmd)
        time.sleep(delay)
        
def run_transmissions(protocol):
    frame_count = 0
    is_beginning = True  # flag to control the initial setup
    sf = 0
    cr = 0
    cf = 0
    pw = 0
    
    protocol.send_cmd("sys set pindig GPIO10 1")
    protocol.send_cmd("sys set pindig GPIO11 0")
    
    for iteration in range(args.iterations):
        print(f"Starting iteration {iteration + 1}")
        
        if is_beginning:  # Initial parameter setup based on NODE_ID
            if NODE_ID < 8:  # For NODE_ID 1 to 7
                cf = NODE_ID - 1  # Set frequency index to NODE_ID - 1
            else:  # For NODE_ID 8 to 11
                cf = NODE_ID % 8  # Start at frequency index 0
                sf = 2  # Start at SF indices 0 to 3
                
            is_beginning = False  # Reset flag after initial setup

        for SF in SFs[sf:]+SFs[:sf]:  # Rotate list to start from the NODE's SF
            protocol.send_cmd(f'radio set sf {SF}')
            protocol.send_cmd(f'radio get sf')
            time.sleep(1)
            
            for CR in CRs:
                protocol.send_cmd(f'radio set cr {CR}')
                protocol.send_cmd(f'radio get cr')
                time.sleep(1)
                
                for CF in CFs[cf:]+CFs[:cf]:  # Rotate list to start from the NODE'S CF
                    protocol.send_cmd(f'radio set freq {int(CF * 1e6)}')
                    protocol.send_cmd(f'radio get freq')
                    time.sleep(1)
                    
                    for TXPower in TXPowers:
                        protocol.send_cmd(f'radio set pwr {TXPower}')
                        protocol.send_cmd(f'radio get pwr')
                        protocol.send_cmd('mac pause')
                        time.sleep(1)  # Wait for the radio to configure
                        
                        for paysize in PL:
                            protocol.send_cmd("sys set pindig GPIO11 1")
                            payload = make_pack(NODE_ID, GATEWAY_ID, frame_count, cf, sf, pw, cr, False)
                            new_payload = f'{payload}'.ljust(paysize, '0')
                            protocol.send_cmd(f'radio tx {new_payload}')
                            timestamp = datetime.utcnow()
                            frame_count = (frame_count + 1) % 65536
                            time.sleep(2)
                            protocol.send_cmd("sys set pindig GPIO11 0")
                            print(SFs[sf])
                            with open(f'{filename}', 'a') as file:
                                file.write(f'{NODE_ID},{timestamp},{CF},{SF},{CR},{TXPower},{new_payload}\r\n')
                            
                        pw = (pw + 1) % 4
                    cf = (cf + 1) % 8
                cr = (cr + 1) % 3
            
            sf = (sf + 1) % 4
         
            	

def main():
    ser = serial.Serial(args.port, baudrate=57600)
    with open(f'{filename}', 'a') as file:
        file.write(f'NodeID,Time,Frequency,Spreading Factor,CRC Rate,Power,Payload')
        file.write('\n')
    with ReaderThread(ser, PrintLines) as protocol:
        run_transmissions(protocol)
        #time.sleep(10)

if __name__ == "__main__":
    # print(datetime.utcnow())
    time.sleep(10)
    main()
