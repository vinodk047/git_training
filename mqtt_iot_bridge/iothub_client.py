"""
Azure IoT Hub Client module for sending messages to IoT Hub
"""
import logging
import time
import json
from typing import Dict, Any, Optional
from azure.iot.device import IoTHubDeviceClient, Message
from azure.iot.device.exceptions import ConnectionFailedError, CredentialError
from .config import IoTHubConfig

logger = logging.getLogger(__name__)


class IoTHubClient:
    """Azure IoT Hub Client for sending messages"""

    def __init__(self, config: IoTHubConfig):
        """
        Initialize IoT Hub Client

        Args:
            config: IoT Hub configuration
        """
        self.config = config
        self.client: Optional[IoTHubDeviceClient] = None
        self.connected = False

    def connect(self):
        """Connect to Azure IoT Hub"""
        try:
            logger.info("Connecting to Azure IoT Hub")

            # Create IoT Hub device client from connection string
            self.client = IoTHubDeviceClient.create_from_connection_string(
                self.config.connection_string
            )

            # Connect to IoT Hub
            self.client.connect()
            self.connected = True

            logger.info(f"Successfully connected to IoT Hub (Device ID: {self.config.device_id})")

        except CredentialError as e:
            logger.error(f"Invalid credentials for IoT Hub: {e}")
            raise
        except ConnectionFailedError as e:
            logger.error(f"Failed to connect to IoT Hub: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to IoT Hub: {e}")
            raise

    def send_message(self, payload: str, properties: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send message to IoT Hub

        Args:
            payload: Message payload (string or JSON)
            properties: Optional message properties/metadata

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.connected or not self.client:
            logger.error("Not connected to IoT Hub")
            return False

        try:
            # Create message
            message = Message(payload)

            # Set message properties if provided
            if properties:
                for key, value in properties.items():
                    message.custom_properties[key] = str(value)

            # Set content encoding and type
            message.content_encoding = "utf-8"
            message.content_type = "application/json"

            # Send message
            logger.debug(f"Sending message to IoT Hub: {payload[:100]}...")
            self.client.send_message(message)

            logger.debug("Message sent successfully to IoT Hub")
            return True

        except Exception as e:
            logger.error(f"Failed to send message to IoT Hub: {e}")
            return False

    def send_message_with_retry(
        self,
        payload: str,
        properties: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        backoff_factor: int = 2
    ) -> bool:
        """
        Send message to IoT Hub with retry logic

        Args:
            payload: Message payload
            properties: Optional message properties
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff factor

        Returns:
            True if message sent successfully, False otherwise
        """
        for attempt in range(max_retries):
            try:
                if self.send_message(payload, properties):
                    return True

                # If send failed, wait before retry
                if attempt < max_retries - 1:
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"Message send failed, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)

            except Exception as e:
                logger.error(f"Error sending message (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = backoff_factor ** attempt
                    time.sleep(wait_time)

        logger.error(f"Failed to send message after {max_retries} attempts")
        return False

    def disconnect(self):
        """Disconnect from Azure IoT Hub"""
        if self.client:
            try:
                logger.info("Disconnecting from Azure IoT Hub")
                self.client.disconnect()
                self.connected = False
                logger.info("Disconnected from Azure IoT Hub")
            except Exception as e:
                logger.error(f"Error disconnecting from IoT Hub: {e}")

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected

    def shutdown(self):
        """Shutdown IoT Hub client"""
        try:
            if self.client:
                self.disconnect()
                self.client.shutdown()
                logger.info("IoT Hub client shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down IoT Hub client: {e}")
