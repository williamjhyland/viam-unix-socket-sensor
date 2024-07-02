import socket
import json
import threading
import time
from typing import Any, ClassVar, Dict, Mapping, Optional, Sequence
from typing_extensions import Self
from viam.components.sensor import Sensor
from viam.logging import getLogger
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily
from viam.utils import struct_to_dict
from viam.errors import NoCaptureToStoreError

LOGGER = getLogger(__name__)

class myThread(threading.Thread):

    def __init__(self, name, socket_file, bufsize, encoding):
        threading.Thread.__init__(self)
        # Thread Info
        self.name = name
        self.running = False
        self.lock = threading.Lock()
        # Socket Info
        self.client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_file = socket_file
        self.bufsize = bufsize
        self.encoding = encoding
        self.reconnect_interval = 5
        self.latest_reading = None
        self.buffer = ""
    
    def run(self):
        LOGGER.info(f"Starting thread of {self.name}")
        self.running = True
        while self.running:
            self.connect_to_server()
            time.sleep(self.reconnect_interval)

    def shutdown(self):
        LOGGER.info('shutting down Socket Client & joining threads')
        self.running = False
        self.client_socket.close()
        self.join()

    def loop(self):
        while self.running:
            try:
                data = self.client_socket.recv(self.bufsize)
                if not data:
                    break
                self.buffer += data.decode(self.encoding)
                lines = self.buffer.split('\n')
                self.buffer = lines[-1]

                if len(lines) > 1:
                    with self.lock:
                        self.latest_reading = self.parse_response(lines[-2])
            except socket.error as e:
                LOGGER.error(f"Failed to receive data: {e}")
                self.shutdown()

    def connect_to_server(self):
        while self.running:
            try:
                self.client_socket.connect(self.socket_file)
                LOGGER.info('Connected to Unix socket server')
                self.loop()
            except socket.error as e:
                LOGGER.error(f"Socket error: {e}")
                self.shutdown()

    def receive_data(self) -> Optional[str]:
        while self.running:
            try:
                data = self.client_socket.recv(self.bufsize)
                self.buffer += data.decode(self.encoding)
                lines = self.buffer.split('\n')
                self.buffer = lines[-1]

                if len(lines) > 1:
                    self.latest_reading = self.parse_response(lines[-2])
            except socket.error as e:
                LOGGER.error(f"Failed to receive data: {e}")
                self.shutdown()

    def parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Error processing response: {e} - Response: {response}")
            return None

class MySensor(Sensor):
    MODEL: ClassVar[Model] = Model(ModelFamily("bill", "unixsocket"), "sensor")
    REQUIRED_ATTRIBUTES = ["socket_file", "bufsize", "encoding"]
    
    def __init__(self, name: str):
        super().__init__(name)
        self.socket_file: str = ""
        self.bufsize: int = 1024
        self.encoding: str = "utf-8"
        self.process_response: bool = False
        self.thread: Optional[myThread] = None
        self.buffer = ""

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        # Create a new instance of MySensor and configure it
        sensor = cls(config.name)
        sensor.reconfigure(config, dependencies)
        return sensor

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> Sequence[str]:
        # Validate the configuration to ensure all required attributes are present
        missing_attrs = [attr for attr in cls.REQUIRED_ATTRIBUTES if attr not in config]
        if missing_attrs:
            raise ValueError(f"Missing required attributes in UnixSocket Sensor Configuration: {', '.join(missing_attrs)}")
        return []

    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        LOGGER.info("Reconfiguring " + self.name)
        
        # Shutdown thread on reconfigure
        if self.thread:
            self.thread.shutdown()

        # Store config and dependencies
        self.config = config
        self.dependencies = dependencies 

        # Parse dictionary from the configuration attributes
        config_dict = struct_to_dict(config.attributes)

        # Set attributes from the configuration
        self.socket_file = config_dict["socket_file"]
        self.bufsize = int(config_dict["bufsize"])
        self.encoding = config_dict["encoding"]

        # Initialize and configure the Unix socket
        self.thread = myThread(self.name, self.socket_file, self.bufsize, self.encoding)
        LOGGER.info("Starting")
        self.thread.start()
        LOGGER.info("Started")

    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Mapping[str, Any]:
        if not self.thread or not self.thread.running:
            LOGGER.error(f"Thread not properly initialized or running on component: {self.name}")
            raise NoCaptureToStoreError

        if self.thread.latest_reading is not None:
            return self.thread.latest_reading
        else:
            LOGGER.debug("No data received from Unix socket sensor")
            raise NoCaptureToStoreError

'''

    def send_data(self, command: str) -> None:
        try:
            # Send a command to the server to request data
            self.sock.sendall(command.encode(self.encoding))
        except socket.error as e:
            LOGGER.error(f"Failed to send data: {e}")

    def receive_data(self) -> Optional[str]:
        try:
            data = self.sock.recv(self.bufsize)
            self.buffer += data.decode(self.encoding)
            
            # Split the buffer on the newline character
            lines = self.buffer.split('\n')
            self.buffer = lines[-1]  # Save the last partial line back to the buffer

            # Return the latest complete line
            if len(lines) > 1:
                return lines[-2]
            return None
        except socket.timeout:
            LOGGER.debug("Socket timeout, no response received.")
            return None
        except socket.error as e:
            LOGGER.error(f"Failed to receive data: {e}")
            return f"Failed to receive data: {e}"

    @staticmethod
    def parse_response(response: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Error processing response: {e} - Response: {response}")
            return None
        
'''
