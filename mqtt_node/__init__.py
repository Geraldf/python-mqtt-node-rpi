from ConfigParser import ConfigParser, NoOptionError
import pkg_resources
import os


############ READ THE ENV TYPE ################

# Allow TEST env when no IO's are availible

try:
    ENV = os.environ["ENV"]
except KeyError:
    ENV = 'PRODUCTION'


############ READ CONFIG FILE #################

# Read defaults and override with user configs
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
reserved = ['MQTT', 'UNIT', 'IO']
used_reserved = set(ios) & set(reserved)
if used_reserved:
    raise ValueError("Can't use reserved key '{}' in IO-list".format(list(used_reserved)))

# Make sure each IO has a valid congif section
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


