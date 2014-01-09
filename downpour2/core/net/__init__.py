import socket
import fcntl
import struct


# Get the IP address attached to an interface or device
def get_interface_ip(interface):

    if not interface is None:

        ip_checks = [
            lambda i: i,
            lambda i: socket.gethostbyname(i),
            lambda i: get_device_ip(i)
        ]

        for check in ip_checks:
            try:
                ip = check(interface)
                socket.inet_aton(ip)
                return ip
            except Exception as e:
                pass

    return None


# Get the IP assigned to an interface name on linux
def get_device_ip(device):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', device[:15])
    )[20:24])
