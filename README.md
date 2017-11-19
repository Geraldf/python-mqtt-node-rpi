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
Make sure this module is started on startup. Since we only communicate with the pigpio daemon we don't need root access.
Run startup script during boot using ``crontab -e``
``@reboot /path/to/dir/start.sh``

Modify the config.ini file to fit your needs

## Test ##

Turn on io by publishing message ``<STATE>`` to topic ``commands/home/<MODULE-NAME>/<TARGET>/output``

With the standard settings in config.ini this could be as follows using mosquitto:
```bash
mosquitto_pub -h 192.168.0.80 -t "commands/home/hall/roof/output" -m "on"
```
