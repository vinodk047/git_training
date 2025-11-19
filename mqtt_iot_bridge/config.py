"""
Configuration management module for MQTT to IoT Hub bridge
"""
import os
import yaml
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MQTTConfig:
    """MQTT Broker Configuration"""
    broker_host: str
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str = "mqtt_iot_bridge"
    topics: list = None
    qos: int = 1
    clean_session: bool = True
    keepalive: int = 60
    use_tls: bool = False
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None

    def __post_init__(self):
        if self.topics is None:
            self.topics = ["#"]  # Default to all topics


@dataclass
class IoTHubConfig:
    """Azure IoT Hub Configuration"""
    connection_string: str
    device_id: str
    module_id: Optional[str] = None
    message_timeout: int = 10000
    protocol: str = "mqtt"  # mqtt, amqp, http


@dataclass
class BridgeConfig:
    """Bridge Configuration"""
    log_level: str = "INFO"
    message_batch_size: int = 1
    message_batch_timeout: int = 5
    enable_message_transformation: bool = False
    transformation_script: Optional[str] = None
    retry_enabled: bool = True
    retry_max_attempts: int = 3
    retry_backoff_factor: int = 2


class ConfigManager:
    """Manages configuration loading from various sources"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager

        Args:
            config_path: Path to configuration file (YAML or JSON)
        """
        self.config_path = config_path
        self.mqtt_config: Optional[MQTTConfig] = None
        self.iothub_config: Optional[IoTHubConfig] = None
        self.bridge_config: Optional[BridgeConfig] = None

    def load_config(self) -> tuple[MQTTConfig, IoTHubConfig, BridgeConfig]:
        """
        Load configuration from file or environment variables

        Returns:
            Tuple of (MQTTConfig, IoTHubConfig, BridgeConfig)
        """
        config_data = {}

        # Load from file if provided
        if self.config_path and os.path.exists(self.config_path):
            logger.info(f"Loading configuration from {self.config_path}")
            config_data = self._load_from_file(self.config_path)

        # Override with environment variables
        config_data = self._load_from_env(config_data)

        # Create configuration objects
        self.mqtt_config = self._create_mqtt_config(config_data.get("mqtt", {}))
        self.iothub_config = self._create_iothub_config(config_data.get("iothub", {}))
        self.bridge_config = self._create_bridge_config(config_data.get("bridge", {}))

        # Validate configuration
        self._validate_config()

        return self.mqtt_config, self.iothub_config, self.bridge_config

    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file"""
        with open(file_path, 'r') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                return yaml.safe_load(f) or {}
            elif file_path.endswith('.json'):
                return json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {file_path}")

    def _load_from_env(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Override configuration with environment variables"""

        # MQTT configuration from environment
        mqtt_config = config_data.get("mqtt", {})
        mqtt_config["broker_host"] = os.getenv("MQTT_BROKER_HOST", mqtt_config.get("broker_host"))
        mqtt_config["broker_port"] = int(os.getenv("MQTT_BROKER_PORT", mqtt_config.get("broker_port", 1883)))
        mqtt_config["username"] = os.getenv("MQTT_USERNAME", mqtt_config.get("username"))
        mqtt_config["password"] = os.getenv("MQTT_PASSWORD", mqtt_config.get("password"))
        mqtt_config["client_id"] = os.getenv("MQTT_CLIENT_ID", mqtt_config.get("client_id", "mqtt_iot_bridge"))

        topics_env = os.getenv("MQTT_TOPICS")
        if topics_env:
            mqtt_config["topics"] = [t.strip() for t in topics_env.split(",")]

        mqtt_config["qos"] = int(os.getenv("MQTT_QOS", mqtt_config.get("qos", 1)))
        mqtt_config["use_tls"] = os.getenv("MQTT_USE_TLS", str(mqtt_config.get("use_tls", False))).lower() == "true"

        # IoT Hub configuration from environment
        iothub_config = config_data.get("iothub", {})
        iothub_config["connection_string"] = os.getenv("IOTHUB_CONNECTION_STRING", iothub_config.get("connection_string"))
        iothub_config["device_id"] = os.getenv("IOTHUB_DEVICE_ID", iothub_config.get("device_id"))
        iothub_config["module_id"] = os.getenv("IOTHUB_MODULE_ID", iothub_config.get("module_id"))

        # Bridge configuration from environment
        bridge_config = config_data.get("bridge", {})
        bridge_config["log_level"] = os.getenv("LOG_LEVEL", bridge_config.get("log_level", "INFO"))
        bridge_config["retry_enabled"] = os.getenv("RETRY_ENABLED", str(bridge_config.get("retry_enabled", True))).lower() == "true"

        config_data["mqtt"] = mqtt_config
        config_data["iothub"] = iothub_config
        config_data["bridge"] = bridge_config

        return config_data

    def _create_mqtt_config(self, data: Dict[str, Any]) -> MQTTConfig:
        """Create MQTT configuration object"""
        return MQTTConfig(
            broker_host=data.get("broker_host", "localhost"),
            broker_port=data.get("broker_port", 1883),
            username=data.get("username"),
            password=data.get("password"),
            client_id=data.get("client_id", "mqtt_iot_bridge"),
            topics=data.get("topics", ["#"]),
            qos=data.get("qos", 1),
            clean_session=data.get("clean_session", True),
            keepalive=data.get("keepalive", 60),
            use_tls=data.get("use_tls", False),
            ca_cert_path=data.get("ca_cert_path"),
            client_cert_path=data.get("client_cert_path"),
            client_key_path=data.get("client_key_path")
        )

    def _create_iothub_config(self, data: Dict[str, Any]) -> IoTHubConfig:
        """Create IoT Hub configuration object"""
        return IoTHubConfig(
            connection_string=data.get("connection_string", ""),
            device_id=data.get("device_id", ""),
            module_id=data.get("module_id"),
            message_timeout=data.get("message_timeout", 10000),
            protocol=data.get("protocol", "mqtt")
        )

    def _create_bridge_config(self, data: Dict[str, Any]) -> BridgeConfig:
        """Create Bridge configuration object"""
        return BridgeConfig(
            log_level=data.get("log_level", "INFO"),
            message_batch_size=data.get("message_batch_size", 1),
            message_batch_timeout=data.get("message_batch_timeout", 5),
            enable_message_transformation=data.get("enable_message_transformation", False),
            transformation_script=data.get("transformation_script"),
            retry_enabled=data.get("retry_enabled", True),
            retry_max_attempts=data.get("retry_max_attempts", 3),
            retry_backoff_factor=data.get("retry_backoff_factor", 2)
        )

    def _validate_config(self):
        """Validate configuration"""
        if not self.mqtt_config.broker_host:
            raise ValueError("MQTT broker host is required")

        if not self.iothub_config.connection_string:
            raise ValueError("IoT Hub connection string is required")

        if not self.iothub_config.device_id:
            raise ValueError("IoT Hub device ID is required")

        logger.info("Configuration validated successfully")
