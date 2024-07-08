import socket
import os
import threading
import time
import json
from datetime import datetime
from typing import Any, Dict

class UnixSocketServer(threading.Thread):
    def __init__(self, socket_file, bufsize, encoding):
        threading.Thread.__init__(self)
        self.socket_file = socket_file
        self.bufsize = bufsize
        self.encoding = encoding
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.clients = []

        # Ensure the socket does not already exist
        try:
            os.unlink(self.socket_file)
        except OSError:
            if os.path.exists(self.socket_file):
                raise

    def run(self):
        self.server_socket.bind(self.socket_file)
        self.server_socket.listen()
        print(f"Server started and listening at {self.socket_file}")

        while True:
            client_socket, _ = self.server_socket.accept()
            self.clients.append(client_socket)
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()

    def handle_client(self, client_socket):
        with client_socket:
            while True:
                try:
                    data = self.get_sample_data()
                    client_socket.sendall(data.encode(self.encoding))
                    time.sleep(.1)  # Simulate some delay between sends
                except socket.error as e:
                    print(f"Socket error: {e}")
                    break

    def get_sample_data(self) -> str:
        # Replace with actual data generation logic
        sample_data: Dict[str, Any] = {
            "user": "example_user",
            "time": datetime.now().strftime('%H:%M:%S.%f')[:-3],
            "meat_type": "beef",
            "doneness": "medium-rare",
            "sear_level": "high",
            "cook_time": 360,  # example in seconds
            "rest_time": 180,  # example in seconds
            "thickness": 1.5  # example in inches
        }
        return json.dumps(sample_data) + "\n"

    def shutdown(self):
        for client_socket in self.clients:
            client_socket.close()
        self.server_socket.close()
        if os.path.exists(self.socket_file):
            os.unlink(self.socket_file)
        print("Server shut down")

if __name__ == "__main__":
    socket_file = "/tmp/my_unix_socket"
    bufsize = 1024
    encoding = "utf-8"

    server = UnixSocketServer(socket_file, bufsize, encoding)
    server.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
