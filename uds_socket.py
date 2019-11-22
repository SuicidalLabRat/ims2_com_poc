import socket
import os
import time

# Create a UDS socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)  # socket.SOCK_DGRAM)
sock.setblocking(False)

server_address = '/tmp/socket_file'

# Make sure file doesn't exist already
try:
    os.unlink(server_address)
except FileNotFoundError:
    pass

# Bind the socket to the port
print('Starting up on {}'.format(server_address))
sock.bind(server_address)


# Listen for incoming connections
sock.listen(1)

while True:
    # Wait for a connection
    print('waiting for a connection')
    try:
        connection, client_address = sock.accept()
    except BlockingIOError as e:
        print(e.errno)
        if e.errno == 11: continue
        else: raise

    try:
        print('connection from {0}'.format(client_address))

        # Receive the data in small chunks and retransmit it
        while True:
            data = 'test'.encode('utf-8')
            if data:
                connection.send(data)
                time.sleep(2)
            else:
                break
            # data = connection.recv(16)
            # print('received {!r}'.format(data))
            # if data:
            #     print('sending data back to the client')
            #     connection.sendall(data)
            # else:
            #     print('no data from', client_address)
            #     break

    finally:
        # Clean up the connection
        print("Closing current connection")
        connection.close()

# sock.send('test'.encode('utf-8'))