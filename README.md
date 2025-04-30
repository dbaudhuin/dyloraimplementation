# S25-DyLoRa-Dylan
# Raspberry Pi End Devices and Gateway Setup Guide

## Assumed Starting Position
When beginning, it is assumed that the devices (gateway and end-devices) are booted with some version of Arch Linux. Initially, these need to be physically accessible; however, we are setting up remote access via SSH. The process is identical for all devices (gateway and end-devices) unless noted with: ⚠️

## Required Materials
- Monitor (Initial Setup)
- HDMI Cable (Initial Setup)
- Keyboard (Initial Setup)
- Raspberry Pi Devices (End Nodes and Gateway)
- Host Machine to access the devices
- WiFi Hotspot (a network with SSH permitted)
- SSH key and its location


## Initial Device Access and WiFi Setup
1. Connect the Raspberry Pi to a Monitor and Keyboard:
   - If the device is already booted when you connect the peripherals, you may need to restart it for them to be detected.
2. Adding Personal Hotspot Credentials to Raspberry Pi:
   - Navigate to `/etc/wpa_supplicant`
   - Run `sudo nano wpa_supplicant.conf` to open a text editor
   - Add the wifi credentials in the same format as below (They don't need to be these example ones; however, they already should have this configured. If you configure your hotspot with these credentials, it should automatically connect):
   ```
   network={
	   ssid="AndesHS"
	   psk="andes_password123"
   }
   ```
   - Restart the device by running `sudo reboot now`

Now that the device is connected to the internet, we can connect to the device and locate its IP address.

3. Access the device's IP address by running `hostname -I` on the device. Its IPv4 address will be what is used to access it (IPv4 addresses look like this: `192.168.10.0`. We are not using the IPv6 address that may look like this: `ffff:ffff:ffff::fff:ffff`).
4. Transferring SSH Key from Host Machine to Raspberry Pi (If you have altered the save location of the SSH key, you may need to update the directory locations in the commands below).
   - Connect the Host Machine to the same network as the device.
   - Linux/MacOS: Run `ssh-copy-id {DEVICES USERNAME}@{DEVICES IP ADDRESS}`
   - Windows: Run `Get-Content {PATH TO YOUR PROFILE}\.ssh\id_rsa.pub | ssh {DEVICES USERNAME}@{DEVICES IP ADDRESS} "mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"` to retrieve the details of your public SSH key, and then pipe it into a command to add your ssh key into the devices saved keys. This will require the device's username and password (REFERENCE MATERIAL 1).
   - If not already remoted into the device, run `ssh {DEVICES USERNAME}@{DEVICES IP ADDRESS}` to confirm remote access.
     - If this does not work, restart the device by running `sudo reboot now` and attempt to run `ssh {DEVICES USERNAME}@{DEVICES IP ADDRESS}` again.

## Running Gateway LoRa Packet Logger:
There are four different programs that all share the same process. To view and edit code related to packet logging, navigate to `gateway/{Desired Packet Logger}/util_pkt_logger/src/` to find `util_pkt_logger.c.`
- Original Utility Packet Logger `lora_gateway-master`: Logs received packets and outputs the number of received packets once it is closed with `CTRL + C`. The program is not intended to output anything during execution, even while receiving packets. This version is not recommended because it contains the default configuration file.
- Modified Utility Packet Logger `modified-lora_gateway-master`: The same as the Original; however, the configuration is changed to use 904.3 as its central frequency. This version is recommended for the "vanilla" packet logger.
- Luis's Utility Packet Logger `luis-gateway`: Serves the same functionality as the Original; however, it breaks each packet down and interprets it using `allinone.py`'s packet structure. When interpreted, the results are printed.
- Dylan's Utility Packet Logger `dylan-gateway`: An extension of Luis's implementation where dylora is invoked. Here, whenever the gateway recognizes a packet with its GATEWAYID at the beginning, it will run this packet through the dylora algorithm, display its progress, and respond with an update/ack packet.

1. Navigate to `gateway/{Desired Packet Logger}/`
2. Run `make clean`
3. Navigate to `gateway/{Desired Packet Logger}/util_pkt_logger/`
4. Run `make`
5. Execute the packet logger with `./util_pkt_logger`

## Running End-Devices:
There are three different programs to transmit packets from an end-device. Two of them are developed by Aakaash and Dylan respectively (`allinone.py`, `allinoneWIP.py`), while the Original (`radio_sender.py`) is provided with the LoStik. They are fundamentally the same; however, they transmit packets differently; additionally, the functionality added to allinoneWIP.py is specific to dylora. There is also a program to enable the end-devices to receive transmissions called `radio_receiver.py`. To view and edit their code, navigate to `end-device/LoStik-master/examples` to find `allinone.py`, `allinoneWIP.py`, `radio_sender.py`, and `radio_receiver.py`. All programs establish their transmission parameters in the `PrintLines` class's `connection_made` function.
- Original Radio Sender `radio_sender.py`: Sends the current time and frame count in a fixed-length message every 10 seconds.
- Aakaash's Ground Truth Sender `allinone.py`: Alternates between transmission parameters to send a wide variety of packets that include these parameters, as well as Node/Gateway identification data. The parameters that change throughout execution are SF, TP, CRC, and payload size. To run this program, you must pass the port the LoStik is connected to as an argument (REFERENCE MATERIAL 2), and you may also establish the interval between packets and the number of packets sent in total. When deploying and using this program, ensure that you change the `NODE_ID` definition at the top of the program to differentiate it from other end-devices that may also be transmitting.
- Dylan's Dylora Sender `allinoneWIP.py`:

## **REFERENCE MATERIAL**
1. Usernames and Passwords:
   - end-device username: pi
   - end-device password: password
   - gateway username: pi
   - gateway password: gateway_password
  
2. How to view connected USB devices to locate the LoStik:
   - Navigate to `/dev/`
   - Run `ls` to list everything in the directory and locate any files that begin with "ttyUSB".
   - (If you are doing this to run the end-device radio transmission programs) Anything labeled with "ttyUSB" has the possibility of being the LoStik, so attempt them all until a connection is made with the radio

3. Hardware in use:
   - Gateway: SX1301 radio chip (used for documentation) wrapped up in the RAK 7243 D3.
Store Page: https://store.rakwireless.com/products/rak7243c-pilot-gateway?variant=39942876168390
   - End-Device: RN2903 radio chip on the LoStik USB radio.
Store Page: https://ronoth.com/products/lostik

The documentation for both can be found in the "Documentation" folder.

4. Accessing device IP addresses without physical access:
   - Connect the Host Machine to the same network as the devices
   - Locate the Host Machine's IP address by running `hostname -I`
   - Use the nmap command to scan the network using the Host Machine's IP address as a mask by running `nmap -sn {INSERT FIRST 3 GROUPS OF NUMBERS}.0/24`
   - Attempt to SSH into each IP address using `ssh {DEVICES USERNAME}@{DEVICES IP ADDRESS}`
  
5. File transfer using rsync:
To transfer files to and from the Host Machine and deployed devices, they must first be connected to the same network. Once this is satisfied, you can run `rsync -avz {TARGET DIRECTORY} {DEVICES USERNAME}@{DEVICES IP ADDRESS}:{DESTINATION DIRECTORY}` to transfer the folder from the target directory to the destination directory.

7. Ensuring settings are the same across the transmitter and receiver to establish a connection:
Both the sender and receiver need to have a common:
   - SF (spreading factor)
   - CRC (coding rate)
   - CF (central frequency or just frequency)
   - BW (bandwidth)
  
These can be configured for end-devices in the radio commands sent when a connection between the device and its radio is established (typically in the `PrintLines` class's `connection_made` function).

For the gateway, the configuration file must be edited to change its operating CF and BW. **AS OF RIGHT NOW I DONT KNOW HOW TO EDIT THE GATEWAYS CRC, BW, OR CF.**
