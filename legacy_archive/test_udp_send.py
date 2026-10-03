import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(3.0)
s.sendto(b"ping", ("51.159.121.126", 8200))
print("UDP packet sent to 51.159.121.126:8200")
