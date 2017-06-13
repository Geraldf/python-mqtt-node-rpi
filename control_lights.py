import pigpio

LIGHTS = dict(
        roof = 26)

STATES = dict(
        on = 1,
        off = 0)


def set_light(light, state):
    gpio.write(LIGHTS[light], STATES[state])


gpio = pigpio.pi()
