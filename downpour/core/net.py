import socket, fcntl, struct

# Set comm interface (useful for routing torrent traffic over VPN, etc)
def get_interface(interface):
    if not interface is None:
        try:
            ip = socket.gethostbyname(interface)
            # Verify we got an IP
            socket.inet_aton(ip)
            return ip
        except socket.error:
            # Probably specified a local interface name
            try:
                ip = get_device_ip(interface)
                # Verify we got an IP
                socket.inet_aton(ip)
                return ip
            except socket.error as se:
                raise IOError('Interface not found')
            except IOError as ioe:
                raise IOError('Interface not found')
    return None

# Get the IP assigned to an interface name on linux
def get_device_ip(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
