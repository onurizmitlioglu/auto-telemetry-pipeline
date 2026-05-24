import csv
import time
import threading
from vehicle.tcu import TCU
from pipeline.processor import Pipeline
from ota.firmware import generate_key_pair
from ota.server import OTAServer

# Gear map: (max_speed_kmh, gear, effective_ratio)
GEAR_MAP = [
    (0,   0, 0.0),
    (20,  1, 3.5 * 3.9),
    (40,  2, 2.0 * 3.9),
    (70,  3, 1.4 * 3.9),
    (100, 4, 1.0 * 3.9),
    (130, 5, 0.8 * 3.9),
    (999, 6, 0.65 * 3.9),
]

def get_gear(speed_kmh: float):
    for max_speed, gear, ratio in GEAR_MAP:
        if speed_kmh <= max_speed:
            return gear, ratio
    return 6, 0.65 * 3.9

def load_wltp(path: str = "config/wltp_cycle.csv"):
    profile = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            profile.append(float(row["speed_meters_per_second"]))
    return profile

def compute_throttle(prev_speed: float, curr_speed: float) -> float:
    delta = curr_speed - prev_speed
    if delta > 0:
        return min(100.0, delta * 20)
    elif curr_speed < 0.5:
        return 0.0
    else:
        return max(0.0, 10.0 + curr_speed * 0.5)

def main():
    # Pipeline — thread 1
    pipeline = Pipeline()
    pipeline.connect()
    pipeline_thread = threading.Thread(target=pipeline.run, daemon=True)
    pipeline_thread.start()

    private_key, public_key = generate_key_pair()
    server = OTAServer()
    server._private_key = private_key
    server.connect()

    # TCU - thread 2
    tcu = TCU("VHC-001", public_key)
    tcu.connect()
    tcu.start()

    # WLTP
    profile = load_wltp()
    prev_speed = 0.0

    print("[Main] WLTP drive cycle starting...")
    for i, speed_ms in enumerate(profile):
        speed_kmh = speed_ms * 3.6
        gear, ratio = get_gear(speed_kmh)
        throttle = compute_throttle(prev_speed, speed_ms)

        # Fault injection scenario - overheat at 500th second
        if 500 <= i <= 505:
            tcu.engine_ecu.coolant_temp_c = 120.0

        tcu.engine_ecu.set_inputs(
            throttle_pct=throttle,
            gear=gear,
            speed_kmh=speed_kmh,
            gear_ratio=ratio,
        )

        prev_speed = speed_ms
        time.sleep(1.0)

    tcu.stop()
    print("[Main] Drive cycle complete.")

    # OTA campaign
    print("[Main] Launching OTA campaign...")
    campaign_id = server.launch_campaign("ENGINE", "2.15.0", ["VHC-001"])
    time.sleep(10)
    print("[Main] OTA complete.")

if __name__ == "__main__":
    main()