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
    # Negative ranges handled via offset per DBC convention

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
Coolant Temperature (°C)                [-40.0/215.0]
Oil Temperature (°C)                    [-40.0/215.0] 
Oil Pressure (bar)                      [0.00/7.00]
Mass Air Flow (g/s)                     [0.00/655.35]
Manifold Absolute Pressure (kPa)        [0/255]
'''
MESSAGE_CATALOGUE[0x0C1] = [
    SignalDef("coolant_temp_c", 0, 9, 0.5, -40, -40, 215, "°C"),
    SignalDef("oil_temp_c", 9, 9, 0.5, -40, -40, 215, "°C"),
    SignalDef("oil_pressure_bar", 18, 10, 0.01, 0, 0, 7, "bar"),
    SignalDef("maf_gs", 28, 17, 0.01, 0, 0, 655.35, "g/s"),
    SignalDef("map_kpa", 45, 8, 1, 0, 0, 255, "kPa"),
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
    SignalDef("lambda", 35, 11, 0.001, 0, 0.000, 1.990, "λ"),
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

'''TRANS_STATUS_1 (high frequency):
Gear Engaged (N=0, 1-6, R=7)            [0/7]
Input Shaft Speed (rpm)                 [0.00/8000.00]
Output Shaft Speed (rpm)                [0.00/8000.00]
Transmission Torque (Nm)                [0/1200]
Shift in Progress (binary)              [0/1]
'''
MESSAGE_CATALOGUE[0x120] = [
    SignalDef("gear_engaged", 0, 3, 1.0, 0, 0, 7, ""),
    SignalDef("input_shaft_rpm", 3, 16, 0.25, 0, 0, 8000, "rpm"),
    SignalDef("output_shaft_rpm", 19, 16, 0.25, 0, 0, 8000, "rpm"),
    SignalDef("transmission_torque_nm", 35, 11, 1.0, 0, 0, 1200, "Nm"),
    SignalDef("shift_in_progress", 46, 1, 1.0, 0, 0, 1, ""),
]

'''TRANS_STATUS_2 (low frequency):
Shifter Position (P/R/N/D/S)            [0/4]
Transmission Temperature (°C)           [-40.0/215.0]
'''
MESSAGE_CATALOGUE[0x121] = [
    SignalDef("shifter_pos", 0, 3, 1.0, 0, 0, 4, ""),
    SignalDef("trans_temp_c", 3, 9, 0.5, -40, -40, 215, "°C"),
]

'''TRANS_FAULT:
TCM MIL Status (binary)                 [0/1]
Active DTC Count                        [0/127]
P0700 - TCM Malfunction                 [0/1]
P0715 - Input Speed Sensor              [0/1]
P0730 - Incorrect Gear Ratio            [0/1]
'''
MESSAGE_CATALOGUE[0x12F] = [
    SignalDef("tcm_mil_status", 0, 1, 1.0, 0, 0, 1, ""),
    SignalDef("tcm_dtc_count", 1, 7, 1.0, 0, 0, 127, ""),
    SignalDef("dtc_p0700", 8, 1, 1.0, 0, 0, 1, ""),
    SignalDef("dtc_p0715", 9, 1, 1.0, 0, 0, 1, ""),
    SignalDef("dtc_p0730", 10, 1, 1.0, 0, 0, 1, ""),
]

'''BMS_STATUS_1:
Battery Pack Voltage (V)                [0.000/16.000]
Battery Pack Current (A)                [-300.0/100.0]
State of Charge (%)                     [0/100]
State of Health (%)                     [0/100]
'''
MESSAGE_CATALOGUE[0x310] = [
    SignalDef("pack_voltage_v", 0, 11, 0.01, 0, 0, 16, "V"),
    SignalDef("pack_current_a", 11, 13, 0.1, -300, -300, 100, "A"),
    SignalDef("soc_pct", 24, 7, 1.0, 0, 0, 100, "%"),
    SignalDef("soh_pct", 31, 7, 1.0, 0, 0, 100, "%"),
]

'''BMS_STATUS_2:
Cell Temperature Minimum (°C)           [-40.0/215.0]
Cell Temperature Maximum (°C)           [-40.0/215.0]
Cell Voltage Minimum (mV)               [1500.000/2700.000]
Cell Voltage Maximum (mV)               [1500.000/2700.000]
Balancing Active Control (binary)       [0/1]
'''
MESSAGE_CATALOGUE[0x311] = [
    SignalDef("cell_temp_min_c", 0, 9, 0.5, -40, -40, 215, "°C"),
    SignalDef("cell_temp_max_c", 9, 9, 0.5, -40, -40, 215, "°C"),
    SignalDef("cell_v_min_mv", 18, 11, 1.0, 1500, 1500, 2700, "mV"),
    SignalDef("cell_v_max_mv", 29, 11, 1.0, 1500, 1500, 2700, "mV"),
    SignalDef("balancing_active", 40, 1, 1.0, 0, 0, 1 , ""),
]

'''ADAS_LANE:
Lane Departure (Normal/Left/Right)      [0/2]
Road Curvature (1/m)                    [-0.015/0.015]
Lane Offset (m)                         [-2.0/2.0]
Speed Limit (km/h)                      [0/255]
'''

MESSAGE_CATALOGUE[0x420] = [
    SignalDef("lane_departure", 0, 2, 1.0, 0, 0, 2 , ""),
    SignalDef("road_curvature", 2, 5, 0.001, -0.015, -0.015, 0.015 , "1/m"),
    SignalDef("lane_offset_m", 7, 9, 0.01, -2.0, -2.0, 2.0, "m"),
    SignalDef("speed_limit_kmh", 16, 8, 1.0, 0, 0, 255, "km/h"),
]

'''ADAS_COLLISION:
Forward Collision Warning (binary)      [0/1]
Time to Collision (ms)                  [0/10000]
Target Distance (m)                     [0.0/400.0]
Target Relative Speed (m/s)             [-100.0/100.0]
Autonomous Emergence Brake (binary)     [0/1]
'''

MESSAGE_CATALOGUE[0x421] = [
    SignalDef("fcw_active", 0, 1, 1.0, 0, 0, 1, ""), 
    SignalDef("ttc_ms", 1, 14, 1.0, 0, 0, 10000, "ms"),
    SignalDef("target_dist_m", 15, 12, 0.1, 0, 0, 400, "m"),
    SignalDef("target_rel_speed", 27, 12, 0.1, -100, -100, 100, "m/s"),
    SignalDef("aeb_triggered", 39, 1, 1.0, 0, 0, 1, ""),
]