"""
MQTT smart-home bridge for Dobby HUD.

Subscribes to device state topics and publishes commands.
Devices are mapped by ID -> MQTT topic pattern.

Env vars:
    MQTT_BROKER   (default: localhost)
    MQTT_PORT     (default: 1883)
    MQTT_USERNAME (optional)
    MQTT_PASSWORD (optional)
    MQTT_PREFIX   (default: homeassistant)
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


class MQTTBridge:
    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        username: str = "",
        password: str = "",
        prefix: str = "homeassistant",
        on_state_change: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.prefix = prefix
        self.on_state_change = on_state_change

        self._client: Optional[mqtt.Client] = None
        self._connected = threading.Event()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Connection                                                          #
    # ------------------------------------------------------------------ #
    def connect(self) -> bool:
        if mqtt is None:
            logger.warning("paho-mqtt not installed; MQTT disabled")
            return False

        self._client = mqtt.Client(client_id="dobby-hud", callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        if self.username:
            self._client.username_pw_set(self.username, self.password)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        try:
            self._client.connect(self.broker, self.port, keepalive=60)
            self._client.loop_start()
            return self._connected.wait(timeout=5)
        except Exception as exc:
            logger.warning("MQTT connect failed: %s", exc)
            return False

    def disconnect(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    # ------------------------------------------------------------------ #
    # Internal callbacks                                                  #
    # ------------------------------------------------------------------ #
    def _on_connect(self, client: Any, userdata: Any, flags: Dict[str, Any], reason_code: Any, properties: Any = None) -> None:
        logger.info("MQTT connected to %s:%s", self.broker, self.port)
        self._connected.set()

    def _on_disconnect(self, client: Any, userdata: Any, flags: Dict[str, Any], reason_code: Any, properties: Any = None) -> None:
        logger.warning("MQTT disconnected")
        self._connected.clear()

    def _on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode() or "{}")
            device_id = topic.split("/")[-1]
            if self.on_state_change:
                self.on_state_change(device_id, payload)
        except Exception as exc:
            logger.debug("MQTT message error: %s", exc)

    # ------------------------------------------------------------------ #
    # Publish command                                                     #
    # ------------------------------------------------------------------ #
    def publish(self, device_id: str, payload: Dict[str, Any]) -> None:
        if not self.is_connected or not self._client:
            logger.debug("MQTT not connected, skipping publish for %s", device_id)
            return
        topic = f"{self.prefix}/switch/{device_id}/set"
        try:
            self._client.publish(topic, json.dumps(payload), retain=True)
            logger.debug("MQTT publish -> %s: %s", topic, payload)
        except Exception as exc:
            logger.warning("MQTT publish failed: %s", exc)

    # ------------------------------------------------------------------ #
    # Subscribe to device state topics                                    #
    # ------------------------------------------------------------------ #
    def subscribe_device(self, device_id: str) -> None:
        if not self.is_connected or not self._client:
            return
        topic = f"{self.prefix}/switch/{device_id}/state"
        try:
            self._client.subscribe(topic)
            logger.debug("MQTT subscribed to %s", topic)
        except Exception as exc:
            logger.warning("MQTT subscribe failed: %s", exc)


def create_bridge_from_env(on_state_change: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> Optional[MQTTBridge]:
    broker = os.getenv("MQTT_BROKER", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    username = os.getenv("MQTT_USERNAME", "")
    password = os.getenv("MQTT_PASSWORD", "")
    prefix = os.getenv("MQTT_PREFIX", "homeassistant")

    bridge = MQTTBridge(
        broker=broker,
        port=port,
        username=username,
        password=password,
        prefix=prefix,
        on_state_change=on_state_change,
    )
    if bridge.connect():
        return bridge
    return None
