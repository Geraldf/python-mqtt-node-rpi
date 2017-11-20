# Light Server #

## Install dependencies ##
This code uses pigpio to control IO pinns. Install pigpio daemon and make sure it starts on machine boot-up
```bash
sudo apt-get install pigpio python-pigpio python3-pigpio
```

Start pigpio as root at boot time, using ``sudo crontab -e``
``@reboot pigpiod``


We also need paho-mqtt python client, install it using pip: 
```bash
pip install paho-mqtt
```

## Configure ##
Make sure this module is started on startup. We use a unit-file to tell systemd to start the application on boot (and make sure that it always is running, respawning it if necessary)

```bash
# If not located in pi homedir, then you must change the path in the mqtt-node.service file!
sudo cp ~/python-mqtt-node-rpi/mqtt-node.service /etc/systemd/system

sudo systemctl daemon-reload
sudo systemctl start mqtt-node.service
sudo systemctl enable mqtt-node.service
```

Modify the config.ini file to fit your needs

## Test ##

Show the log using the systemd journal:
```bash
sudo journalctl -u mqtt-node -f
```

Turn on io by publishing message ``<STATE>`` to topic ``commands/home/<MODULE-NAME>/<TARGET>/output``

With the standard settings in config.ini this could be as follows using mosquitto:
```bash
mosquitto_pub -h 192.168.0.80 -t "commands/home/hall/roof/output" -m "on"
```

## Misc ##

#### Auto import new nodes to ssh ####
By using nodes with the mqtt-node program you have a self-discovery database of all the nodes names and IP-addresses.

Using a simple script we can retrieve this information and add in the ssh config. Next time you want to ssh into your raspberry you dont have to worry about what IP it has, just type ``ssh <node_name>``, eg. using the standard config.ini file ``ssh hall``.

Make the script run every now and then using crontab or manually run it when something has changed. The script finds the ip for all nodes on the topic ``home/<node_name>/info/ip``.

```bash
#!/bin/bash

# Node discovery script
# Dependencies: Please first install mosquitto_sub

# Author Daniel Falk
# https://github.com/daniel-falk/python-mqtt-node-rpi

# This is the address to the MQTT broker
SERVER=192.168.0.80

IDENTIFIER="# EVERYTHING AFTER THIS COMMENT IS VOLATILE AND MIGHT GET REMOVED!"

# Read all names and IPs from MQTT
UNITS=$(timeout 0.3 mosquitto_sub -h $SERVER -t home/+/info/ip -v)

# Convert to arrays
OLDIFS=$IFS
IFS=$'\n'
units=($UNITS)
IFS=$OLDIFS

# Remove output from last time and add new
sed -ni "/$IDENTIFIER/q;p" ~/.ssh/config
echo "$IDENTIFIER" >> ~/.ssh/config
echo "# ALSO, DON'T CHANGE THE COMMENT ABOVE OR YOU WILL BREAK THE SCRIPT" >> ~/.ssh/config

# Loop through
for (( i=0; i<${#units[@]}; i++ )); do
    NAME=$(echo ${units[$i]} | sed 's/^[^/]\+\/\([^/]\+\)\/.*/\1/')
    IP=$(echo ${units[$i]} | awk '{ print $2 }')

    # Add to ssh-config
    echo "Host $NAME
    HostName $IP
    User pi" >> ~/.ssh/config
done
```
