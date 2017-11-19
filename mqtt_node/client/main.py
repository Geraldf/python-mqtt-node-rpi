from ConfigParser import NoOptionError
from .. import conf, log, ios, ENV
from mqtt import Mqtt

if ENV != "TEST":
    from ..io.control import set_io as action
else:
    # Dummy action so we can test on workstation without IOs
    def action(target, value):
        log("DUMMY: Setting {} to {}".format(target, value))
        return True


def proxy_action(target, state):
    ans = dict(
            target=target in ios,
            state=None,
            action=None)

    if ans["target"]:
        try:
            pin = int(conf.get(target, "pin"))
        except Exception as e:
            ans["target"] = str(e)

        try:
            value = int(conf.get(target, state))
            ans["state"]=True
        except NoOptionError:
            ans["state"]=False

        if ans["state"]:
            try:
                if action(pin, value):
                    ans["action"] = True
                else:
                    ans["action"] = False
            except Exception as e:
                # Forward exception to MQTT
                ans["action"] = str(e)

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

