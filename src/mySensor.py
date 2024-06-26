import socket
import json
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

class MySensor(Sensor):
    MODEL: ClassVar[Model] = Model(ModelFamily("bill", "unixsocket"), "sensor")
    REQUIRED_ATTRIBUTES = ["socket_file", "bufsize", "encoding"]
    
    def __init__(self, name: str):
        super().__init__(name)
        self.socket_file: str = ""
        self.bufsize: int = 1024
        self.encoding: str = "utf-8"
        self.process_response: bool = False
        self.sock: Optional[socket.socket] = None
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
        
        # Close socket if already open
        if self.sock:
            self.sock.close()

        # Parse dictionary from the configuration attributes
        config_dict = struct_to_dict(config.attributes)

        # Set attributes from the configuration
        self.socket_file = config_dict["socket_file"]
        self.bufsize = int(config_dict["bufsize"])
        self.encoding = config_dict["encoding"]

        # Initialize and configure the Unix socket
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(1)

        # Connect to the Unix socket server
        try:
            self.sock.connect(self.socket_file)
        except socket.error as e:
            LOGGER.error(f"Failed to connect to Unix socket: {e}")
            raise 

    async def get_readings(self, extra: Optional[Dict[str, Any]] = None, **kwargs) -> Mapping[str, Any]:
        # Ensure the socket is initialized
        if not self.sock:
            raise NoCaptureToStoreError("Socket not initialized")

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
        


