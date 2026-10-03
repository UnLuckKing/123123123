import json
import paramiko
import sys
import threading
import select
import socket

def forward_port(local_port, remote_port, ssh_client):
    class ForwardServer(threading.Thread):
        def __init__(self, port):
            super().__init__()
            self.port = port
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', self.port))
            self.server_socket.listen(100)

        def run(self):
            print(f"Listening on port {self.port} to forward to remote {remote_port}")
            while True:
                client_sock, addr = self.server_socket.accept()
                chan = ssh_client.get_transport().open_channel(
                    'direct-tcpip', ('127.0.0.1', remote_port), addr)
                if chan is None:
                    client_sock.close()
                    continue
                
                threading.Thread(target=self.handler, args=(client_sock, chan)).start()

        def handler(self, client_sock, chan):
            while True:
                r, w, x = select.select([client_sock, chan], [], [])
                if client_sock in r:
                    data = client_sock.recv(1024)
                    if len(data) == 0:
                        break
                    chan.send(data)
                if chan in r:
                    data = chan.recv(1024)
                    if len(data) == 0:
                        break
                    client_sock.send(data)
            chan.close()
            client_sock.close()

    server = ForwardServer(local_port)
    server.daemon = True
    server.start()
    return server

if __name__ == '__main__':
    with open('mac_args.json') as f:
        args = json.load(f)
        
    rc_port = None
    for arg in args:
        if arg.startswith('--riotclient-app-port='):
            rc_port = int(arg.split('=')[1])
            break
            
    if not rc_port:
        print("No riotclient-app-port found")
        sys.exit(1)
        
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('51.159.121.126', username='m1', password='PNGGJHc5f7f1')
    
    forward_port(rc_port, rc_port, ssh)
    
    import time
    while True:
        time.sleep(1)
