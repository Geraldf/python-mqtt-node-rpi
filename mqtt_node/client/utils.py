import socket
from .. import conf

'''
get the mac-address of the computer
'''
def get_mac():
    try:
        str = open('/sys/class/net/wlan0/address').read()
    except:
        raise RuntimeError('Could not get MAC for wlan0')
    return str[0:17]    # cut off trailing \n

'''
get the ip-address of the computer
'''
def get_ip():
    ip = socket.gethostbyname(socket.gethostname())

    if ip.startswith("127."):
        try:
            server = conf.get("MQTT", "server")
        except:
            # There shouldn't be any need to actually reach a destination to get our ip
            server = "1.2.3.4"

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((server, 1))
            ip = s.getsockname()[0]
        except:
            ip="?"
        finally:
            s.close()

    return ip
