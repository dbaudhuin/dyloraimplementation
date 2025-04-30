#!/usr/bin/env python3
import time
import serial
import argparse
from datetime import datetime
import threading

from serial.threaded import LineReader, ReaderThread

# Updated argument parser to include iterations
parser = argparse.ArgumentParser(description='LoRa Radio mode sender.')
parser.add_argument('--port', default='/dev/ttyUSB0', help="Serial port descriptor")
parser.add_argument('--interval', type=int, default=2, help="Interval between transmissions in seconds")
parser.add_argument('--iterations', type=int, default=100000000000000000000000000000000000, help="Number of iterations for all combinations")
args = parser.parse_args()

# Define parameter ranges
SFs = ['sf7', 'sf8', 'sf9', 'sf10', 'sf11', 'sf12']
CRs = ['4/5', '4/7', '4/8']
CFs = [904.1, 904.1, 904.1, 904.1, 904.1, 904.1, 904.1, 904.1]  

TXPowers = [5, 10, 15, 20]  
PL= [60, 120, 180, 240] 
NODE_ID = 10
GATEWAY_ID = 0
SENT_SUCESS = 0
lock = threading.Lock()

#Time to generate distinct output file names
filetime = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
filetime = filetime.replace(':', '.') #Some OS do not support ':' in file name declaration
filename = f"{filetime[0:10]}_{filetime[11:19]}.csv"

initial_sf = 3 # sf10


def make_pack(source, destination, sequence_number, frequency, spreading_factor, power, crc, reset):
    first_byte = (source << 4) | destination
    sequence_bytes = sequence_number.to_bytes(2, byteorder='big')
    fourth_byte = (frequency << 5) | (spreading_factor << 2) | power
    print("spreading factor: ", spreading_factor)
    


    fifth_byte = (crc << 6) | (63 if reset else 0)
    packet = bytes([first_byte] + list(sequence_bytes) + [fourth_byte, fifth_byte])
    return packet.hex()




class PrintLines(LineReader):
    def __init__(self):
        super().__init__()
        self.tx_ok_event = threading.Event()
        self.rx_ok_event = threading.Event()
        
    def connection_made(self, transport):
        super(PrintLines, self).connection_made(transport)
        print("connection made")
        self.transport = transport

        


    def handle_line(self, data):
        
        # if data == "ok":
        #     return
        # print(f"RECV: {data}")
        
        data = data.strip()
        
        if data == "radio_tx_ok":
            print("Transmission successful.")
            self.tx_ok_event.set()
            return


        # Once data recieved we need to make sure its ours
        # Then once its ours, we need to see if the ack is
        # what we expect, and if its not, theres a big issue pal.
        
        # If the ack is correct, we say the message has been acked
        # and then we can move on to the next message and set a variable
        # to say we have been acked.
        
        # If the ack is not correct, we need to resend the message
        # and wait for the ack again.
        
        if data.startswith("radio_rx"):
            print(f"RECV: {data}")
            self.rx_ok_event.set()
            # interpret_pack(data)
            return
        
        if data == "ok":
            return
        
        print(f"RECV: {data}")
        

        time.sleep(.1)
        if data.startswith("radio_tx"):
            time.sleep(.1)
            self.send_cmd("mac pause")
            self.send_cmd('radio rx 0')



    def connection_lost(self, exc):
        if exc:
            print(exc)
        print("port closed")

    def send_cmd(self, cmd, delay=0.5):
        print(f"SEND: {cmd}")
        self.write_line(cmd)
        time.sleep(delay)

def interpret_pack(data):
    first_byte = data[0]
    source = (first_byte >> 4) & 0x0F
    destination = first_byte & 0x0F
    sequence_number = int.from_bytes(data[1:3], byteorder='big')
    # Check and if this is the ack we expect, set the acked variable to true
    frequency = (data[3] >> 5) & 0x07
    spreading_factor = (data[3] >> 2) & 0x07
    power = data[3] & 0x03
    crc = (data[4] >> 6) & 0x03
    reset = (data[4] >> 5) & 0x01
    
    # Take spreading factor and TP set the radio
    
    # Print radio settings to confirm

    return
        
def run_transmissions(protocol):
    frame_count = 0
    sf = initial_sf
    cr = 0
    cf = 0
    pw = 0
    
    #Make the initial settings establish here.
    protocol.send_cmd(f'radio set sf sf10', delay=1)
    protocol.send_cmd(f'radio set cr 4/5', delay=1)
    protocol.send_cmd(f'radio set freq {int(904.1 * 1e6)}', delay=1)
    # protocol.send_cmd(f'radio set freq {int(904.3 * 1e6)}', delay=1)
    # protocol.send_cmd(f'radio set freq {int(904.9 * 1e6)}', delay=1)

    protocol.send_cmd(f'radio set pwr 20', delay=1)
    protocol.send_cmd('radio set bw 125', delay=1)
    
    total_sent = 0
    total_rx_confirmed = 0


    
    for iteration in range(args.iterations):
        # Check to see if weve been acked or not yet, if we havent yet resend.
        print(f"Starting iteration {iteration + 1}")
        

        # # protocol.send_cmd(f'radio set sf sf10', delay=1)
        # protocol.send_cmd(f'radio get sf')
        
        # # protocol.send_cmd(f'radio set cr 4/5', delay=1)
        # protocol.send_cmd(f'radio get cr')
            
        # # protocol.send_cmd(f'radio set freq {int(904.1 * 1e6)}', delay=1)
        # protocol.send_cmd(f'radio get freq')
                
        # # protocol.send_cmd(f'radio set pwr 20', delay=1)
        # protocol.send_cmd(f'radio get pwr')
        
        # # protocol.send_cmd('radio set bw 125', delay=1)
        # protocol.send_cmd('radio get bw', delay=1)
        
        # here we may want to change sf to what we are set to (what we got from the server response)
        
        frame_count = (frame_count + 1) % 65536
        payload = make_pack(NODE_ID, GATEWAY_ID, frame_count, cf, sf, pw, cr, False)
        new_payload = f'{payload}'.ljust(60, '0')
        # protocol.send_cmd(f' radio rxstop')

        # time.sleep(2.5)
        # protocol.send_cmd("mac pause")
        protocol.send_cmd(f'radio tx {new_payload}')
        
        # time.sleep(2)
        if protocol.tx_ok_event.wait(timeout=2):
            print("TX confirmed; going to RX mode.")
            protocol.tx_ok_event.clear()
            protocol.send_cmd("radio rx 0")
            total_sent += 1
        else:
            print("TX confirmation not received!")
            # protocol.send_cmd(f'radio tx 0')
            
            
        flag = False
            
        if protocol.rx_ok_event.wait(timeout=10):
            print("RX confirmed")
            protocol.rx_ok_event.clear()
            total_rx_confirmed += 1
        else:
            print("RX confirmation not received!")
        time.sleep(5)
            

        time.sleep(5) # extend interval and mess with frequencies (on node) (With and without venv)

        # protocol.send_cmd("mac pause")
        print(f"{total_rx_confirmed} Rx confirmations out of {total_sent} packets sent.\n")

        timestamp = datetime.utcnow()
            
        
            	

def main():
    ser = serial.Serial(args.port, baudrate=57600)
    with open(f'{filename}', 'a') as file:
        file.write(f'NodeID,Time,Frequency,Spreading Factor,CRC Rate,Power,Payload')
        file.write('\n')
    with ReaderThread(ser, PrintLines) as protocol:
        run_transmissions(protocol)

if __name__ == "__main__":
    time.sleep(10)
    main()
