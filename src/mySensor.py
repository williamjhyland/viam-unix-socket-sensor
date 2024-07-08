import socket
import json
import threading
import time
import errno
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

class SocketThread(threading.Thread):

    def __init__(self, name, socket_file, bufsize, encoding):
        threading.Thread.__init__(self)
        # Thread Info
        self.name = name
        self.running = False
        self.connected = False
        self.lock = threading.Lock()
        # Socket Info
        self.client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_file = socket_file
        self.bufsize = bufsize
        self.encoding = encoding
        self.reconnect_interval = .1
        self.latest_reading = None
        self.buffer = ""
    
    def run(self):
        LOGGER.info(f"Starting thread of {self.name}")
        self.running = True
        while self.running:
            LOGGER.debug(f"Trying Connection -- self.Connected status is {self.connected}")
            self.connect_to_server()
            time.sleep(self.reconnect_interval)

    def shutdown(self):
        LOGGER.info('Shutting down thread.')
        self.running = False
        if self.client_socket:
            self.client_socket.close()

    def loop(self):
        while self.running and self.connected:
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
                self.connected = False

    def connect_to_server(self):
        try:
            self.client_socket.connect(self.socket_file)
            LOGGER.info('Connected to Unix socket server')
            self.connected = True
        except ConnectionRefusedError as cre:
            LOGGER.error(f"ConnectionRefusedError: is the server online? {cre}")
            self.connected = False        
        except OSError as ose:
            if ose.errno == errno.ENOENT:  # Error number for "No such file or directory"
                LOGGER.error(f"OS error (No such file or directory): {ose}")
                self.connected = False
            elif ose.errno == 56:  # Error number for "Socket is already connected"
                LOGGER.debug(f"OS error (Socket is already connected): {ose}")
                self.connected = True
            else:
                LOGGER.error(f"OS error: {ose}")
                self.connected = False

        self.loop()

    def receive_data(self) -> Optional[str]:
        while self.running:
            try:
                data = self.client_socket.recv(self.bufsize)
                self.buffer += data.decode(self.encoding)
                lines = self.buffer.split('\n')
                self.buffer = lines[-1]
                if len(lines) > 1:
                    with self.lock:
                        self.latest_reading = self.parse_response(lines[-2])
            except socket.error as e:
                LOGGER.error(f"Failed to receive data: {e}")
                self.connected = False

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
        self.thread: Optional[SocketThread] = None
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
        self.thread = SocketThread(self.name, self.socket_file, self.bufsize, self.encoding)
        self.thread.start()

    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Mapping[str, Any]:
        if not self.thread:
            LOGGER.error(f"Thread not properly initialized on component: {self.name}. Shutting down.")
            raise NoCaptureToStoreError
        
        if not self.thread.connected:
            LOGGER.error(f"Socket not connected on component: {self.name}.")
            raise NoCaptureToStoreError

        if self.thread.latest_reading is not None:
            return self.thread.latest_reading
        else:
            LOGGER.info("No data received from Unix socket sensor")
            raise NoCaptureToStoreError
        
    async def close(self):
        LOGGER.info("Closing sensor and shutting down thread")
        if self.thread:
            self.thread.shutdown()
