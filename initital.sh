# If not located in pi homedir, then you must change the path in the mqtt-node.service file!
sudo cp ~/python-mqtt-node-rpi/mqtt-node.service /etc/systemd/system

sudo systemctl daemon-reload
sudo systemctl start mqtt-node.service
sudo systemctl enable mqtt-node.service