import paho.mqtt.client as mqtt
from control_lights import set_light
import socket
from time import sleep
import sys


# Settings go here FIXME: Move to ini-file
# ----------------------------------------
NODE_NAME = "hall"
SERVER = "192.168.0.80"
MIN_RETRY_TIME = 2
MAX_RETRY_TIME = 20
# ---------------------------------------

connected = False
retry_time = MIN_RETRY_TIME
log_file = None

if len(sys.argv) == 2:
    print("Writing log messages to " + sys.argv[1])
    log_file = sys.argv[1]


'''
print to stdout and logfile
'''
def log(msg):
    global log_file
    print(msg)
    if not log_file is None:
        with open(log_file, 'a') as handle:
            handle.write(msg + "\n")


'''
get the mac-address of the computer
'''
def get_mac():
    try:
        str = open('/sys/class/net/wlan0/address').read()
    except:
        raise RuntimeError('Could not get MAC for wlan0')
    return str[0:17]    # cut off trailing \n


'''
callback for paho on mqtt message
'''
def on_msg(client, userdata, msg):
    action = msg.topic.split('/')[-2]
    target = msg.topic.split('/')[-1]
    state = msg.payload

    res = 1
    if action == "set":
        try:
            res = set_light(target, state)
            log("target {} changed to {}".format(target, state))
        except:
            res = 2
            log("Failed to set light {} to state {}.".format(target, state))
    else:
        log("Unknown command received...")

    if res == 0:
        ans = 'ok,{}'.format(state)
    elif res == 1:
        ans = 'error,unknown command'
    elif res == -1:
        ans = 'error,unknown target'
    elif res == -2:
        ans = 'error,unknown state'
    client.publish(
            'cmdres/{node}/{target}'.format(node=NODE_NAME, target=target),
            payload=ans,
            qos=1,
            retain=False)


'''
callback for paho on mqtt connected
'''
def on_connect(client, userdata, rc):
    global connected
    if rc == 0:
        log("Connected")
        client.subscribe("commands/hall/#", qos=1)
        return
    log("Connecttion failed with status " + str(rc))
    connected = False
    sleep(retry_time)
    retry_time = min(MAX_RETRY_TIME, retry_time*2)
    try_connect(mqttc)


'''
callback for paho on mqtt disconnect
'''
def on_disconnect(client, userdata, rc):
    global retry_time
    global connected
    log("Disconnected with reason {}...".format(rc))
    connected = False
    if rc != 0:
        try_connect(mqttc)


'''
try to connect to mqtt server
'''
def try_connect(mqttc):
    global retry_time
    global connected
    while(not connected):
        try:
            mqttc.connect(SERVER, keepalive=25)
            connected = True
        except socket.error:
            log("Failed to connect... Retrying in {} seconds".format(retry_time))
            sleep(retry_time)
            retry_time = min(MAX_RETRY_TIME, retry_time*2)





mqttc = mqtt.Client(client_id=get_mac(), clean_session=False)

mqttc.on_message = on_msg
mqttc.on_connect = on_connect
mqttc.on_disconnect = on_disconnect

try_connect(mqttc)

mqttc.loop_start()

try:
    while True:
        sleep(1)
except KeyboardInterrupt:
    pass
finally:
    mqttc.loop_stop()
