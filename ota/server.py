import time
import json
import paho.mqtt.client as mqtt
import psycopg2
import yaml
from ota.firmware import FirmwarePackage, generate_key_pair, create_package

def load_config(path: str = "config/settings.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

class OTAServer:
    def __init__(self):
        config = load_config()
        self._private_key, self._public_key = generate_key_pair()
        self._mqtt = mqtt.Client()
        self._db = None
        self._campaigns = {}
        self._vehicle_status = {}

    def connect(self):
        config = load_config()
        
        self._mqtt.on_message = self._on_message
        self._mqtt.connect("localhost", 1883)
        self._mqtt.subscribe("ota/status/#")
        self._mqtt.loop_start()
        
        pg = config["postgres"]
        self._db = psycopg2.connect(
            host=pg["host"],
            port=pg["port"],
            database=pg["database"],
            user=pg["user"],
            password=pg["password"],
        )
        print("[OTA Server] Connected")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            vehicle_id = payload.get("vehicle_id")
            status_code = payload.get("status_code")
            progress_pct = payload.get("progress_pct")
            error_code = payload.get("error_code")
            campaign_id = payload.get("campaign_id")

            self._vehicle_status[vehicle_id] = payload
            print(f"[OTA Server] {vehicle_id} → status={status_code} progress={progress_pct}%")

            # Write to postgres
            self._write_ota_status(vehicle_id, payload)

            # State machine
            campaign = self._find_campaign(campaign_id)
            if campaign:
                if status_code == "READY":
                    self._send_command(vehicle_id, campaign_id, campaign["package"], "INSTALL")
                elif status_code == "DONE":
                    self._send_command(vehicle_id, campaign_id, campaign["package"], "ACTIVATE")
                elif status_code == "ACTIVATED":
                    campaign["completed"].append(vehicle_id)
                    print(f"[OTA Server] {vehicle_id} — update complete ✓")
                    
                    # Campaign tamamlandıysa güncelle
                    if len(campaign["completed"]) == len(campaign["vehicle_ids"]):
                        try:
                            cursor = self._db.cursor()
                            cursor.execute("""
                                UPDATE ota_campaigns 
                                SET state = 'COMPLETED', completed = %s, completed_at = NOW()
                                WHERE campaign_id = %s
                            """, (len(campaign["completed"]), campaign_id))
                            self._db.commit()
                        except Exception as e:
                            self._db.rollback()

                elif status_code == "ERROR":
                    campaign["errors"].append(vehicle_id)
                    self.check_and_rollback(campaign_id)

        except Exception as e:
            print(f"[OTA Server] Message error: {e}")

    def _find_campaign(self, campaign_id: str):
        return self._campaigns.get(campaign_id)    

    def _write_ota_status(self, vehicle_id: str, payload: dict):
        try:
            cursor = self._db.cursor()
            cursor.execute("""
                INSERT INTO ota_status (
                    vehicle_id, campaign_id, session_id,
                    status_code, progress_pct, error_code, fw_version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                vehicle_id,
                payload.get("campaign_id"),
                payload.get("session_id"),
                payload.get("status_code"),
                payload.get("progress_pct"),
                payload.get("error_code"),
                payload.get("fw_version"),
            ))
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            print(f"[OTA Server] DB error: {e}")

    def launch_campaign(self, ecu_target: str, version: str, vehicle_ids: list[str]):
        campaign_id = f"{ecu_target}-{version}-{int(time.time())}"
        
        # Create Firmware package
        package = create_package(ecu_target, version, self._private_key, size_kb=512)
        
        # Save campaign
        self._campaigns[campaign_id] = {
            "package": package,
            "vehicle_ids": vehicle_ids,
            "completed": [],
            "errors": [],
            "state": "ACTIVE",
        }
        
        # Write campaign to PostgreSQL
        self._write_campaign(campaign_id, ecu_target, version, len(vehicle_ids))
        
        # Canary — %10 of vehicles first
        canary_count = max(1, len(vehicle_ids) // 10)
        canary_vehicles = vehicle_ids[:canary_count]
        
        print(f"[OTA Server] Campaign {campaign_id} — canary: {canary_vehicles}")
        
        for vehicle_id in canary_vehicles:
            self._send_command(vehicle_id, campaign_id, package, "PREPARE")
        
        return campaign_id
    
    def _write_campaign(self, campaign_id: str, ecu_target: str, version: str, total_vehicles: int):
        try:
            cursor = self._db.cursor()
            cursor.execute("""
                INSERT INTO ota_campaigns (
                    campaign_id, ecu_target, fw_version,
                    state, total_vehicles
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                campaign_id,
                ecu_target,
                version,
                "ACTIVE",
                total_vehicles,
            ))
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            print(f"[OTA Server] Campaign DB error: {e}")

    def _send_command(self, vehicle_id: str, campaign_id: str, package: FirmwarePackage, cmd_type: str):
        payload = {
            "campaign_id": campaign_id,
            "session_id": f"{campaign_id}-{vehicle_id}",
            "cmd_type": cmd_type,
            "ecu_target": package.ecu_target,
            "fw_version": package.version,
            "package_id": package.package_id,
            "checksum": package.checksum,
            "signature": package.signature.hex(),
        }
        topic = f"ota/commands/{vehicle_id}"
        self._mqtt.publish(topic, json.dumps(payload))
        print(f"[OTA Server] → {vehicle_id} {cmd_type}")

    def check_and_rollback(self, campaign_id: str, error_threshold: float = 0.15):
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return
        
        total = len(campaign["vehicle_ids"])
        errors = len(campaign["errors"])
        completed = len(campaign["completed"]) + errors
        
        if completed == 0:
            return
        
        error_rate = errors / completed
        
        if error_rate > error_threshold:
            print(f"[OTA Server] Error rate {error_rate:.1%} > {error_threshold:.1%} — ROLLBACK")
            campaign["state"] = "ROLLING_BACK"
            
            for vehicle_id in campaign["completed"]:
                self._send_command(vehicle_id, campaign_id, campaign["package"], "ROLLBACK")
            
            # Update PostgreSQL
            try:
                cursor = self._db.cursor()
                cursor.execute("""
                    UPDATE ota_campaigns SET state = %s WHERE campaign_id = %s
                """, ("ROLLED_BACK", campaign_id))
                self._db.commit()
            except Exception as e:
                self._db.rollback()
        else:
            print(f"[OTA Server] Error rate {error_rate:.1%} — OK, continuing rollout")

    def expand_rollout(self, campaign_id: str):
        campaign = self._campaigns.get(campaign_id)
        if not campaign or campaign["state"] != "ACTIVE":
            return
        
        all_vehicles = campaign["vehicle_ids"]
        canary_count = max(1, len(all_vehicles) // 10)
        remaining = all_vehicles[canary_count:]
        
        if not remaining:
            print(f"[OTA Server] Campaign {campaign_id} — all vehicles done")
            return
        
        print(f"[OTA Server] Expanding rollout to {len(remaining)} vehicles")
        
        for vehicle_id in remaining:
            self._send_command(vehicle_id, campaign_id, campaign["package"], "PREPARE")

    