import paho.mqtt.client as mqtt
#from control_lights import set_light
import socket
from time import sleep, time
import sys
from .. import log
from utils import get_mac
import json


'''
callback for paho on mqtt message
'''
def on_msg(client, data, msg):
    target = msg.topic.split('/')[-2]
    state = msg.payload

    status = data.callback(target, state)

    if all(value == True for value in status.values()):
        ans = dict(status="ok", value=state)
    else:
        d_err = []
        if status["target"] == False:
            d_err.append("Target is invalid")
        if status["state"] == False:
            d_err.append("Value is invalid")
        if status["action"] == False:
            d_err.append("Snap. Failed to set value for target")
        if isinstance(status["action"], str):
            d_err.append("Snap. Exception: " + status["action"])
        ans = dict(
                status="error",
                error=d_err,
                target=target,
                t_value=state)

        log("Update failed: {}".format(ans))

    ans["time"] = time()

    client.publish(
            'home/{node}/{target}/output'.format(node=data.node_name, target=target),
            payload=json.dumps(ans),
            qos=1,
            retain=False)


'''
callback for paho on mqtt connected
'''
def on_connect(client, data, flags, rc):
    if rc == 0:
        log("Connected")
        topic = "commands/home/{}/+/output".format(data.node_name)
        client.subscribe(topic, qos=1)
        return
    log("Connection failed with status " + str(rc))
    data.connected = False
    sleep(data.retry_time)
    data.retry_time = min(data.max_retry_time, data.retry_time*2)
    data.try_connect(data.mqttc)


'''
callback for paho on mqtt disconnect
'''
def on_disconnect(client, data, rc):
    log("Disconnected with reason {}...".format(rc))
    data.connected = False
    if rc != 0:
        data.try_connect(data.mqttc)


class Mqtt:
    def __init__(self, config, action_callback):
        self.id = get_mac()
        self.connected = False
        self.min_retry_time = config["min_retry_time"]
        self.max_retry_time = config["max_retry_time"]
        self.retry_time = self.min_retry_time
        self.server = config['server']
        self.node_name = config['node_name']

        self.callback = action_callback

        self.mqttc = mqtt.Client(client_id=self.id, clean_session=True, userdata=self)

        self.mqttc.on_message = on_msg
        self.mqttc.on_connect = on_connect
        self.mqttc.on_disconnect = on_disconnect


    '''
    Connect to MQTT and block until keyboard interrupt
    '''
    def connect_and_block(self):
        self.try_connect()

        self.mqttc.loop_start()

        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.mqttc.loop_stop()


    '''
    get mqtt id
    '''
    def get_id(self):
        return self.id


    '''
    try to connect to mqtt server
    '''
    def try_connect(self):
        while(not self.connected):
            try:
                self.mqttc.connect(self.server, keepalive=25)
                self.connected = True
            except socket.error:
                log("Failed to connect... Retrying in {} seconds".format(self.retry_time))
                sleep(self.retry_time)
                self.retry_time = min(self.max_retry_time, retry_time*2)

