"""
Main Bridge module connecting MQTT and IoT Hub
"""
import logging
import signal
import sys
import json
import time
from typing import Optional
from queue import Queue, Empty
from threading import Thread, Event
from paho.mqtt.client import MQTTMessage

from .config import MQTTConfig, IoTHubConfig, BridgeConfig
from .mqtt_client import MQTTClient
from .iothub_client import IoTHubClient

logger = logging.getLogger(__name__)


class MQTTIoTHubBridge:
    """Bridge between MQTT Broker and Azure IoT Hub"""

    def __init__(
        self,
        mqtt_config: MQTTConfig,
        iothub_config: IoTHubConfig,
        bridge_config: BridgeConfig
    ):
        """
        Initialize the bridge

        Args:
            mqtt_config: MQTT configuration
            iothub_config: IoT Hub configuration
            bridge_config: Bridge configuration
        """
        self.mqtt_config = mqtt_config
        self.iothub_config = iothub_config
        self.bridge_config = bridge_config

        # Initialize clients
        self.mqtt_client: Optional[MQTTClient] = None
        self.iothub_client: Optional[IoTHubClient] = None

        # Message queue for processing
        self.message_queue = Queue()

        # Control flags
        self.running = Event()
        self.shutdown_requested = Event()

        # Statistics
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "messages_failed": 0,
            "start_time": None
        }

        # Worker thread
        self.worker_thread: Optional[Thread] = None

    def start(self):
        """Start the bridge"""
        try:
            logger.info("=" * 60)
            logger.info("Starting MQTT to IoT Hub Bridge")
            logger.info("=" * 60)

            # Register signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            # Initialize and connect MQTT client
            logger.info("Initializing MQTT client...")
            self.mqtt_client = MQTTClient(self.mqtt_config, self._on_mqtt_message)
            self.mqtt_client.connect()

            # Initialize and connect IoT Hub client
            logger.info("Initializing IoT Hub client...")
            self.iothub_client = IoTHubClient(self.iothub_config)
            self.iothub_client.connect()

            # Start message processing worker
            self.running.set()
            self.worker_thread = Thread(target=self._message_processor, daemon=True)
            self.worker_thread.start()

            self.stats["start_time"] = time.time()

            logger.info("=" * 60)
            logger.info("Bridge is running. Press Ctrl+C to stop.")
            logger.info("=" * 60)

            # Keep the main thread alive
            while not self.shutdown_requested.is_set():
                time.sleep(1)

                # Periodically log statistics
                if int(time.time()) % 60 == 0:  # Every minute
                    self._log_statistics()

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Error starting bridge: {e}")
            raise
        finally:
            self.stop()

    def stop(self):
        """Stop the bridge"""
        logger.info("Stopping bridge...")

        # Set shutdown flag
        self.shutdown_requested.set()
        self.running.clear()

        # Wait for worker thread to finish
        if self.worker_thread and self.worker_thread.is_alive():
            logger.info("Waiting for worker thread to finish...")
            self.worker_thread.join(timeout=5)

        # Disconnect clients
        if self.mqtt_client:
            self.mqtt_client.disconnect()

        if self.iothub_client:
            self.iothub_client.shutdown()

        # Log final statistics
        self._log_statistics()

        logger.info("Bridge stopped successfully")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self.shutdown_requested.set()

    def _on_mqtt_message(self, message: MQTTMessage):
        """
        Callback for MQTT messages

        Args:
            message: MQTT message
        """
        try:
            self.stats["messages_received"] += 1

            # Add message to queue for processing
            self.message_queue.put({
                "topic": message.topic,
                "payload": message.payload.decode("utf-8", errors="ignore"),
                "qos": message.qos,
                "retain": message.retain,
                "timestamp": time.time()
            })

        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")

    def _message_processor(self):
        """Process messages from queue and send to IoT Hub"""
        logger.info("Message processor started")

        while self.running.is_set():
            try:
                # Get message from queue with timeout
                try:
                    msg_data = self.message_queue.get(timeout=1)
                except Empty:
                    continue

                # Transform message if needed
                transformed_payload = self._transform_message(msg_data)

                # Prepare message properties
                properties = {
                    "mqtt_topic": msg_data["topic"],
                    "mqtt_qos": msg_data["qos"],
                    "source": "mqtt_bridge",
                    "timestamp": msg_data["timestamp"]
                }

                # Send to IoT Hub
                success = False
                if self.bridge_config.retry_enabled:
                    success = self.iothub_client.send_message_with_retry(
                        transformed_payload,
                        properties,
                        self.bridge_config.retry_max_attempts,
                        self.bridge_config.retry_backoff_factor
                    )
                else:
                    success = self.iothub_client.send_message(transformed_payload, properties)

                # Update statistics
                if success:
                    self.stats["messages_sent"] += 1
                else:
                    self.stats["messages_failed"] += 1
                    logger.warning(f"Failed to send message from topic '{msg_data['topic']}'")

                # Mark task as done
                self.message_queue.task_done()

            except Exception as e:
                logger.error(f"Error processing message: {e}")

        logger.info("Message processor stopped")

    def _transform_message(self, msg_data: dict) -> str:
        """
        Transform MQTT message before sending to IoT Hub

        Args:
            msg_data: Message data dictionary

        Returns:
            Transformed message payload as string
        """
        try:
            # Try to parse as JSON
            try:
                payload_json = json.loads(msg_data["payload"])
                is_json = True
            except json.JSONDecodeError:
                payload_json = {"data": msg_data["payload"]}
                is_json = False

            # Add metadata
            transformed = {
                "mqtt_topic": msg_data["topic"],
                "mqtt_qos": msg_data["qos"],
                "mqtt_retain": msg_data["retain"],
                "timestamp": msg_data["timestamp"],
                "payload": payload_json if is_json else msg_data["payload"]
            }

            return json.dumps(transformed)

        except Exception as e:
            logger.error(f"Error transforming message: {e}")
            # Return original payload wrapped in JSON
            return json.dumps({
                "mqtt_topic": msg_data["topic"],
                "payload": msg_data["payload"],
                "error": str(e)
            })

    def _log_statistics(self):
        """Log bridge statistics"""
        uptime = time.time() - self.stats["start_time"] if self.stats["start_time"] else 0

        logger.info("=" * 60)
        logger.info("Bridge Statistics:")
        logger.info(f"  Uptime: {uptime:.0f} seconds")
        logger.info(f"  Messages Received (MQTT): {self.stats['messages_received']}")
        logger.info(f"  Messages Sent (IoT Hub): {self.stats['messages_sent']}")
        logger.info(f"  Messages Failed: {self.stats['messages_failed']}")
        logger.info(f"  Queue Size: {self.message_queue.qsize()}")
        logger.info(f"  MQTT Connected: {self.mqtt_client.is_connected() if self.mqtt_client else False}")
        logger.info(f"  IoT Hub Connected: {self.iothub_client.is_connected() if self.iothub_client else False}")
        logger.info("=" * 60)
