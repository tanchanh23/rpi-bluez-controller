#!/bin/bash
sleep 45

sudo bluetoothctl <<EOF
power on
discoverable on
pairable off
agent NoInputNoOutput
default-agent 
EOF

sleep 15
cd /home/pi/elevator_ble/
sudo /usr/bin/python3 elevator_air.py
