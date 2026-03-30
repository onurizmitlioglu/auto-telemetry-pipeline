import random
import math

from vehicle.can_codec import encode


class EngineECU:
    def __init__(self, fault_injection: bool = False):
        
        self._gear = 0
        self._speed_kmh = 0.0
        self._gear_ratio = 1.0
        self._wheel_radius = 0.33
        self.throttle_pct = 0.0

        self.engine_rpm = 0.00
        self.engine_load_pct = 0.0
        self.ignition_timing = 0.0

        self._ambient = random.uniform(-10.0, 30.0)
        self.coolant_temp_c = self._ambient + random.uniform(-2.0, 2.0)
        self.oil_temp_c = self._ambient + random.uniform(-3.0, 1.0)
        self.oil_pressure_bar = 0.00
        self.maf_gs = 0.00
        self.map_kpa = 0

        self.fuel_level_pct = random.uniform(30.0, 95.0)
        self.fuel_consumption = 0.0
        self.injector_pw_us = 0
        self.lambda_ = 1.000

        self.fault_injection = fault_injection
        self.mil_status = 0
        self.dtc_count = 0
        self.dtc_p0300 = 0
        self.dtc_p0171 = 0
        self.dtc_p0217 = 0


    # Set imputs in coordination with gear and speed information
    def set_inputs(self, throttle_pct: float, gear: int = 0, speed_kmh: float = 0.0, gear_ratio: float = 1.0, wheel_radius: float = 0.33):
        self.throttle_pct = max(0.0, min(100.0, throttle_pct))
        self._gear = gear
        self._speed_kmh = speed_kmh
        self._gear_ratio = gear_ratio
        self._wheel_radius = wheel_radius

    # Generate signals, inject fault and forward to TCU (gateway)
    def tick(self) -> list:
        self._update_physics()
        self._maybe_inject_fault()
        return [
            (0x0C0, encode(0x0C0, self._get_engine_status_1())),
            (0x0C1, encode(0x0C1, self._get_engine_status_2())),
            (0x0C2, encode(0x0C2, self._get_engine_status_3())),
            (0x0CF, encode(0x0CF, self._get_engine_fault())),
        ]

    # Depending on drivings state, generate realistic signals
    def _update_physics(self):
        _is_cold = self.coolant_temp_c < 70.0

        # --- Engine RPM from speed + gear ---
        if self._gear == 0 or self._speed_kmh < 0.5:
            if _is_cold:
                # Cold start — ECU holds higher idle RPM until warm
                cold_idle_rpm = 1200.0 - (self.coolant_temp_c / 70.0) * 400.0
                cold_idle_rpm = max(800.0, cold_idle_rpm)
                target_rpm = cold_idle_rpm + self.throttle_pct * 50
            else:
                target_rpm = 800.0 + self.throttle_pct * 50
        else:
            speed_ms = self._speed_kmh / 3.6
            wheel_circumference = 2 * math.pi * self._wheel_radius
            wheel_rps = speed_ms / wheel_circumference
            target_rpm = wheel_rps * self._gear_ratio * 60
            target_rpm += self.throttle_pct * 5

        self.engine_rpm += (target_rpm - self.engine_rpm) * (0.05 if self._gear == 0 else 0.15)
        self.engine_rpm = max(0.0, min(8000.0, self.engine_rpm))

        # --- Engine load ---
        self.engine_load_pct = min(100.0, self.throttle_pct * 0.8 + (self.engine_rpm / 8000) * 20)

        # --- Temperatures ---
        warmup_rate = 0.00003 if self.engine_rpm > 500 else 0.000005
        self.coolant_temp_c += (90.0 - self.coolant_temp_c) * warmup_rate
        self.oil_temp_c += (95.0 - self.oil_temp_c) * 0.00003

        # --- Oil pressure (RPM dependent) ---
        self.oil_pressure_bar = 0.5 + (self.engine_rpm / 8000) * 5.0

        # --- MAF (proportional to RPM and load) ---
        self.maf_gs = 2.0 + (self.engine_rpm / 1000) * (self.engine_load_pct / 100) * 12.0 + random.gauss(0, 0.3)
        self.maf_gs = max(0.0, self.maf_gs)

        # --- MAP ---
        self.map_kpa = 35.0 + (self.throttle_pct / 100) * 70.0 + random.gauss(0, 1.0)

        # --- Ignition timing ---
        self.ignition_timing = 10.0 + (self.engine_rpm / 8000) * 20.0 - (self.engine_load_pct / 100) * 8.0

        # --- Lambda ---
        if self.throttle_pct > 80:
            self.lambda_ = 0.90 + random.gauss(0, 0.01)   # rich under full load
        elif self.throttle_pct < 2:
            self.lambda_ = 1.08 + random.gauss(0, 0.01)    # lean on overrun
        else:
            self.lambda_ = 1.0 + random.gauss(0, 0.008)   # stoichiometric

        # --- Fuel consumption ---
        self.fuel_consumption = max(0.5, (self.engine_load_pct / 100) * 15.0 + random.gauss(0, 0.5))
        self.fuel_level_pct -= self.fuel_consumption * 0.000001
        self.fuel_level_pct = max(0.0, self.fuel_level_pct)

        # --- Injector pulse width ---
        if self.engine_rpm > 100:
            self.injector_pw_us = int(2000 + (self.engine_load_pct / 100) * 10000 + random.gauss(0, 100))
        else:
            self.injector_pw_us = 0


    # Inject conditional fault 
    def _maybe_inject_fault(self):
        if not self.fault_injection:
            return

        # P0217 - Overheat
        if self.coolant_temp_c > 108.0:
            self.dtc_p0217 = 1
        else:
            self.dtc_p0217 = 0

        # P0171 - Lean
        if self.lambda_ > 1.15:
            self.dtc_p0171 = 1
        else:
            self.dtc_p0171 = 0

        # P0300 - Misfire
        if self.engine_rpm < 900 and self.engine_load_pct > 60:
            self.dtc_p0300 = 1
        else:
            self.dtc_p0300 = 0

        self.dtc_count = self.dtc_p0217 + self.dtc_p0171 + self.dtc_p0300
        self.mil_status = 1 if self.dtc_count > 0 else 0
        
    # Get final signals
    def _get_engine_status_1(self) -> dict:
        return {
            "engine_rpm":       self.engine_rpm,
            "throttle_pct":     self.throttle_pct,
            "engine_load_pct":  self.engine_load_pct,
            "ignition_timing":  self.ignition_timing,
        }
    
    def _get_engine_status_2(self) -> dict:
        return {
            "coolant_temp_c":   self.coolant_temp_c,
            "oil_temp_c":       self.oil_temp_c,
            "oil_pressure_bar": self.oil_pressure_bar,
            "maf_gs":           self.maf_gs,
            "map_kpa":          self.map_kpa,
        }
    
    def _get_engine_status_3(self) -> dict:
        return {
            "fuel_level_pct":   self.fuel_level_pct,
            "fuel_consumption": self.fuel_consumption,
            "injector_pw_us":   self.injector_pw_us,
            "lambda":           self.lambda_,
        }
    
    def _get_engine_fault(self) -> dict:
        return {
            "mil_status":       float(self.mil_status),
            "dtc_count":        float(self.dtc_count),
            "dtc_p0300":        float(self.dtc_p0300),
            "dtc_p0171":        float(self.dtc_p0171),
            "dtc_p0217":        float(self.dtc_p0217),
        }