
'''
get the mac-address of the computer
'''
def get_mac():
    try:
        str = open('/sys/class/net/wlan0/address').read()
    except:
        raise RuntimeError('Could not get MAC for wlan0')
    return str[0:17]    # cut off trailing \n
