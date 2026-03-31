import time
import threading
from kafka import KafkaProducer, KafkaConsumer
from vehicle.ecu.engine_ecu import EngineECU
from proto.can_frame_pb2 import CANFrame
import yaml
import json

import paho.mqtt.client as mqtt
from ota.firmware import FirmwareManager, generate_key_pair

def load_config(path: str = "config/settings.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


class TCU:
    def __init__(self, vehicle_id: str, public_key=None):
        config = load_config()
        self.vehicle_id = vehicle_id
        self._tick_interval = config["ecu"]["engine"]["tick_interval_ms"] / 1000.0
        self.kafka_bootstrap = config["kafka"]["bootstrap"]
        self._connect_retries = config["kafka"]["connect_retries"]
        self._connect_delay = config["kafka"]["connect_delay_s"]
        self.engine_ecu = EngineECU(fault_injection=True)
        self._producer = None
        self._consumer = None
        self._running = False
        self._public_key = public_key
        self._firmware_manager = FirmwareManager(vehicle_id, public_key) if public_key else None
        self._mqtt_client = mqtt.Client()

    def connect(self):
        self._mqtt_client.on_message = self._on_ota_command
        self._mqtt_client.connect("localhost", 1883)
        self._mqtt_client.subscribe(f"ota/commands/{self.vehicle_id}")
        self._mqtt_client.loop_start()
         
        for attempt in range(self._connect_retries):
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.kafka_bootstrap,
                    acks="all",
                )
                self._consumer = KafkaConsumer(
                    "ota-commands",
                    bootstrap_servers=self.kafka_bootstrap,
                    group_id=f"tcu-{self.vehicle_id}",
                    auto_offset_reset="latest",
                    consumer_timeout_ms=50,
                )
                print(f"[TCU {self.vehicle_id}] Connected to Kafka")
                return
            except Exception as e:
                print(f"[TCU {self.vehicle_id}] Kafka not ready, retry {attempt+1}/{self._connect_retries}")
                time.sleep(self._connect_delay)
        raise RuntimeError("TCU: cannot connect to Kafka")
    
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[TCU {self.vehicle_id}] Started")

    def _run_loop(self):
        while self._running:
            tick_start = time.time()
            
            # Get CAN frames from ECUs
            frames = self.engine_ecu.tick()
            
            # Send each frame to Kafka
            for can_id, data in frames:
                self._send_frame(can_id, data)
            
            # Update tick interval
            elapsed = time.time() - tick_start
            sleep_time = max(0, self._tick_interval - elapsed)
            time.sleep(sleep_time)

    def _send_frame(self, can_id: int, data: bytes):
        frame = CANFrame(
            vehicle_id=self.vehicle_id,
            vehicle_timestamp=time.time(),
            arbitration_id=can_id,
            dlc=len(data),
            data=data,
        )
        self._producer.send(
            "can-raw",
            key=self.vehicle_id.encode(),
            value=frame.SerializeToString(),
        )

    def _on_ota_command(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print(f"[TCU {self.vehicle_id}] OTA command: {payload.get('cmd_type')} for {payload.get('ecu_target')}")
            
            if self._firmware_manager:
                self._firmware_manager.handle_command(payload, self._send_ota_status)
        except Exception as e:
            print(f"[TCU {self.vehicle_id}] OTA command error: {e}")


    def _send_ota_status(self, campaign_id: str, session_id: str, status_code: str,
                      progress_pct: int = 0, error_code: int = 0, fw_version: str = ""):
        payload = {
            "vehicle_id": self.vehicle_id,
            "campaign_id": campaign_id,
            "session_id": session_id,
            "status_code": status_code,
            "progress_pct": progress_pct,
            "error_code": error_code,
            "fw_version": fw_version,
        }
        self._mqtt_client.publish(f"ota/status/{self.vehicle_id}", json.dumps(payload))
        print(f"[TCU {self.vehicle_id}] → status={status_code} progress={progress_pct}%")


    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self._producer:
            self._producer.flush()
            self._producer.close()
        print(f"[TCU {self.vehicle_id}] Stopped")
        