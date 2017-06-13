#!/bin/bash

LOG=/home/pi/light_server.log

DIR=$(dirname $0)

echo "
--- STARTING SERVER ---" >> $LOG
date >> $LOG
ps -aux | grep [p]igpiod >> $LOG

python $DIR/light_server.py $LOG
