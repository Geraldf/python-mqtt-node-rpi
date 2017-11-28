from . import gpio

def set_io(pin, state):
    return int(gpio.write(pin, state)) == 0

def get_io(pin):
    return gpio.read(pin)
