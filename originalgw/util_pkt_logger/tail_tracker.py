#!/usr/bin/python3

import time, subprocess, select, sys, os, csv, requests, threading, glob

from datetime import datetime
from datetime import timedelta

star_duration = timedelta(seconds = 5)
notif_threshold = timedelta(minutes = 30)
node_min = 1
node_max = 14
bot_token = '7009016075:AAE2TDUZsNCa1rXLaSMguhuMJQRfXWBa9-k'
chat_id = "-4165692264"

receive_times = {}
nodes_down = set()
log_times = []
ping_count = 0
current_filename = None
current_file = None
tracking_busy = False

recv_now = datetime.utcnow()
for n in range(node_min, node_max + 1):
    receive_times[n] = recv_now

def send_message(message):
    try:
        print(f"SENDING: {message}")
        requests.get(f'https://api.telegram.org/bot{bot_token}/sendMessage', params = { 'chat_id': chat_id, 'text': message })
    except Exception as e:
        print("Failed to send request")
        print(e)

send_message("Tracker was restarted")

def track_csv(is_startup):
    global current_filename, current_file, tracking_busy, ping_count
    tracking_busy = True
    current_ctime = 0
    if current_filename:
        current_time = os.path.getctime(current_filename)
    next_filename = current_filename
    for filename in glob.glob("*.csv"):
        if os.path.getctime(filename) > current_ctime:
            next_filename = filename
            current_ctime = os.path.getctime(filename)
    if next_filename != current_filename:
        current_filename = next_filename
        if current_file:
            current_file.close()
        if not is_startup:
            send_message(f"Logger was restarted")
        print("OPENING")
        current_file = open(current_filename, "r")
        print("READING")
        ping_count += len(current_file.readlines()) - 1
        current_file.seek(0, os.SEEK_END)
        print("DONE")
    tracking_busy = False


def follow(file, timestep = 0.1):
    line = ''
    while True:
        if tracking_busy:
            time.sleep(timestep)
            continue
        try:
            tmp = file.readline()
        except ValueError as e:
            return
        if tmp is not None and tmp != '':
            line += tmp
            if line.endswith("\n"):
                yield line
            line = ''
        else:
            time.sleep(timestep)

track_csv(True)

def thread_csv():
    while True:
        time.sleep(15)
        track_csv(False)

track_thread = threading.Thread(target=thread_csv)
track_thread.start()

def create_stars(duration):
    star_types = ['⡀', '⣀', '⣄', '⣤', '⣦', '⣶', '⣷', '⣿']
    ret = ''
    while len(ret) < 60:
        if len(star_types) * star_duration <= duration:
            duration -= len(star_types) * star_duration
            ret += star_types[-1]
        else:
            ret += star_types[duration // star_duration]
            break
    else:
        ret += "+"
    return ret

while True:
    print("TAILING")
    for line in follow(current_file):
        ping_count += 1
        r = list(csv.reader([line]))[0]
        if len(r) != 16:
            continue
        node = int(r[15][:2][::-1],16)
        crc_ok = r[7].strip() == "CRC_OK"
        recv_time = datetime.strptime(r[2], "%Y-%m-%d %H:%M:%S.%fZ")
        log_times.append(recv_time)
        while len(log_times) != 0:
            if recv_time - log_times[0] > timedelta(minutes = 15):
                log_times.pop(0)
            else:
                break
        print("----")
        if not crc_ok:
            print("CRC BAD")
            print(*r, sep=' ')
            print("----")
        elif node > node_max or node < node_min:
            print(f"INVALID NODE: {node}")
            print(*r, sep=' ')
            print("----")
        else:
            receive_times[node] = recv_time

        for node,node_time in receive_times.items():
            duration = recv_time - node_time
            if duration > notif_threshold:
                if node not in nodes_down:
                    nodes_down.add(node)
                    send_message(f"Node {node} is down")
            else:
                if node in nodes_down:
                    nodes_down.remove(node)
                    send_message(f"Node {node} is back up")

        for node,node_time in sorted(receive_times.items()):
            duration = recv_time - node_time
            print(str(node).rjust(2, ' '), duration, create_stars(duration))

        last_15 = len(log_times) / 15
        last_5 = sum([(recv_time - n) <= timedelta(minutes = 5) for n in log_times]) / 5
        last_1 = sum([(recv_time - n) <= timedelta(minutes = 1) for n in log_times]) / 1
        print(f"Packets/min of last 1 min: {last_1:.2f}; 5 min: {last_5:.2f}; 15 min: {last_15:.2f}")
        print(f"TOTAL: {ping_count}", flush=True)
