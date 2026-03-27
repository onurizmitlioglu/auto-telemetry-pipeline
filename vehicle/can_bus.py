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


MESSAGE_CATALOGUE: Dict[int, List[SignalDef]] = {}

MESSAGE_CATALOGUE[0x0C0] = [
    SignalDef("engine_rpm", 0, 16, 0.25, 0, 8000, "rpm"),
    SignalDef("throttle_pct", 16, 10, 0.1, 0, 0, 100, "%"),
    SignalDef("engine_load_pct", 26, 10, 0.1, 0, 0, 100, "%"),
    SignalDef("ignition_timing", 36, 7, 0.5, 0, -5, 40, "deg", is_signed=True),
]

'''
Other CAN messages here
'''

