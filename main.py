"""
MQTT to IoT Hub Bridge - Main Entry Point
"""
import sys
import argparse
from mqtt_iot_bridge.config import ConfigManager
from mqtt_iot_bridge.logger import setup_logger
from mqtt_iot_bridge.bridge import MQTTIoTHubBridge


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="MQTT to IoT Hub Bridge - Stream data from MQTT broker to Azure IoT Hub"
    )
    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file (YAML or JSON)",
        default=None
    )
    parser.add_argument(
        "-l", "--log-level",
        help="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        default=None
    )
    parser.add_argument(
        "--log-file",
        help="Path to log file (optional)",
        default=None
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config_manager = ConfigManager(args.config)
        mqtt_config, iothub_config, bridge_config = config_manager.load_config()

        # Override log level if provided via CLI
        if args.log_level:
            bridge_config.log_level = args.log_level

        # Setup logging
        logger = setup_logger(
            name="mqtt_iot_bridge",
            level=bridge_config.log_level,
            log_file=args.log_file
        )

        logger.info("Configuration loaded successfully")

        # Create and start bridge
        bridge = MQTTIoTHubBridge(mqtt_config, iothub_config, bridge_config)
        bridge.start()

    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
