"""
MQTT Client module for subscribing to MQTT broker
"""
import paho.mqtt.client as mqtt
import ssl
import logging
from typing import Callable, Optional
from .config import MQTTConfig

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT Client for subscribing to broker and handling messages"""

    def __init__(self, config: MQTTConfig, on_message_callback: Callable):
        """
        Initialize MQTT Client

        Args:
            config: MQTT configuration
            on_message_callback: Callback function for handling received messages
        """
        self.config = config
        self.on_message_callback = on_message_callback
        self.client: Optional[mqtt.Client] = None
        self.connected = False

    def connect(self):
        """Connect to MQTT broker"""
        try:
            # Create MQTT client
            self.client = mqtt.Client(
                client_id=self.config.client_id,
                clean_session=self.config.clean_session
            )

            # Set username and password if provided
            if self.config.username and self.config.password:
                self.client.username_pw_set(self.config.username, self.config.password)
                logger.info("MQTT authentication configured")

            # Configure TLS if enabled
            if self.config.use_tls:
                self._configure_tls()

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_subscribe = self._on_subscribe

            # Connect to broker
            logger.info(f"Connecting to MQTT broker at {self.config.broker_host}:{self.config.broker_port}")
            self.client.connect(
                self.config.broker_host,
                self.config.broker_port,
                self.config.keepalive
            )

            # Start network loop in background thread
            self.client.loop_start()

            logger.info("MQTT client started")

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    def _configure_tls(self):
        """Configure TLS/SSL for secure connection"""
        try:
            tls_context = ssl.create_default_context()

            if self.config.ca_cert_path:
                tls_context.load_verify_locations(self.config.ca_cert_path)

            if self.config.client_cert_path and self.config.client_key_path:
                tls_context.load_cert_chain(
                    certfile=self.config.client_cert_path,
                    keyfile=self.config.client_key_path
                )

            self.client.tls_set_context(tls_context)
            logger.info("TLS/SSL configured for MQTT connection")

        except Exception as e:
            logger.error(f"Failed to configure TLS: {e}")
            raise

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            logger.info("Successfully connected to MQTT broker")

            # Subscribe to topics
            for topic in self.config.topics:
                client.subscribe(topic, qos=self.config.qos)
                logger.info(f"Subscribing to topic: {topic} (QoS {self.config.qos})")

        else:
            self.connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            logger.error(f"Failed to connect: {error_messages.get(rc, f'Unknown error ({rc})')}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker (code: {rc}). Will attempt to reconnect.")
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback when subscription is confirmed"""
        logger.info(f"Subscription confirmed (Message ID: {mid}, QoS: {granted_qos})")

    def _on_message(self, client, userdata, msg):
        """Callback when message is received"""
        try:
            logger.debug(f"Received message on topic '{msg.topic}': {msg.payload.decode('utf-8', errors='ignore')[:100]}")

            # Call the message handler callback
            self.on_message_callback(msg)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            logger.info("Disconnecting from MQTT broker")
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected
