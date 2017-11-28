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
    ans = dict(
            target=target in ios,
            state=None,
            action=None)

    try:
        # If target name is specified in config file...
        if ans["target"]:
            target_conf = dict(conf.items(target))

            if "pin" in target_conf.keys():
                target_type = "pin"

            if target_type == "pin":
                # Get target io-pin number
                try:
                    pin = int(target_conf[target_type])
                except KeyError as e:
                    ans["target"] = str(e)

                # Get the value of the requested state
                try:
                    value = int(target_conf[state])
                    ans["state"] = True
                except KeyError as e:
                    ans["state"] = str(e)

                # Set the io's value
                if ans["state"] == True:
                    try:
                        if set_io(pin, value):
                            ans["action"] = True
                        else:
                            ans["action"] = False
                    except Exception as e:
                        # Forward exception to MQTT
                        ans["action"] = str(e)

                # Read the current state of the io
                if (pin):
                    try:
                        last_state = str(get_io(pin))
                        ans["last_state"] = [k for k, v in target_conf.iteritems() if k!=target_type and v==last_state][0]
                    except IndexError:
                        ans["last_state"] = last_state
                    except Exception as e:
                        ans["last_state"] = str(e)
                else:
                    ans["last_state"] = ""
            else:
                err_str = "Unknown target type: {}".format(target)
                ans["target"] = err_str
                log(err_str)

    # Catch all other exceptions to make sure that one thread doesn't get stuck...
    except Exception as e:
        ans["target"] = str(e)

    return ans


def run_client():

    c = dict(conf.items("MQTT"))
    c.update(dict(conf.items("UNIT")))
    mqtt = Mqtt(c, proxy_action)

    mqtt.info.update(dict(
        description=conf.get("UNIT", "description"),
        targets=str(ios)))

    log("Using client ID {}".format(mqtt.get_id()))

    mqtt.connect_and_block()

