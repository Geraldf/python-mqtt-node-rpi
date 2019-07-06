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
Proxy the action to correct unit (as of now only io-control unit exists)
'''
def proxy_action(target, state):
    target_exists = target in ios
    state_exists = None
    action_success = None
    current_state = None

    try:
        # If target name is specified in config file...
        if target_exists:
            target_conf = dict(conf.items(target))

            if "pin" in target_conf.keys():
                target_type = "pin"

            if target_type == "pin":
                # Get target io-pin number
                try:
                    pin_number = int(target_conf[target_type])
                except KeyError as e:
                    target_exists = str(e)

                # Get the value of the requested state
                try:
                    value = int(target_conf[state])
                    state_exists = True
                except KeyError as e:
                    state_exists = str(e)

                # Set the io's value
                if state_exists == True:
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
                    current_state = [k for k, v in target_conf.iteritems() if k!=target_type and v==io_state][0]
                except IndexError:
                    # Failed to find mapping - return the raw io value
                    current_state = io_state
                except NameError:
                    current_state = ""
                except Exception as e:
                    current_state = str(e)
            else:
                err_str = "Type of target is unknown: {}".format(target)
                target_exists = err_str
                log(err_str)

    # Catch all other exceptions to make sure that one thread doesn't get stuck...
    except Exception as e:
        target_exists = str(e)

    return Mqtt.CallbackAnswer(target_exists, state_exists, action_success, current_state)


def run_client():
    c = dict(conf.items("MQTT"))
    c.update(dict(conf.items("UNIT")))
    mqtt = Mqtt(c, proxy_action)

    mqtt.info.update(dict(
        description=conf.get("UNIT", "description"),
        targets=str(ios)))

    log("Using client ID {}".format(mqtt.get_id()))

    mqtt.connect_and_block()

