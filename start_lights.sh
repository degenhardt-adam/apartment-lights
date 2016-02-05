#!/bin/sh
cd /home/pi/lights
sudo nohup python -u lights.py > /home/pi/lights/log &
