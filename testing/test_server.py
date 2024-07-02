import socket
import os
import time
from datetime import datetime
import json

# Define the Unix socket file path
socket_file = '/tmp/unix_socket_example'

# Ensure the socket does not already exist
try:
    os.unlink(socket_file)
except OSError:
    if os.path.exists(socket_file):
        raise

# Create a Unix domain socket
server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# Bind the socket to the file path
server_socket.bind(socket_file)

# Listen for incoming connections
server_socket.listen(1)

print(f'Server is listening at {socket_file}')

while True:
    # Accept a connection
    connection, client_address = server_socket.accept()
    print(f'Connection from {client_address}')

    try:
        while True:
            # Generate data (example values provided)
            data = {
                "user": "example_user",
                "time": datetime.now().strftime('%H:%M:%S.%f')[:-3],
                "meat_type": "beef",
                "doneness": "medium-rare",
                "sear_level": "high",
                "cook_time": 360,  # example in seconds
                "rest_time": 180,  # example in seconds
                "thickness": 1.5  # example in inches
            }
            
            # Convert dictionary to JSON string
            json_data = json.dumps(data) + '\n'  # Adding newline for easier splitting in the client
            
            # Send data to the client
            connection.sendall(json_data.encode('utf-8'))
            
            # Wait for 10 milliseconds before sending the next piece of data
    except BrokenPipeError:
        # Handle case where client disconnects
        print(f'Client {client_address} disconnected')
    finally:
        # Clean up the connection
        connection.close()
