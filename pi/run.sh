#!/bin/bash

#lock file
LOCKFILE=/tmp/myscript.lock
#check if lock file exsits
if [ -e "$LOCKFILE" ]; then
    echo "Script is already running."
    exit 1
fi
# Create lock file
touch "$LOCKFILE"
echo "Starting Script..."

echo "Activating Virtual Enveronment"
source /home/pi/pi/LoStik-master/examples/venv/bin/activate
echo "Virtual Environment Activated"
echo "Opening Script Folder"
cd /home/pi/pi/LoStik-master/examples/aakash/LoStik/examples
echo "Starting the Script"
./allinone.py
