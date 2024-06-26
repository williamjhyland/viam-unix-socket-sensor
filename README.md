# Viam Unix Socket Sensor Module
## Description

This project demonstrates the integration of a Viam sensor component with a Unix socket, enabling the sensor to read data from the socket given a socket file, a buffer, and an encoding. When enabled with data capture at an appropriate frequency, the sensor continuously polls the Unix socket at a configurable rate, capturing and processing data in a buffer. Complete messages are parsed as JSON and printed with precise timestamps, ensuring efficient and accurate data capture for advanced scenarios at a low-level interface.

## Viam Module

A module is a package with streamlined deployment to a Viam server. Modules can run alongside viam-server as separate processes, communicating with viam-server over UNIX sockets. A Viam Module can deploy and manage components such as a Viam Sensor.

## Viam Sensor

A sensor component sends can send information returned from the “GetReadings” method to the computer controlling the machine. We can customize capture data continuously, or only when specific conditions are met.

## Configuration

Generalized Attribute Guide
```json
{
  "socket_file": "/path/to/unix_socket",
  "bufsize": buffer size as int,
  "encoding": "encoding string",
}
```

Generic Example
```json
{
  "socket_file": "/tmp/unix_socket_example",
  "bufsize": 1024,
  "encoding": "utf-8",
}
```
