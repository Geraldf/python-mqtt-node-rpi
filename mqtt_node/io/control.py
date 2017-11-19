from . import gpio

def set_io(pin, state):
    return gpio.write(pin, state)
