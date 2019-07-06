# Author Daniel Falk daniel@da-robotteknik.se
#
# MQTT io controller node for Raspberry Pi
#
# This is a background service that can be used to control
# and watch the Raspberry's IO output pins through MQTT.
#
# The pins to control and the MQTT server to connect to
# are specified in the "config.ini" file.

from ConfigParser import ConfigParser, NoOptionError
import pkg_resources
import os


############ READ THE ENV TYPE ################

# Allow TEST env when no IO's are availible
# this way we can run the client on a desktop in "dummy mode"
# by exporting ENV=TEST

try:
    ENV = os.environ["ENV"]
except KeyError:
    ENV = 'PRODUCTION'


############ READ CONFIG FILE #################

# Read defaults and override with user configs
# Default are found in mqtt_node/default.ini
# while user configs are found in ./config.ini
defaults = pkg_resources.resource_filename(__name__, "default.ini")
conf = ConfigParser()
conf.read(defaults);
conf.read("config.ini");

# Verify that user has specified atleast one IO
sections = conf.sections()

if not "IO" in sections:
    raise ValueError("No [IO] section specified in config. No reason to continue...")

ios = [key for key, value in conf.items("IO")]
if len(ios) == 0:
    raise ValueError("No IO's specified in config. No reason to continue...")

# Make sure no reserved config sections are used as io names
# As of today configParser parses all keys as lower case, so this should not happen...
# Using these names cant be done since each IO needs a section of the same name,
# in that case we could not (easily) differ the unit and mqtt-server data from io data.
reserved = ['MQTT', 'UNIT', 'IO']
used_reserved = set(ios) & set(reserved)
if used_reserved:
    raise ValueError("Can't use reserved key '{}' in IO-list".format(list(used_reserved)))

# Make sure each IO has a valid config section
# The config section must at least specify the io pin number
for io in ios:
    if not io in sections:
        raise ValueError("No section speciofied for IO '{}'".format(io))
    if not "pin" in [key for key, value in conf.items(io)]:
        raise ValueError("No pin specified for IO '{}'".format(io))


########## DEFINE A LOG FUNCTION ###############

def log(msg):
    global conf
    print(msg)
    try:
        log_file = conf.get("UNIT", "log_file")
        with open(log_file, 'a') as handle:
            handle.write(msg + "\n")
    except NoOptionError:
        pass


