#!/bin/bash

echo "
--- STARTING MQTT NODE ---"
if ! ps -aux | grep [p]igpiod; then
    echo "WARNING, Pigpio daemon is not running!"
fi

cd $(dirname $0)
python -m mqtt_node 2> err.txt
