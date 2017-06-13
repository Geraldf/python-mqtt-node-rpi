## Light Server ##

Install pigpiod

Start at boot time, using ``sudo crontab -e``
``@reboot pigpiod``

Run startup script during boot using ``crontab -e``
``@reboot /path/to/dir/start.sh``

## Turning on lights ##

Turn on light by publishing message ``on`` to topic ``commands/hall/set/roof``
