import time
import threading
from kafka import KafkaProducer, KafkaConsumer
from vehicle.ecu.engine_ecu import EngineECU
from proto.can_frame_pb2 import CANFrame
import yaml

def load_config(path: str = "config/settings.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


class TCU:
    def __init__(self, vehicle_id: str):
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

    def connect(self):
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
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self._producer:
            self._producer.flush()
            self._producer.close()
        print(f"[TCU {self.vehicle_id}] Stopped")
        