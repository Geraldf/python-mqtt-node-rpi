from . import gpio

def set_io(pin, state):
    return int(gpio.write(pin, state)) == 0
