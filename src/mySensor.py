import socket
import json
import threading
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

    def __init__(self, threadID, name, socket_file):
        threading.Thread.__init__(self)
        # Thread Info
        self.threadID = threadID
        self.name = name
        self.running = False
        self.lock = threading.Lock()
        # Socket Info
        self.client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_file = socket_file

    def run(self):
        LOGGER.info(f"Starting {self.name}")
        self.running = True
        self.loop()

    def shutdown(self):
        LOGGER.info('shutting down Socket Client & joining threads')
        self.running = False
        self.client_socket.close()
        self.join()

    def loop(self):
        LOGGER.info(f'Attempting connection on client to host...')
        while self.running:
            try:
                self.client_socket.connect(self.socket_file)
                while self.running:
                    # Add your data handling code here
                    pass
            except socket.error as e:
                LOGGER.error(f"Socket error: {e}")
                self.shutdown()

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

    def parse_response(response: str) -> Optional[Dict[str, Any]]:
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
        self.sock: Optional[myThread] = None
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
        self.thread = myThread(self.name, f"{self.name}_thread", self.socket_file, self.bufsize, self.encoding)
        self.thread.start()

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(1)

        # Connect to the Unix socket server
        try:
            self.sock.connect(self.socket_file)
        except socket.error as e:
            self.sock = None
            if e.errno == 61:  # Connection refused
                LOGGER.error(f"Failed to connect to Unix socket: {e}. Is the server initialized?")
            else:
                LOGGER.error(f"Failed to connect to Unix socket: {e}")

    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Mapping[str, Any]:
        # Ensure the socket is initialized if not call reconfigure
        if not self.thread or not self.thread.running:
            LOGGER.error(f"Thread not properly initialized or running. Closing component: {self.name}")
            raise NoCaptureToStoreError

        readings = {}

        try:
            # Send a request to the server
            # self.send_data('REQUEST DATA')  # This ensures synchronization and control over data requests

            # Continuously read data from the server until the latest complete line is received
            latest_reading = None
            while latest_reading is None:
                response = self.receive_data()
                if response:
                    latest_reading = self.parse_response(response)

            if latest_reading:
                readings = latest_reading
            
            return readings  # Return the latest reading directly

        except socket.timeout:
            LOGGER.debug("Failed to receive data from Unix socket sensor")
            return {}

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
