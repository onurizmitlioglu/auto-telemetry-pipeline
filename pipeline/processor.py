import psycopg2
from kafka import KafkaConsumer
from proto.can_frame_pb2 import CANFrame
from vehicle.can_codec import decode
import yaml
import time

def load_config(path: str = "config/settings.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

class Pipeline:
    def __init__(self):
        config = load_config()
        self.kafka_bootstrap = config["kafka"]["bootstrap"]
        self._consumer = None
        self._db = None
        self._vehicle_state = {}
        self._last_snapshot = time.time()
        self._snapshot_interval = 1.0
        self._active_anomalies = {}

        with open("config/anomaly_rules.yaml") as f:
            self._rules = yaml.safe_load(f)["rules"]

    def connect(self):
        config = load_config()
        
        self._consumer = KafkaConsumer(
            "can-raw",
            bootstrap_servers=self.kafka_bootstrap,
            group_id="pipeline-v3",
            auto_offset_reset="earliest",
            consumer_timeout_ms=1000,
        )
        
        pg = config["postgres"]
        self._db = psycopg2.connect(
            host=pg["host"],
            port=pg["port"],
            database=pg["database"],
            user=pg["user"],
            password=pg["password"],
        )
        print("[Pipeline] Connected to Kafka and PostgreSQL")
    
    def run(self):
        print("[Pipeline] Starting...")
        while True:
            for message in self._consumer:
                try:
                    frame = CANFrame()
                    frame.ParseFromString(message.value)
                    signals = decode(frame.arbitration_id, frame.data)
                    if signals:
                        if frame.vehicle_id not in self._vehicle_state:
                            self._vehicle_state[frame.vehicle_id] = {}
                        self._vehicle_state[frame.vehicle_id].update(signals)
                        
                except Exception as e:
                    print(f"[Pipeline] Error: {e}")

                now = time.time()
                if now - self._last_snapshot >= self._snapshot_interval:
                    for vehicle_id, state in self._vehicle_state.items():
                        self._write_snapshot(vehicle_id, state)
                    self._last_snapshot = now

    def _check_anomalies(self, vehicle_id: str, state: dict):
        if vehicle_id not in self._active_anomalies:
            self._active_anomalies[vehicle_id] = set()

        for rule in self._rules:
            rule_name = rule["rule"]
            conditions = rule["conditions"]
            logic = rule.get("logic", "AND")

            results = []
            for cond in conditions:
                value = state.get(cond["signal"])
                if value is None:
                    results.append(False)
                    continue
                if cond["operator"] == ">":
                    results.append(value > cond["threshold"])
                elif cond["operator"] == "<":
                    results.append(value < cond["threshold"])

            triggered = all(results) if logic == "AND" else any(results)

            if triggered and rule_name not in self._active_anomalies[vehicle_id]:
                self._active_anomalies[vehicle_id].add(rule_name)
                try:
                    cursor = self._db.cursor()
                    cursor.execute("""
                        INSERT INTO anomaly_events (
                            vehicle_id, ts, rule, severity,
                            signal, value, threshold, description
                        ) VALUES (%s, to_timestamp(%s), %s, %s, %s, %s, %s, %s)
                    """, (
                        vehicle_id,
                        time.time(),
                        rule_name,
                        rule["severity"],
                        conditions[0]["signal"],
                        state.get(conditions[0]["signal"]),
                        conditions[0]["threshold"],
                        rule["description"],
                    ))
                    self._db.commit()
                except Exception as e:
                    self._db.rollback()
                    print(f"[Pipeline] Anomaly write error: {e}")

            elif not triggered and rule_name in self._active_anomalies[vehicle_id]:
                self._active_anomalies[vehicle_id].discard(rule_name)

    def _write_snapshot(self, vehicle_id: str, state: dict):
        try:
            cursor = self._db.cursor()
            cursor.execute("""
                INSERT INTO telemetry (
                    vehicle_id, ts,
                    engine_rpm, throttle_pct, engine_load_pct,
                    coolant_temp_c, oil_temp_c, oil_pressure_bar,
                    maf_gs, map_kpa,
                    fuel_level_pct, fuel_consumption,
                    mil_status, dtc_count
                ) VALUES (
                    %s, to_timestamp(%s),
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s
                )
            """, (
                vehicle_id,
                time.time(),
                state.get("engine_rpm"),
                state.get("throttle_pct"),
                state.get("engine_load_pct"),
                state.get("coolant_temp_c"),
                state.get("oil_temp_c"),
                state.get("oil_pressure_bar"),
                state.get("maf_gs"),
                state.get("map_kpa"),
                state.get("fuel_level_pct"),
                state.get("fuel_consumption"),
                state.get("mil_status"),
                state.get("dtc_count"),
            ))
            self._db.commit()
            self._check_anomalies(vehicle_id, state)
        except Exception as e:
            self._db.rollback()
            print(f"[Pipeline] Anomaly write error: {e}")
