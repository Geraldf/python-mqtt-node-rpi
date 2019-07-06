from ConfigParser import NoOptionError
from .. import conf, log, ios, ENV
from mqtt import Mqtt

if ENV != "TEST":
    from ..io.control import set_io, get_io
else:
    global last_value
    last_value = {}
    # Dummy action so we can test on workstation without IOs
    def set_io(target, value):
        global last_value
        last_value[target] = value
        log("DUMMY: Setting {} to {}".format(target, value))
        return True

    def get_io(target):
        global last_value
        try:
            return last_value[target]
        except KeyError:
            return "?"


'''
Get the type of a target given its name
'''
def find_target_type(target):
    target_conf = dict(conf.items(target))

    if "pin" in target_conf.keys():
        try:
            if target_conf["pin_direction"] == "input":
                return "input"
            elif target_conf["pin_direction"] == "output":
                return "output"
            else:
                log("Unknown pin direction of pin target '{}', direction = '{}'".format(
                    target, target_conf["pin_direction"]))
                return None
        except KeyError:
            # Default to output for legacy compatibility
            return "output"
    else:
        log("Type of target is unknown: {}".format(target))
        return None


'''
Handle an output state change request
'''
def handle_output(target, state):
    target_conf = dict(conf.items(target))

    # Get target io-pin number
    try:
        pin_number = int(target_conf["pin"])
    except KeyError as e:
        return Mqtt.CallbackAnswer(str(e), None, None, None)

    # Get the value of the requested state
    try:
        value = int(target_conf[state])
        state_exists = True
    except KeyError as e:
        return Mqtt.CallbackAnswer(True, str(e), None, None)

    # Set the io's value
    try:
        if set_io(pin_number, value):
            action_success = True
        else:
            action_success = False
    except Exception as e:
        # Forward exception to MQTT
        action_success = str(e)

    # Read the current state of the io
    try:
        io_state = str(get_io(pin_number))
        # Perform a reverse lookup of the state name from the config
        current_state = [k for k, v in target_conf.iteritems() if not k.startswith("pin") and v==io_state][0]
    except IndexError:
        # Failed to find mapping - return the raw io value
        current_state = io_state
    except NameError:
        current_state = ""
    except Exception as e:
        current_state = str(e)

    return Mqtt.CallbackAnswer(True, True, action_success, current_state)


'''
Proxy the action to correct unit (as of now only output io control unit exists)
'''
def proxy_action(target, state):
    target_exists = None

    try:
        # If target name is specified in config file...
        if target in ios:
            target_type = find_target_type(target)
            if target_type is not None:
                if target_type == "output":
                    return handle_output(target, state)
                else:
                    target_exists = "Nothing implemented for target type '{}'".format(target_type)
            else:
                target_exists = "Target type unknown for '{}'".format(target)
        else:
            target_exists = "No target with name '{}'".format(target)
    except Exception as e:
        # Catch all other exceptions to make sure that one thread doesn't get stuck...
        log(str(e))
        target_exists = str(e)

    return Mqtt.CallbackAnswer(target_exists, None, None, None)


def run_client():
    c = dict(conf.items("MQTT"))
    c.update(dict(conf.items("UNIT")))
    mqtt = Mqtt(c, proxy_action)

    mqtt.info.update(dict(
        description=conf.get("UNIT", "description"),
        targets=str(ios)))

    log("Using client ID {}".format(mqtt.get_id()))

    mqtt.connect_and_block()

