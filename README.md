# MQTT to IoT Hub Bridge

A modular, parameterized Python bridge to connect MQTT Broker and stream data to Azure IoT Hub. This solution provides a robust, containerized bridge for seamlessly forwarding MQTT messages to Azure IoT Hub with full configurability and enterprise-grade features.

## Features

- **Modular Architecture**: Clean separation of concerns with dedicated modules for MQTT, IoT Hub, configuration, and bridging logic
- **Parameterized Configuration**: Support for YAML, JSON config files and environment variables
- **Robust Error Handling**: Automatic retry logic with exponential backoff
- **Message Transformation**: Enrich MQTT messages with metadata before forwarding to IoT Hub
- **TLS/SSL Support**: Secure MQTT connections with certificate-based authentication
- **Statistics & Monitoring**: Built-in statistics tracking and periodic logging
- **Containerized**: Docker and Docker Compose support for easy deployment
- **Graceful Shutdown**: Proper signal handling for clean shutdowns
- **Logging**: Comprehensive logging with configurable levels

## Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌──────────────┐
│             │         │                  │         │              │
│  MQTT       │◄────────┤  MQTT-IoT Hub   │────────►│  Azure       │
│  Broker     │         │  Bridge          │         │  IoT Hub     │
│             │         │                  │         │              │
└─────────────┘         └──────────────────┘         └──────────────┘
                               │
                               │
                        ┌──────▼──────┐
                        │             │
                        │ Message     │
                        │ Queue       │
                        │             │
                        └─────────────┘
```

## Project Structure

```
mqtt-iot-hub-bridge/
├── mqtt_iot_bridge/          # Main package
│   ├── __init__.py           # Package initialization
│   ├── config.py             # Configuration management
│   ├── logger.py             # Logging setup
│   ├── mqtt_client.py        # MQTT client wrapper
│   ├── iothub_client.py      # IoT Hub client wrapper
│   └── bridge.py             # Main bridge logic
├── main.py                   # Entry point
├── config.yaml               # Configuration file (YAML)
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Docker Compose configuration
├── .dockerignore             # Docker ignore patterns
└── README.md                 # This file
```

## Prerequisites

- Python 3.11+
- Azure IoT Hub instance
- MQTT Broker (e.g., Mosquitto, HiveMQ, AWS IoT Core)
- Docker (optional, for containerized deployment)

## Installation

### Option 1: Local Python Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mqtt-iot-hub-bridge
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Option 2: Docker Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mqtt-iot-hub-bridge
```

2. Build Docker image:
```bash
docker build -t mqtt-iot-bridge:latest .
```

## Configuration

### Method 1: Configuration File (config.yaml)

Edit `config.yaml` with your settings:

```yaml
mqtt:
  broker_host: "your-mqtt-broker.com"
  broker_port: 1883
  username: "mqtt_user"
  password: "mqtt_password"
  topics:
    - "sensors/#"
    - "devices/#"
  qos: 1

iothub:
  connection_string: "HostName=<your-hub>.azure-devices.net;DeviceId=<device>;SharedAccessKey=<key>"
  device_id: "mqtt-bridge-device"

bridge:
  log_level: "INFO"
  retry_enabled: true
  retry_max_attempts: 3
```

### Method 2: Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your settings:
```bash
MQTT_BROKER_HOST=your-mqtt-broker.com
MQTT_BROKER_PORT=1883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_password
MQTT_TOPICS=sensors/#,devices/#

IOTHUB_CONNECTION_STRING=HostName=<your-hub>.azure-devices.net;DeviceId=<device>;SharedAccessKey=<key>
IOTHUB_DEVICE_ID=mqtt-bridge-device

LOG_LEVEL=INFO
```

### Configuration Priority

Environment variables override configuration file settings:
1. Environment variables (highest priority)
2. Configuration file
3. Default values (lowest priority)

## Usage

### Running Locally

#### With Configuration File:
```bash
python main.py -c config.yaml
```

#### With Environment Variables:
```bash
export MQTT_BROKER_HOST=mqtt.example.com
export IOTHUB_CONNECTION_STRING="HostName=..."
python main.py
```

#### With Custom Log Level:
```bash
python main.py -c config.yaml --log-level DEBUG
```

#### With Log File:
```bash
python main.py -c config.yaml --log-file bridge.log
```

### Running with Docker

#### Using Docker Run:
```bash
docker run -d \
  --name mqtt-iot-bridge \
  -e MQTT_BROKER_HOST=mqtt.example.com \
  -e MQTT_BROKER_PORT=1883 \
  -e IOTHUB_CONNECTION_STRING="HostName=..." \
  -e IOTHUB_DEVICE_ID=mqtt-bridge-device \
  mqtt-iot-bridge:latest
```

#### Using Docker Compose:
```bash
# Edit .env file with your settings
cp .env.example .env
nano .env

# Start the bridge
docker-compose up -d

# View logs
docker-compose logs -f mqtt-iot-bridge

# Stop the bridge
docker-compose down
```

#### With Local MQTT Broker (Testing):
```bash
# Start both bridge and local Mosquitto broker
docker-compose --profile testing up -d

# This starts both services:
# - mosquitto: Local MQTT broker on port 1883
# - mqtt-iot-bridge: Bridge connecting to local broker
```

## Azure IoT Hub Setup

### 1. Create IoT Hub Device

```bash
# Using Azure CLI
az iot hub device-identity create \
  --hub-name <your-hub-name> \
  --device-id mqtt-bridge-device

# Get connection string
az iot hub device-identity connection-string show \
  --hub-name <your-hub-name> \
  --device-id mqtt-bridge-device
```

### 2. Configure Connection String

Use the connection string from above in your configuration:
- In `config.yaml`: `iothub.connection_string`
- In `.env`: `IOTHUB_CONNECTION_STRING`

## MQTT Broker Setup

### Using Mosquitto (Local Testing)

1. Install Mosquitto:
```bash
# Ubuntu/Debian
sudo apt-get install mosquitto mosquitto-clients

# macOS
brew install mosquitto

# Or use Docker (included in docker-compose with --profile testing)
```

2. Test publishing:
```bash
# Publish test message
mosquitto_pub -h localhost -t "sensors/temperature" -m '{"temperature": 25.5, "humidity": 60}'

# Subscribe to verify
mosquitto_sub -h localhost -t "sensors/#"
```

## Message Flow

1. **MQTT Message Received**: Bridge subscribes to configured topics
2. **Message Queued**: Incoming messages are queued for processing
3. **Message Transformation**: Messages are enriched with metadata:
   ```json
   {
     "mqtt_topic": "sensors/temperature",
     "mqtt_qos": 1,
     "mqtt_retain": false,
     "timestamp": 1637012345.678,
     "payload": {
       "temperature": 25.5,
       "humidity": 60
     }
   }
   ```
4. **Send to IoT Hub**: Transformed message sent with custom properties
5. **Retry on Failure**: Automatic retry with exponential backoff if enabled

## Monitoring

### Statistics Logging

The bridge logs statistics every minute:
```
============================================================
Bridge Statistics:
  Uptime: 3600 seconds
  Messages Received (MQTT): 1250
  Messages Sent (IoT Hub): 1248
  Messages Failed: 2
  Queue Size: 0
  MQTT Connected: True
  IoT Hub Connected: True
============================================================
```

### Health Check

Docker health check is configured to monitor bridge health:
```bash
docker inspect --format='{{.State.Health.Status}}' mqtt-iot-bridge
```

## Advanced Features

### TLS/SSL Configuration

For secure MQTT connections:

```yaml
mqtt:
  use_tls: true
  ca_cert_path: "/path/to/ca.crt"
  client_cert_path: "/path/to/client.crt"
  client_key_path: "/path/to/client.key"
```

### Topic Filtering

Subscribe to specific topics:

```yaml
mqtt:
  topics:
    - "factory/line1/sensors/#"
    - "factory/line2/sensors/#"
    - "alerts/critical"
```

### Retry Configuration

Configure retry behavior:

```yaml
bridge:
  retry_enabled: true
  retry_max_attempts: 5
  retry_backoff_factor: 2  # Wait time: 2^attempt seconds
```

## Troubleshooting

### Connection Issues

**MQTT Connection Failed:**
- Verify broker host and port
- Check username/password if authentication is enabled
- Ensure firewall allows connection
- Test with `mosquitto_sub` or MQTT client

**IoT Hub Connection Failed:**
- Verify connection string format
- Check device exists in IoT Hub
- Ensure device is enabled
- Verify network connectivity to Azure

### Message Not Forwarding

- Check log level is set to DEBUG for detailed logging
- Verify MQTT topics are being subscribed correctly
- Check queue size in statistics
- Review failed message count

### Docker Issues

**Container won't start:**
```bash
# Check logs
docker logs mqtt-iot-bridge

# Verify environment variables
docker exec mqtt-iot-bridge env

# Check configuration
docker exec mqtt-iot-bridge cat /app/config.yaml
```

## Performance Tuning

### Message Batching (Future Enhancement)

Currently processes messages individually. Batching can be added:
```yaml
bridge:
  message_batch_size: 10
  message_batch_timeout: 5
```

### Queue Management

For high-throughput scenarios:
- Increase queue size if needed (modify code)
- Use multiple worker threads
- Implement message prioritization

## Security Best Practices

1. **Use TLS/SSL**: Enable for both MQTT and IoT Hub
2. **Secure Credentials**: Use environment variables or secrets management
3. **Non-root Container**: Docker image runs as non-root user
4. **Network Isolation**: Use Docker networks for isolation
5. **Regular Updates**: Keep dependencies updated

## Development

### Running Tests (Future Enhancement)

```bash
pytest tests/
```

### Code Structure

- `config.py`: Configuration loading and validation
- `mqtt_client.py`: MQTT connection and subscription
- `iothub_client.py`: IoT Hub message sending
- `bridge.py`: Main orchestration logic
- `logger.py`: Logging configuration

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Submit pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues and documentation
- Review Azure IoT Hub documentation

## Changelog

### v1.0.0 (Initial Release)
- Modular architecture with separate MQTT and IoT Hub clients
- Configuration via YAML, JSON, or environment variables
- Automatic retry with exponential backoff
- Message transformation and enrichment
- Docker and Docker Compose support
- Comprehensive logging and statistics
- TLS/SSL support for MQTT
- Graceful shutdown handling

## Acknowledgments

- Built with [paho-mqtt](https://github.com/eclipse/paho.mqtt.python)
- Azure IoT SDK for Python
- Docker containerization

---

**Author**: IoT Developer
**Version**: 1.0.0
**Last Updated**: 2025
