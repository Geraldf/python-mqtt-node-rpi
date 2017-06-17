import pigpio

LIGHTS = dict(
        roof = 26)

STATES = dict(
        on = 1,
        off = 0)


def set_light(light, state):
    if not light in LIGHTS:
        return -1
    if not state in STATES:
        return -2
    gpio.write(LIGHTS[light], STATES[state])
    return 0


gpio = pigpio.pi()
