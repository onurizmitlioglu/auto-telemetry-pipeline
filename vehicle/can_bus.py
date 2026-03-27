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
Engine (RPM)                            [0/8000]
Throttle (%)                            [0/100]
Engine Load (%)                         [0/100]
Ignition Timing (deg)                   [-5/40]
'''
MESSAGE_CATALOGUE[0x0C0] = [
    SignalDef("engine_rpm", 0, 16, 0.25, 0, 0, 8000, "rpm"),
    SignalDef("throttle_pct", 16, 10, 0.1, 0, 0, 100, "%"),
    SignalDef("engine_load_pct", 26, 10, 0.1, 0, 0, 100, "%"),
    SignalDef("ignition_timing", 36, 7, 0.5, -5, -5, 40, "deg"),
]

'''ENGINE_STATUS_2: 
Coolant Temperature (°C)                [-40/+215]
Oil Temperature (°C)                    [-40/+215] 
Oil Pressure (bar)                      [0/7]
Mass Air Flow (g/s)                     [0/655.35]
Manifold Absolute Pressure (kPa)        [0/255]
'''
MESSAGE_CATALOGUE[0x0C1] = [
    SignalDef("coolant_temp_c", 0, 9, 0.5, -40, -40, 215, "°C"),
    SignalDef("oil_temp_c", 9, 9, 0.5, -40, -40, 215, "°C"),
    SignalDef("oil_pressure_bar", 18, 10, 0.01, 0, 0, 7, "bar"),
    SignalDef("maf_gs", 28, 16, 0.01, 0, 0, 655.35, "g/s"),
    SignalDef("map_kpa", 44, 8, 1, 0, 0, 255, "kPa"),
]