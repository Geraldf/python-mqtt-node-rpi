#!/bin/bash

echo "
--- STARTING MQTT NODE ---"
if ! ps -aux | grep [p]igpiod; then
    echo "WARNING, Pigpio daemon is not running!"
fi

python -m mqtt_node
