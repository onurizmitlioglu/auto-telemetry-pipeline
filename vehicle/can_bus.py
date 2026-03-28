from dataclasses import dataclass
from typing import Dict, List

@dataclass
class SignalDef:
    name: str
    start_bit: int
    length: int
    factor: float
    offset: float
    min: float
    max: float
    unit: str
    is_signed: bool = False

"""
Signal ranges and units in message catalogue follow SAE J1979 (OBD-II) conventions where applicable.
CAN message structure and bit packing are simulation-specific.
"""


MESSAGE_CATALOGUE: Dict[int, List[SignalDef]] = {}

'''ENGINE_STATUS_1:
Engine (RPM)                            [0.00/8000.00]
Throttle (%)                            [0.0/100.0]
Engine Load (%)                         [0.0/100.0]
Ignition Timing (deg)                   [-5.0/40.0]
'''
MESSAGE_CATALOGUE[0x0C0] = [
    SignalDef("engine_rpm", 0, 16, 0.25, 0, 0, 8000, "rpm"),
    SignalDef("throttle_pct", 16, 10, 0.1, 0, 0, 100, "%"),
    SignalDef("engine_load_pct", 26, 10, 0.1, 0, 0, 100, "%"),
    SignalDef("ignition_timing", 36, 7, 0.5, -5, -5, 40, "deg"),
]

'''ENGINE_STATUS_2: 
Coolant Temperature (°C)                [-40.0/+215.0]
Oil Temperature (°C)                    [-40.0/+215.0] 
Oil Pressure (bar)                      [0.00/7.00]
Mass Air Flow (g/s)                     [0.00/655.35]
Manifold Absolute Pressure (kPa)        [0/255]
'''
MESSAGE_CATALOGUE[0x0C1] = [
    SignalDef("coolant_temp_c", 0, 9, 0.5, -40, -40, 215, "°C"),
    SignalDef("oil_temp_c", 9, 9, 0.5, -40, -40, 215, "°C"),
    SignalDef("oil_pressure_bar", 18, 10, 0.01, 0, 0, 7, "bar"),
    SignalDef("maf_gs", 28, 16, 0.01, 0, 0, 655.35, "g/s"),
    SignalDef("map_kpa", 44, 8, 1, 0, 0, 255, "kPa"),
]

'''ENGINE_STATUS_3:
Fuel Level (%)                          [0.0/100.0]
Fuel Consumption (l/100km)              [0.0/50.0]
Injector Pulse Width (µs)               [0/25000]
Normalized Air-Fuel Ratio (λ)           [0.000/1.990]                                   
'''
MESSAGE_CATALOGUE[0x0C2] = [
    SignalDef("fuel_level_pct", 0, 10, 0.1, 0, 0, 100, "%"),
    SignalDef("fuel_consumption", 10, 10, 0.1, 0, 0, 50, "l/100km"),
    SignalDef("injector_pw_us", 20, 15, 1.0, 0, 0, 25000, "µs"),
    SignalDef("lambda", 35, 11, 0.001, 0, 0, 1.99, "λ"),
]

'''
ENGINE_FAULT:
Malfunction Indicator Lamp (binary)     [0/1]
Active DTC Count                        [0/127]
P0300 - Random/Multiple Misfire         [0/1]
p0171 - Fuel System Lean (Bank 1)       [0/1]
P0217 - Engine Coolant Over Temp.       [0/1]
'''
MESSAGE_CATALOGUE[0x0CF] = [
    SignalDef("mil_status", 0, 1, 1.0, 0, 0, 1, ""),
    SignalDef("dtc_count", 1, 7, 1.0, 0, 0, 127, ""),
    SignalDef("dtc_p0300", 8, 1, 1.0, 0, 0, 1, ""),
    SignalDef("dtc_p0171", 9, 1, 1.0, 0, 0, 1, ""),
    SignalDef("dtc_p0217", 10, 1, 1.0, 0, 0, 1, ""),
]