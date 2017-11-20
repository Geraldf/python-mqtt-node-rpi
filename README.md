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
