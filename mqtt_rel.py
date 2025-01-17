

import paho.mqtt.client as mqtt
import configparser
import ssl
import time
import sys
import socket
import signal
import os
import logging
__author__ = "Gerald Fuchs"
__copyright__ = "Copyright (C) Gerald Fuchs"
__date__ = "30.12.2021"

'''
based on the initial implementation of https://github.com/daniel-falk/python-mqtt-node-rpi

'''


PFIO_MODULE = False
GPIO_MODULE = False
GPIO_OUTPUT_PINS = []

# Script name (without extension) used for config/logfile names
APPNAME = os.path.splitext(os.path.basename(__file__))[0]
INIFILE = os.getenv('INIFILE', APPNAME + '.ini')
LOGFILE = os.getenv('LOGFILE', APPNAME + '.log')

# Read the config file
config = configparser.ConfigParser()
config.read(INIFILE)

# Use ConfigParser to pick out the settings
MODULE = config.get("global", "module")
DEBUG = config.getboolean("global", "debug")

MQTT_HOST = config.get("global", "mqtt_host")
MQTT_PORT = config.getint("global", "mqtt_port")
MQTT_CLIENT_ID = config.get("global", "mqtt_client_id")
MQTT_QOS = config.getint("global", "mqtt_qos")
MQTT_RETAIN = config.getboolean("global", "mqtt_retain")
MQTT_CLEAN_SESSION = config.getboolean("global", "mqtt_clean_session")
MQTT_TOPIC = config.get("global", "mqtt_topic")
MQTT_LWT = config.get("global", "mqtt_lwt")

MQTT_USERNAME = config.get("global", "mqtt_username", fallback=None)
MQTT_PASSWORD = config.get("global", "mqtt_password", fallback=None)

MQTT_TLS_PROTOCOL = config.get("global", "mqtt_tls_protocol", fallback=None)
MQTT_TLS_INSECURE = config.get("global", "mqtt_tls_insecure", fallback=False)
MQTT_CERT_PATH = config.get("global", "mqtt_cert_path", fallback=None)

MONITOR_PINS = config.get("global", "monitor_pins", raw=True)
MONITOR_PINS_PUD = config.get(
    "global", "monitor_pins_pud")  # UP, DOWN or unset
MONITOR_PIN_NUMBERING = config.get(
    "global", "monitor_pin_numbering")  # BCM or BOARD
MONITOR_OUT_INVERT = config.getboolean("global", "monitor_out_invert")
MONITOR_POLL = config.getfloat("global", "monitor_poll")
MONITOR_REFRESH = config.get("global", "monitor_refresh")

# Initialise logging
LOGFORMAT = '%(asctime)-15s %(levelname)-5s %(message)s'

logging.basicConfig(level=logging.DEBUG, format=LOGFORMAT)
# if DEBUG:
#     logging.basicConfig(filename=LOGFILE,
#                         level=logging.DEBUG,
#                         format=LOGFORMAT)
# else:
#     logging.basicConfig(filename=LOGFILE,
#                         level=logging.INFO,
#                         format=LOGFORMAT)

logging.info("Starting " + APPNAME)
logging.info("INFO MODE")
logging.debug("DEBUG MODE")
logging.debug("INIFILE = %s" % INIFILE)
logging.debug("LOGFILE = %s" % LOGFILE)

# Check we have the necessary module
if MODULE.lower() == "pfio":
    try:
        import pifacedigitalio as PFIO
        logging.info("PiFace.PFIO module detected...")
        PFIO_MODULE = True
    except ImportError:
        logging.error(
            "Module = %s in %s but PiFace.PFIO module was not found" %
            (MODULE, INIFILE))
        sys.exit(2)

if MODULE.lower() == "gpio":
    try:
        import RPi.GPIO as GPIO
        logging.info("RPi.GPIO module detected...")
        GPIO_MODULE = True
    except ImportError:
        logging.error(
            "Module = %s in %s but RPi.GPIO module was not found" %
            (MODULE, INIFILE))
        sys.exit(2)

# Convert the list of strings to a list of ints.
# Also strips any whitespace padding
PINS = []
if MONITOR_PINS:
    PINS.extend(list(map(int, MONITOR_PINS.split(","))))

if len(PINS) == 0:
    logging.debug("Not monitoring any pins")
else:
    logging.debug("Monitoring pins %s" % PINS)

# Append a column to the list of PINS. This will be used to store state.
for PIN in PINS:
    PINS[PINS.index(PIN)] = [PIN, -1]

MQTT_TOPIC_IN = MQTT_TOPIC + "/in/+"
MQTT_TOPIC_OUT = MQTT_TOPIC + "/out/%d"

# Create the MQTT client
if not MQTT_CLIENT_ID:
    MQTT_CLIENT_ID = APPNAME + "_%d" % os.getpid()
    MQTT_CLEAN_SESSION = True

mqttc = mqtt.Client(MQTT_CLIENT_ID, clean_session=MQTT_CLEAN_SESSION)

# MQTT callbacks


def on_connect(mosq, obj, flags, result_code):
    """
    Handle connections (or failures) to the broker.
    This is called after the client has received a CONNACK message
    from the broker in response to calling connect().
    The parameter rc is an integer giving the return code:

    0: Success
    1: Refused . unacceptable protocol version
    2: Refused . identifier rejected
    3: Refused . server unavailable
    4: Refused . bad user name or password (MQTT v3.1 broker only)
    5: Refused . not authorised (MQTT v3.1 broker only)
    """
    if result_code == 0:
        logging.info("Connected to %s:%s" % (MQTT_HOST, MQTT_PORT))

        # Subscribe to our incoming topic
        mqttc.subscribe(MQTT_TOPIC_IN, qos=MQTT_QOS)

        # Subscribe to the monitor refesh topic if required
        if MONITOR_REFRESH:
            mqttc.subscribe(MONITOR_REFRESH, qos=0)

        # Publish retained LWT as per http://stackoverflow.com/questions/19057835/how-to-find-connected-mqtt-client-details/19071979#19071979
        # See also the will_set function in connect() below
        mqttc.publish(MQTT_LWT, "1", qos=0, retain=True)

    elif result_code == 1:
        logging.info("Connection refused - unacceptable protocol version")
    elif result_code == 2:
        logging.info("Connection refused - identifier rejected")
    elif result_code == 3:
        logging.info("Connection refused - server unavailable")
    elif result_code == 4:
        logging.info("Connection refused - bad user name or password")
    elif result_code == 5:
        logging.info("Connection refused - not authorised")
    else:
        logging.warning("Connection failed - result code %d" % (result_code))


def on_disconnect(mosq, obj, result_code):
    """
    Handle disconnections from the broker
    """
    if result_code == 0:
        logging.info("Clean disconnection from broker")
    else:
        logging.info("Broker connection lost. Retrying in 5s...")
        time.sleep(5)


def on_message(mosq, obj, msg):
    """
    Handle incoming messages
    """
    if msg.topic == MONITOR_REFRESH:
        logging.debug("Refreshing the state of all monitored pins...")
        refresh()
        return

    topicparts = msg.topic.split("/")
    pin = int(topicparts[len(topicparts) - 1])
    logging.debug("Incoming message for pin %d -> %s" % (pin, msg.payload))
    value = int(msg.payload)
    logging.debug("Incoming message for pin %d -> %d" % (pin, value))

    if PFIO_MODULE:
        if value == 1:
            PFIO.digital_write(pin, 1)
        else:
            PFIO.digital_write(pin, 0)

    if GPIO_MODULE:
        if pin not in GPIO_OUTPUT_PINS:
            pass
            # GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
            # GPIO_OUTPUT_PINS.append(pin)

        if value == 1:
            GPIO.output(pin, GPIO.LOW)
        else:
            GPIO.output(pin, GPIO.HIGH)

# End of MQTT callbacks


def cleanup(signum, frame):
    """
    Signal handler to ensure we disconnect cleanly
    in the event of a SIGTERM or SIGINT.
    """
    # Cleanup our interface modules
    if PFIO_MODULE:
        logging.debug("Clean up PiFace.PFIO module")
        PFIO.deinit()

    if GPIO_MODULE:
        logging.debug("Clean up RPi.GPIO module")
        for pin in GPIO_OUTPUT_PINS:
            GPIO.output(pin, GPIO.HIGH)
        GPIO.cleanup()

    # Publish our LWT and cleanup the MQTT connection
    logging.info("Disconnecting from broker...")
    mqttc.publish(MQTT_LWT, "0", qos=0, retain=True)
    mqttc.disconnect()
    mqttc.loop_stop()

    # Exit from our application
    logging.info("Exiting on signal %d" % (signum))
    sys.exit(signum)


def connect():
    """
    Connect to the broker, define the callbacks, and subscribe
    This will also set the Last Will and Testament (LWT)
    The LWT will be published in the event of an unclean or
    unexpected disconnection.
    """
    # Add the callbacks
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_message = on_message

    # Set the login details
    if MQTT_USERNAME:
        mqttc.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    # Set TLS details
    if MQTT_TLS_PROTOCOL:
        if MQTT_TLS_PROTOCOL == 'tlsv1_2':
            mqttc.tls_set(MQTT_CERT_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
            mqttc.tls_insecure_set(MQTT_TLS_INSECURE)
        if MQTT_TLS_PROTOCOL == 'tlsv1_1':
            mqttc.tls_set(MQTT_CERT_PATH, tls_version=ssl.PROTOCOL_TLSv1_1)
            mqttc.tls_insecure_set(MQTT_TLS_INSECURE)
        if MQTT_TLS_PROTOCOL == 'tlsv1':
            mqttc.tls_set(MQTT_CERT_PATH, tls_version=ssl.PROTOCOL_TLSv1)
            mqttc.tls_insecure_set(MQTT_TLS_INSECURE)
        if MQTT_TLS_PROTOCOL == 'sslv3':
            mqttc.tls_set(MQTT_CERT_PATH, tls_version=ssl.PROTOCOL_SSLv3)
            mqttc.tls_insecure_set(MQTT_TLS_INSECURE)

    # Set the Last Will and Testament (LWT) *before* connecting
    mqttc.will_set(MQTT_LWT, payload="0", qos=0, retain=True)

    # Attempt to connect
    logging.debug("Connecting to %s:%d..." % (MQTT_HOST, MQTT_PORT))
    try:
        mqttc.connect(MQTT_HOST, MQTT_PORT, 60)
    except Exception as e:
        logging.error(
            "Error connecting to %s:%d: %s" %
            (MQTT_HOST, MQTT_PORT, str(e)))
        sys.exit(2)

    # Let the connection run forever
    mqttc.loop_start()


def init_pfio():
    """
    Initialise the PFIO library
    """
    PFIO.init()


def init_gpio():
    """
    Initialise the GPIO library
    """
    GPIO.setwarnings(False)
    if MONITOR_PIN_NUMBERING == "BCM":
        logging.debug("Initialising GPIO using BCM numbering")
        GPIO.setmode(GPIO.BCM)
    else:
        logging.debug("Initialising GPIO using Board numbering")
        GPIO.setmode(GPIO.BOARD)

    for PIN in PINS:
        index = [y[0] for y in PINS].index(PIN[0])
        pin = PINS[index][0]

        logging.debug("Initialising GPIO input pin %d..." % (pin))
        GPIO.setup(pin, GPIO.OUT)
        # if MONITOR_PINS_PUD == "UP":
        #     GPIO.setup(pin, GPIO.OUT, pull_up_down=GPIO.PUD_UP)
        # elif MONITOR_PINS_PUD == "DOWN":
        #     GPIO.setup(pin, GPIO.OUT, pull_up_down=GPIO.PUD_DOWN)
        # else:
        #     GPIO.setup(pin, GPIO.OUT)


def read_pin(pin):
    state = -1
    if PFIO_MODULE:
        state = PFIO.digital_read(pin)

    if GPIO_MODULE:
        state = GPIO.input(pin)

    if MONITOR_OUT_INVERT:
        if state == 0:
            state = 1
        elif state == 1:
            state = 0
    return(state)


def refresh():
    """
    Refresh the state of all pins we are monitoring
    """
    for PIN in PINS:
        index = [y[0] for y in PINS].index(PIN[0])
        pin = PINS[index][0]
        state = read_pin(pin)

        logging.debug("Refreshing pin %d state -> %d" % (pin, state))
        mqttc.publish(
            MQTT_TOPIC_OUT %
            pin,
            payload=state,
            qos=MQTT_QOS,
            retain=MQTT_RETAIN)


def poll():
    """
    The main loop in which we monitor the state of the PINs
    and publish any changes.
    """
    while True:
        for PIN in PINS:
            index = [y[0] for y in PINS].index(PIN[0])
            pin = PINS[index][0]
            oldstate = PINS[index][1]
            newstate = read_pin(pin)

            if newstate != oldstate:
                logging.debug(
                    "Pin %d changed from %d to %d" %
                    (pin, oldstate, newstate))
                mqttc.publish(
                    MQTT_TOPIC_OUT %
                    pin,
                    payload=newstate,
                    qos=MQTT_QOS,
                    retain=MQTT_RETAIN)
                PINS[index][1] = newstate

        time.sleep(MONITOR_POLL)


# Use the signal module to handle signals
for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
    signal.signal(sig, cleanup)

# Initialise our pins
if PFIO_MODULE:
    init_pfio()

if GPIO_MODULE:
    init_gpio()

# Connect to broker and begin polling our GPIO pins
connect()
poll()
