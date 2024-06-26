import socket
import time
import json

# Configuration dictionary with necessary fields
config = {
    "bufsize": 1024,
    "encoding": "utf-8",
    "socket_file": "/tmp/unix_socket_example"
}

def main():
    # Extract configuration values
    bufsize = config["bufsize"]
    encoding = config["encoding"]
    socket_file = config["socket_file"]

    # Create a Unix domain socket
    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Connect the socket to the server
    client_socket.connect(socket_file)

    buffer = ""

    try:
        while True:
            # Capture the time the request is sent
            request_time = time.time()  # Using time.time() for higher precision

            # Send a request to the server
            client_socket.sendall(b'REQUEST DATA')

            # Receive data from the server
            while True:
                data = client_socket.recv(bufsize)
                if not data:
                    break
                buffer += data.decode(encoding)

                # Split the buffer on the newline character
                lines = buffer.split('\n')
                buffer = lines[-1]  # Save the last partial line back to the buffer

                # Process all complete lines
                if len(lines) > 1:
                    response = lines[-2]  # Get the latest complete line
                    break

            # Capture the time the response is received
            response_time = time.time()

            # Parse the received data
            try:
                parsed_data = json.loads(response)
            except json.JSONDecodeError as e:
                parsed_data = f"Error processing response: {e} - Response: {response}"

            # Print the request time, response time, and the received data
            print(f'Request sent at: {time.strftime("%H:%M:%S", time.localtime(request_time))}.{int(request_time*1000)%1000:03d}, '
                  f'Response received at: {time.strftime("%H:%M:%S", time.localtime(response_time))}.{int(response_time*1000)%1000:03d}, '
                  f'Received data: {parsed_data}')
            
            # Wait to maintain a 10 Hz request rate
            time.sleep(0.1)
    finally:
        # Clean up the connection
        client_socket.close()

if __name__ == "__main__":
    main()
