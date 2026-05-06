"""
================================================================================
ASM Technologies Ltd
Integrated Chassis & Frame Analysis System  |  Version 5
================================================================================

Combined Module 1: Chassis CFD & Structural Analysis (based on V3)
Combined Module 2: Frame Section & Chassis Load Analysis (based on V4)

Standards Referenced:
  - IS 2062:2011  Hot Rolled Medium and High Tensile Structural Steel
  - IS 800:2007   General Construction in Steel
  - IS 4923:1997  Hollow Steel Sections (HSS) for Structural Use
  - AISI / ASTM   Reference standards for comparison studies

Units Convention:
  - Lengths: m (meters) or mm (millimeters) — labeled explicitly
  - Section modulus: cm³ (cubic centimeters)
  - Stress: MPa (N/mm²)
  - Force: N (Newtons) or kN (kiloNewtons)
  - Mass: kg
================================================================================
"""
# python asm_integrated_chassis_frame_analysis_v5.py

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import (
    BOTH,
    BooleanVar,
    Canvas,
    END,
    LEFT,
    PhotoImage,
    RIGHT,
    StringVar,
    Tk,
    Toplevel,
    filedialog,
    messagebox,
    ttk,
)

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

# ==============================================================================
# GLOBAL CONFIGURATION
# ==============================================================================
COMPANY_NAME = "ASM Technologies Ltd"
APP_TITLE = "Integrated Chassis & Frame Analysis System"
APP_VERSION = "V5"
LOGO_PATH = Path(__file__).with_name("ASM-Logo.png")

ASM_BLUE = "#104984"
ASM_BLUE_DARK = "#0a2d52"
ASM_PANEL = "#f4f7fb"
ASM_GREEN = "#167a3a"
ASM_RED = "#b3261e"
ASM_AMBER = "#b36b16"

G = 9.80665  # Standard gravity (m/s²)

INDIAN_STANDARDS_NOTE = (
    "Indian Standards Referenced: IS 2062:2011 (Structural Steel), "
    "IS 800:2007 (Steel Construction), IS 4923:1997 (Hollow Steel Sections). "
    "AISI/ASTM values provided for international comparison only."
)


# ==============================================================================
# SHARED MATERIAL DATABASES WITH STANDARDS REFERENCES
# ==============================================================================
@dataclass(frozen=True)
class ChassisMaterial:
    name: str
    youngs_gpa: float
    yield_mpa: float
    ultimate_mpa: float
    poisson: float
    density: float
    color: str
    standard: str
    use: str = ""


@dataclass(frozen=True)
class FrameMaterial:
    name: str
    youngs_gpa: float
    yield_mpa: float
    density: float
    standard: str
    use: str


CHASSIS_MATERIALS = {
    "IS 2062 E250 Mild Steel (IS 2062:2011)": ChassisMaterial(
        "IS 2062 E250 Mild Steel",
        200.0,
        250.0,
        410.0,
        0.30,
        7850,
        "#2f7dc1",
        "IS 2062:2011",
        "Common Indian chassis/frame fabrication steel. Grade A/B/C per IS 2062:2011.",
    ),
    "IS 2062 E350 Structural Steel (IS 2062:2011)": ChassisMaterial(
        "IS 2062 E350 Structural Steel",
        200.0,
        350.0,
        490.0,
        0.30,
        7850,
        "#1f8a70",
        "IS 2062:2011",
        "Higher strength structural chassis member material. Grade A/B/C per IS 2062:2011.",
    ),
    "ASTM A36 Steel (ASTM Reference)": ChassisMaterial(
        "ASTM A36 Steel",
        200.0,
        250.0,
        400.0,
        0.30,
        7850,
        "#4c78a8",
        "ASTM A36",
        "General structural steel comparison baseline.",
    ),
    "AISI 1018 Low Carbon Steel (AISI Reference)": ChassisMaterial(
        "AISI 1018 Low Carbon Steel",
        205.0,
        370.0,
        440.0,
        0.29,
        7870,
        "#72b7b2",
        "AISI 1018",
        "Low carbon steel for brackets and welded fittings.",
    ),
    "HSS 550 Steel (IS 4923:1997)": ChassisMaterial(
        "HSS 550 Steel",
        200.0,
        550.0,
        620.0,
        0.30,
        7850,
        "#f58518",
        "IS 4923:1997",
        "High strength steel for weight-reduced chassis rail study. Hollow Section per IS 4923.",
    ),
    "HSS 700 Steel (IS 4923:1997)": ChassisMaterial(
        "HSS 700 Steel",
        200.0,
        700.0,
        780.0,
        0.30,
        7850,
        "#a83a32",
        "IS 4923:1997",
        "High strength truck frame / heavy load comparison material. Hollow Section per IS 4923.",
    ),
    "Domex 700 MC (Automotive HSS)": ChassisMaterial(
        "Domex 700 MC",
        210.0,
        700.0,
        750.0,
        0.30,
        7850,
        "#9467bd",
        "SSAB Domex",
        "Automotive high strength steel used for chassis and transport structures.",
    ),
    "Aluminum 6061-T6 (ISO/ASTM)": ChassisMaterial(
        "Aluminum 6061-T6",
        68.9,
        276.0,
        310.0,
        0.33,
        2700,
        "#59a14f",
        "ASTM B209",
        "Lightweight comparison material; deflection usually increases.",
    ),
    "CFRP Carbon Fiber (Advanced)": ChassisMaterial(
        "CFRP Carbon Fiber",
        70.0,
        600.0,
        700.0,
        0.10,
        1600,
        "#303030",
        "Custom",
        "Advanced lightweight comparison material, not typical for main truck chassis rails.",
    ),
    "Titanium Ti-6Al-4V (ASTM B265)": ChassisMaterial(
        "Titanium Ti-6Al-4V",
        113.8,
        880.0,
        950.0,
        0.342,
        4430,
        "#b36b16",
        "ASTM B265",
        "High strength lightweight comparison material, costly for chassis use.",
    ),
}

FRAME_MATERIALS = {
    "IS 2062 E250 Mild Steel (IS 2062:2011)": FrameMaterial(
        "IS 2062 E250 Mild Steel",
        200.0,
        250.0,
        7850.0,
        "IS 2062:2011",
        "Common chassis/frame fabrication steel per Indian Standard.",
    ),
    "IS 2062 E350 Structural Steel (IS 2062:2011)": FrameMaterial(
        "IS 2062 E350 Structural Steel",
        200.0,
        350.0,
        7850.0,
        "IS 2062:2011",
        "Higher strength chassis rail and cross-member material per Indian Standard.",
    ),
    "HSS 550 Steel (IS 4923:1997)": FrameMaterial(
        "HSS 550 Steel",
        200.0,
        550.0,
        7850.0,
        "IS 4923:1997",
        "High strength steel for weight-reduced frame study per Indian Standard.",
    ),
    "HSS 700 Steel (IS 4923:1997)": FrameMaterial(
        "HSS 700 Steel",
        200.0,
        700.0,
        7850.0,
        "IS 4923:1997",
        "Heavy-duty high strength truck frame comparison material per Indian Standard.",
    ),
    "Domex 700 MC (Automotive HSS)": FrameMaterial(
        "Domex 700 MC",
        210.0,
        700.0,
        7850.0,
        "SSAB Domex",
        "Automotive high strength steel for chassis and transport structures.",
    ),
}


# ==============================================================================
# CHASSIS MODULE DATA (V3 Heritage)
# ==============================================================================
@dataclass(frozen=True)
class ChassisComponent:
    name: str
    length_m: float
    width_m: float
    thickness_m: float
    component_type: str
    description: str


CHASSIS_COMPONENTS = {
    "4x2 Truck Main Chassis Rail": ChassisComponent(
        "4x2 Truck Main Chassis Rail",
        4.2,
        0.075,
        0.18,
        "cbeam",
        "Main chassis rail for a small/medium 4x2 truck. Suitable for wheelbase and payload load checks.",
    ),
    "Truck Chassis C-Section Rail": ChassisComponent(
        "Truck Chassis C-Section Rail",
        5.0,
        0.08,
        0.20,
        "cbeam",
        "Single longitudinal C-section chassis rail. Width = flange width (m), Thickness = section height (m).",
    ),
    "Truck Chassis Box Rail": ChassisComponent(
        "Truck Chassis Box Rail",
        5.0,
        0.10,
        0.22,
        "cbeam",
        "Closed/boxed chassis rail approximation for high torsional stiffness comparison.",
    ),
    "Cross Member": ChassisComponent(
        "Cross Member",
        1.2,
        0.075,
        0.15,
        "cbeam",
        "Chassis cross member between left and right rails. Useful for lateral/transverse load checks.",
    ),
    "Suspension Bracket Zone": ChassisComponent(
        "Suspension Bracket Zone",
        0.45,
        0.12,
        0.18,
        "cbeam",
        "Local reinforced chassis zone near suspension bracket, checked with concentrated loads.",
    ),
    "Body Mount Bracket Zone": ChassisComponent(
        "Body Mount Bracket Zone",
        0.35,
        0.10,
        0.14,
        "cbeam",
        "Local chassis fitting zone for body/fairing/cab mounting brackets and bolt reaction checks.",
    ),
}

CHASSIS_LOAD_PRESETS = {
    "4x2 Truck Main Chassis Rail": [
        ("Transverse", 9000.0, "Middle"),
        ("Axial", 3500.0, "Front"),
        ("Torque", 1200.0, "Rear"),
    ],
    "Truck Chassis C-Section Rail": [
        ("Transverse", 12000.0, "Middle"),
        ("Axial", 5000.0, "Front"),
        ("Torque", 1800.0, "Rear"),
    ],
    "Truck Chassis Box Rail": [
        ("Transverse", 15000.0, "Middle"),
        ("Axial", 6000.0, "Front"),
        ("Torque", 2500.0, "Rear"),
    ],
    "Cross Member": [
        ("Transverse", 6000.0, "Middle"),
        ("Axial", 1200.0, "Base"),
        ("Torque", 700.0, "Bolt Area"),
    ],
    "Suspension Bracket Zone": [
        ("Transverse", 18000.0, "Bolt Area"),
        ("Axial", 4000.0, "Base"),
        ("Torque", 2200.0, "Bolt Area"),
    ],
    "Body Mount Bracket Zone": [
        ("Transverse", 4500.0, "Bolt Area"),
        ("Axial", 1500.0, "Base"),
        ("Torque", 600.0, "Bolt Area"),
    ],
}

CHASSIS_LOAD_TYPES = ("Axial", "Transverse", "Pressure", "Torque")
CHASSIS_LOAD_ZONES = ("Front", "Middle", "Rear", "Full Span", "Bolt Area", "Base")
CHASSIS_BOUNDARIES = ("Simply Supported", "Cantilever", "Fixed-Fixed")

CFD_PRESETS = {
    "Highway cruise": {
        "speed_kmh": 80.0,
        "air_density": 1.225,
        "cd": 0.70,
        "cl": 0.05,
        "wind_angle": 0.0,
        "gust": 1.0,
    },
    "Highway gust": {
        "speed_kmh": 100.0,
        "air_density": 1.225,
        "cd": 0.85,
        "cl": 0.08,
        "wind_angle": 20.0,
        "gust": 1.25,
    },
    "Crosswind study": {
        "speed_kmh": 90.0,
        "air_density": 1.225,
        "cd": 0.95,
        "cl": 0.10,
        "wind_angle": 35.0,
        "gust": 1.20,
    },
    "Low speed yard": {
        "speed_kmh": 30.0,
        "air_density": 1.225,
        "cd": 0.60,
        "cl": 0.02,
        "wind_angle": 0.0,
        "gust": 1.0,
    },
}


# ==============================================================================
# FRAME MODULE DATA (V4 Heritage)
# ==============================================================================
ENGINE_LOADS_KG = {
    "Small diesel engine": 420.0,
    "Medium diesel engine": 650.0,
    "Heavy diesel engine": 900.0,
    "Electric motor + pack": 1200.0,
}
AXLE_LOADS_KG = [3000, 4000, 5000, 6000, 7500, 9000, 10500, 12000, 14000, 16000]
FRONT_AXLE_POSITIONS_M = [0.9, 1.0, 1.1, 1.2, 1.3, 1.5]
REAR_AXLE_POSITIONS_M = [3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0, 8.0, 9.0, 10.0]


# ==============================================================================
# CHASSIS CALCULATION ENGINE
# ==============================================================================
def calculate_cfd_load(
    speed_kmh,
    air_density,
    drag_coefficient,
    lift_coefficient,
    projected_area,
    wind_angle_deg,
    gust_factor,
    length_m,
):
    speed_ms = speed_kmh / 3.6
    effective_speed = speed_ms * gust_factor
    angle_rad = math.radians(wind_angle_deg)
    dynamic_pressure = 0.5 * air_density * effective_speed**2
    frontal_factor = max(math.cos(angle_rad), 0.0) ** 2
    side_factor = abs(math.sin(angle_rad))
    pressure_pa = dynamic_pressure * drag_coefficient * max(frontal_factor, 0.20)
    drag_n = pressure_pa * projected_area
    side_force_n = dynamic_pressure * drag_coefficient * projected_area * side_factor
    lift_n = dynamic_pressure * lift_coefficient * projected_area
    air_viscosity = 1.81e-5
    reynolds = (
        air_density * effective_speed * max(length_m, 1e-6) / air_viscosity
    )
    return {
        "speed_ms": speed_ms,
        "effective_speed_ms": effective_speed,
        "dynamic_pressure_pa": dynamic_pressure,
        "pressure_pa": pressure_pa,
        "drag_n": drag_n,
        "side_force_n": side_force_n,
        "lift_n": lift_n,
        "reynolds": reynolds,
        "projected_area_m2": projected_area,
        "wind_angle_deg": wind_angle_deg,
        "gust_factor": gust_factor,
    }


def chassis_section_area(component_type: str, width_m: float, thickness_m: float) -> float:
    if component_type == "cbeam":
        web_height = thickness_m
        flange_width = width_m
        wall_t = 0.010
        return (
            2.0 * flange_width * wall_t
            + max(web_height - 2.0 * wall_t, wall_t) * wall_t
        )
    return max(width_m * thickness_m, 1e-9)


def chassis_second_moment(
    component_type: str, width_m: float, thickness_m: float
) -> float:
    if component_type == "cbeam":
        b = width_m
        h = thickness_m
        t = 0.010
        inner_b = max(b - 2.0 * t, t)
        inner_h = max(h - 2.0 * t, t)
        return max(
            (b * h**3 / 12.0) - (inner_b * inner_h**3 / 12.0), 1e-12
        )
    return max(width_m * thickness_m**3 / 12.0, 1e-12)


def chassis_zone_factor(zone: str) -> float:
    return {
        "Front": 0.80,
        "Middle": 1.00,
        "Rear": 0.80,
        "Full Span": 0.65,
        "Bolt Area": 1.25,
        "Base": 1.15,
    }.get(zone, 1.0)


def calculate_chassis(
    component_type,
    length_m,
    width_m,
    thickness_m,
    material,
    loads,
    boundary,
    fos_target,
):
    area = chassis_section_area(component_type, width_m, thickness_m)
    inertia = chassis_second_moment(component_type, width_m, thickness_m)
    c = max(thickness_m / 2.0, 1e-6)
    e_pa = material.youngs_gpa * 1e9

    axial_n = 0.0
    transverse_n = 0.0
    pressure_pa = 0.0
    torque_nm = 0.0
    weighted_transverse = 0.0

    for load_type, value, zone in loads:
        factor = chassis_zone_factor(zone)
        if load_type == "Axial":
            axial_n += value * factor
        elif load_type == "Transverse":
            transverse_n += value * factor
            weighted_transverse += value * factor
        elif load_type == "Pressure":
            pressure_pa += value
            pressure_force = value * width_m * length_m
            transverse_n += pressure_force * factor
            weighted_transverse += pressure_force * factor
        elif load_type == "Torque":
            torque_nm += value * factor
            equivalent_force = value / max(length_m, 1e-6)
            transverse_n += equivalent_force
            weighted_transverse += equivalent_force

    x_values = []
    bending = []
    axial = []
    shear = []
    torsion = []
    von_mises = []
    strain = []
    zones = []

    for i in range(31):
        x = length_m * i / 30.0
        if boundary == "Cantilever":
            moment = weighted_transverse * (length_m - x)
            deflection_factor = 3.0
        elif boundary == "Fixed-Fixed":
            center = 1.0 - (2.0 * x / max(length_m, 1e-6) - 1.0) ** 2
            moment = weighted_transverse * length_m * max(center, 0.0) / 8.0
            deflection_factor = 192.0
        else:
            moment = weighted_transverse * min(x, length_m - x) / 2.0
            deflection_factor = 48.0

        sigma_b = abs(moment * c / inertia) / 1e6
        sigma_a = abs(axial_n / area) / 1e6
        tau_v = abs(1.5 * transverse_n / area) / 1e6
        tau_t = abs(torque_nm * c / max(2.0 * inertia, 1e-12)) / 1e6
        tau_total = tau_v + tau_t
        sigma_vm = math.sqrt((sigma_b + sigma_a) ** 2 + 3.0 * tau_total**2)

        x_values.append(x * 1000.0)
        bending.append(sigma_b)
        axial.append(sigma_a)
        shear.append(tau_v)
        torsion.append(tau_t)
        von_mises.append(sigma_vm)
        strain.append(sigma_vm / (material.youngs_gpa * 1000.0))
        zones.append(material.yield_mpa / max(sigma_vm, 1e-6))

    max_stress = max(von_mises)
    max_strain = max(strain)

    total_force = max(transverse_n, 0.0)
    if boundary == "Cantilever":
        max_deflection_mm = (
            total_force * length_m**3 / (3.0 * e_pa * inertia) * 1000.0
        )
    elif boundary == "Fixed-Fixed":
        max_deflection_mm = (
            total_force * length_m**3 / (192.0 * e_pa * inertia) * 1000.0
        )
    else:
        max_deflection_mm = (
            total_force * length_m**3 / (48.0 * e_pa * inertia) * 1000.0
        )

    load_axis = []
    deflection_curve = []
    for i in range(1, 31):
        force_i = total_force * i / 30.0
        if boundary == "Cantilever":
            delta = force_i * length_m**3 / (3.0 * e_pa * inertia) * 1000.0
        elif boundary == "Fixed-Fixed":
            delta = force_i * length_m**3 / (192.0 * e_pa * inertia) * 1000.0
        else:
            delta = force_i * length_m**3 / (48.0 * e_pa * inertia) * 1000.0
        load_axis.append(force_i / 1000.0)
        deflection_curve.append(delta)

    return {
        "x_mm": x_values,
        "bending_mpa": bending,
        "axial_mpa": axial,
        "shear_mpa": shear,
        "torsion_mpa": torsion,
        "von_mises_mpa": von_mises,
        "strain": strain,
        "fos_zone": zones,
        "load_kn": load_axis,
        "deflection_mm": deflection_curve,
        "max_stress_mpa": max_stress,
        "max_strain": max_strain,
        "max_deflection_mm": max_deflection_mm,
        "fos": material.yield_mpa / max(max_stress, 1e-6),
        "mass_kg": length_m * area * material.density,
        "pressure_pa": pressure_pa,
        "transverse_n": transverse_n,
        "axial_n": axial_n,
        "torque_nm": torque_nm,
        "area_m2": area,
        "inertia_m4": inertia,
        "fos_target": fos_target,
        "deflection_factor": deflection_factor,
    }


# ==============================================================================
# FRAME CALCULATION ENGINE
# ==============================================================================
def channel_section_properties(height_mm: float, flange_mm: float, thickness_mm: float):
    h = height_mm / 1000.0
    b = flange_mm / 1000.0
    t = thickness_mm / 1000.0
    if min(h, b, t) <= 0:
        raise ValueError(
            "Frame height (mm), flange width (mm), and thickness (mm) must be greater than zero."
        )
    if t >= h / 2 or t >= b:
        raise ValueError(
            "Thickness (mm) is too large for the selected C-channel dimensions."
        )

    web_area = t * h
    flange_area = b * t
    area = web_area + 2.0 * flange_area
    web_i = t * h**3 / 12.0
    flange_i_centroid = b * t**3 / 12.0
    flange_offset = h / 2.0 - t / 2.0
    inertia = web_i + 2.0 * (flange_i_centroid + flange_area * flange_offset**2)
    section_modulus = inertia / (h / 2.0)
    return {
        "area_m2": area,
        "inertia_m4": inertia,
        "section_modulus_m3": section_modulus,
        "section_modulus_cm3": section_modulus * 1e6,
        "height_m": h,
        "flange_m": b,
        "thickness_m": t,
    }


def integrate_deflection(x_values, moment_nm, e_pa, inertia_m4, fap_m, rap_m):
    theta = [0.0]
    y = [0.0]
    for i in range(1, len(x_values)):
        dx = x_values[i] - x_values[i - 1]
        curvature_prev = moment_nm[i - 1] / (e_pa * inertia_m4)
        curvature_curr = moment_nm[i] / (e_pa * inertia_m4)
        theta.append(theta[-1] + 0.5 * (curvature_prev + curvature_curr) * dx)
        y.append(y[-1] + 0.5 * (theta[-2] + theta[-1]) * dx)

    def interp(arr, x):
        if x <= x_values[0]:
            return arr[0]
        if x >= x_values[-1]:
            return arr[-1]
        for i in range(1, len(x_values)):
            if x_values[i] >= x:
                ratio = (x - x_values[i - 1]) / (x_values[i] - x_values[i - 1])
                return arr[i - 1] + ratio * (arr[i] - arr[i - 1])
        return arr[-1]

    y_f = interp(y, fap_m)
    y_r = interp(y, rap_m)
    slope_correction = (y_r - y_f) / max(rap_m - fap_m, 1e-6)
    corrected = [
        val - (y_f + slope_correction * (x - fap_m))
        for x, val in zip(x_values, y)
    ]
    return corrected


def frame_analysis(inputs):
    length = inputs["length_m"]
    fap = inputs["fap_m"]
    rap = inputs["rap_m"]
    ffl = inputs["ffl_m"]
    rfl = inputs["rfl_m"]
    material = inputs["material"]
    section = channel_section_properties(
        inputs["height_mm"], inputs["flange_mm"], inputs["thickness_mm"]
    )
    e_pa = material.youngs_gpa * 1e9

    front_axle_target_n = inputs["front_axle_load_kg"] * G
    rear_axle_target_n = inputs["rear_axle_load_kg"] * G
    total_design_load_n = front_axle_target_n + rear_axle_target_n
    cab_load_n = inputs["cab_load_kg"] * G
    engine_load_n = inputs["engine_load_kg"] * G
    frame_self_weight_n = section["area_m2"] * length * material.density * G
    known_load_n = cab_load_n + engine_load_n + frame_self_weight_n
    payload_n = max(total_design_load_n - known_load_n, 0.0)

    loads = [
        {
            "name": "Cab load",
            "x": max(0.15, min(fap * 0.55, length)),
            "n": cab_load_n,
        },
        {
            "name": "Engine load",
            "x": max(0.20, min(fap + 0.35, length)),
            "n": engine_load_n,
        },
    ]

    udl_start = max(fap, 0.0)
    udl_end = min(length, rap + max(rfl * 0.60, 0.0))
    udl_length = max(udl_end - udl_start, 0.1)
    payload_udl_npm = payload_n / udl_length
    frame_udl_npm = frame_self_weight_n / length

    equivalent_loads = loads + [
        {
            "name": "Payload equivalent",
            "x": udl_start + udl_length / 2.0,
            "n": payload_n,
        },
        {
            "name": "Frame self weight",
            "x": length / 2.0,
            "n": frame_self_weight_n,
        },
    ]
    total_down = sum(load["n"] for load in equivalent_loads)
    moment_about_front = sum(
        load["n"] * (load["x"] - fap) for load in equivalent_loads
    )
    wheelbase = max(rap - fap, 1e-6)
    rear_reaction_n = moment_about_front / wheelbase
    front_reaction_n = total_down - rear_reaction_n

    x_values = [length * i / 240.0 for i in range(241)]
    shear = []
    moment = []
    for x in x_values:
        v = 0.0
        if x >= fap:
            v += front_reaction_n
        if x >= rap:
            v += rear_reaction_n
        for load in loads:
            if x >= load["x"]:
                v -= load["n"]
        if x > 0:
            v -= frame_udl_npm * min(x, length)
        if x >= udl_start:
            v -= payload_udl_npm * min(x - udl_start, udl_length)
        shear.append(v)

        m = 0.0
        if x >= fap:
            m += front_reaction_n * (x - fap)
        if x >= rap:
            m += rear_reaction_n * (x - rap)
        for load in loads:
            if x >= load["x"]:
                m -= load["n"] * (x - load["x"])
        m -= frame_udl_npm * min(x, length) * (x - min(x, length) / 2.0)
        if x >= udl_start:
            used = min(x - udl_start, udl_length)
            m -= payload_udl_npm * used * (x - (udl_start + used / 2.0))
        moment.append(m)

    deflection_m = integrate_deflection(
        x_values, moment, e_pa, section["inertia_m4"], fap, rap
    )
    stress_mpa = [abs(m) / section["section_modulus_m3"] / 1e6 for m in moment]
    max_moment = max(moment, key=lambda value: abs(value))
    max_stress = max(stress_mpa)
    max_deflection_mm = max(abs(value) for value in deflection_m) * 1000.0
    fos = material.yield_mpa / max(max_stress, 1e-6)

    sections_x = [length * i / 24.0 for i in range(25)]
    section_modulus = [section["section_modulus_cm3"] for _ in sections_x]
    utilization = [
        min(
            abs(interpolate_frame(x_values, stress_mpa, x))
            / material.yield_mpa
            * 100.0,
            999.0,
        )
        for x in sections_x
    ]

    checks = []
    checks.append(check_item(fap < rap, "FAP must be before RAP."))
    checks.append(
        check_item(
            abs(ffl - fap) <= 0.15,
            "FFL (m) should approximately match front axle position (m).",
        )
    )
    checks.append(
        check_item(
            abs((length - rap) - rfl) <= 0.15,
            "RFL (m) should approximately match length - rear axle position (m).",
        )
    )
    checks.append(
        check_item(
            ffl + rfl <= 2.0 * wheelbase,
            "Total overhang FFL + RFL (m) must not exceed 2 × wheelbase (m).",
        )
    )
    checks.append(
        check_item(
            ffl <= wheelbase, "Front overhang (m) should not exceed wheelbase (m)."
        )
    )
    checks.append(
        check_item(
            rfl <= wheelbase, "Rear overhang (m) should not exceed wheelbase (m)."
        )
    )
    checks.append(
        check_item(fos >= inputs["fos_target"], "Factor of safety must meet target.")
    )
    checks.append(
        check_item(
            max_deflection_mm <= length * 1000.0 / 300.0,
            "Frame deflection (mm) should be within L/300 guideline.",
        )
    )

    front_error = (
        abs(front_reaction_n - front_axle_target_n)
        / max(front_axle_target_n, 1.0)
        * 100.0
    )
    rear_error = (
        abs(rear_reaction_n - rear_axle_target_n)
        / max(rear_axle_target_n, 1.0)
        * 100.0
    )
    checks.append(
        check_item(
            front_error <= 15.0,
            "Calculated front reaction (kg) should be within 15% of selected FA load (kg).",
        )
    )
    checks.append(
        check_item(
            rear_error <= 15.0,
            "Calculated rear reaction (kg) should be within 15% of selected RA load (kg).",
        )
    )

    return {
        "section": section,
        "x_m": x_values,
        "shear_n": shear,
        "moment_nm": moment,
        "deflection_mm": [value * 1000.0 for value in deflection_m],
        "stress_mpa": stress_mpa,
        "sections_x_m": sections_x,
        "section_modulus_cm3": section_modulus,
        "utilization_pct": utilization,
        "max_moment_nm": max_moment,
        "max_stress_mpa": max_stress,
        "max_deflection_mm": max_deflection_mm,
        "fos": fos,
        "front_reaction_n": front_reaction_n,
        "rear_reaction_n": rear_reaction_n,
        "front_error_pct": front_error,
        "rear_error_pct": rear_error,
        "payload_kg": payload_n / G,
        "frame_self_weight_kg": frame_self_weight_n / G,
        "checks": checks,
    }


def interpolate_frame(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if xs[i] >= x:
            ratio = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + ratio * (ys[i] - ys[i - 1])
    return ys[-1]


def check_item(ok, text):
    return {"ok": bool(ok), "text": text}


# ==============================================================================
# UI: CHASSIS STRUCTURAL ANALYSIS TAB
# ==============================================================================
class ChassisStructuralTab(ttk.Frame):
    def __init__(self, parent, status_var):
        super().__init__(parent)
        self.status_var = status_var
        self.current_result = None
        self.last_cfd = None
        self.logo_image = None

        self.component_name = StringVar(
            value="4x2 Truck Main Chassis Rail"
        )
        self.material_name = StringVar(
            value="IS 2062 E350 Structural Steel (IS 2062:2011)"
        )
        self.compare_name = StringVar(value="HSS 700 Steel (IS 4923:1997)")
        self.boundary = StringVar(value="Simply Supported")

        self.cad_loaded_var = StringVar(value="No CAD part loaded")
        self.cad_detail_var = StringVar(
            value="Upload a STEP/STL/CATPart/mesh file to auto-detect the chassis preset."
        )
        self.cad_button_var = StringVar(value="Upload Part File")
        self.loaded_cad_path = None

        self.length_var = StringVar()
        self.width_var = StringVar()
        self.thickness_var = StringVar()
        self.fos_target_var = StringVar(value="2.5")

        self.cfd_enabled = BooleanVar(value=False)
        self.cfd_preset = StringVar(value="Highway gust")
        self.cfd_speed_var = StringVar(value="100")
        self.cfd_density_var = StringVar(value="1.225")
        self.cfd_cd_var = StringVar(value="0.85")
        self.cfd_cl_var = StringVar(value="0.08")
        self.cfd_area_var = StringVar(value="1.6")
        self.cfd_angle_var = StringVar(value="20")
        self.cfd_gust_var = StringVar(value="1.25")
        self.cfd_summary = StringVar(value="Road/air load not calculated yet.")

        self.load_rows = []
        self.metric_vars = {
            "stress": StringVar(value="-"),
            "strain": StringVar(value="-"),
            "deflection": StringVar(value="-"),
            "fos": StringVar(value="-"),
            "mass": StringVar(value="-"),
        }

        self.build_ui()
        self.load_component_defaults()
        self.update_material_panel()
        self.run_analysis()

    def build_ui(self):
        # Scrollable container
        shell = ttk.Frame(self)
        shell.pack(fill=BOTH, expand=True)
        self.scroll_canvas = Canvas(shell, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            shell, orient="vertical", command=self.scroll_canvas.yview
        )
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)
        self.scroll_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill="y")

        container = ttk.Frame(self.scroll_canvas, padding=12)
        self.scroll_window = self.scroll_canvas.create_window(
            (0, 0), window=container, anchor="nw"
        )
        container.bind(
            "<Configure>",
            lambda _e: self.scroll_canvas.configure(
                scrollregion=self.scroll_canvas.bbox("all")
            ),
        )
        self.scroll_canvas.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.itemconfigure(
                self.scroll_window, width=e.width
            ),
        )
        self.bind_all("<MouseWheel>", self.on_mousewheel)

        # Standards note
        std_label = ttk.Label(
            container,
            text=INDIAN_STANDARDS_NOTE,
            wraplength=900,
            foreground=ASM_BLUE_DARK,
            background="#ffffff",
            font=("Segoe UI", 8, "italic"),
        )
        std_label.pack(fill="x", pady=(0, 8))

        main = ttk.Panedwindow(container, orient="horizontal")
        main.pack(fill=BOTH, expand=True)

        left = ttk.Frame(main, padding=(0, 0, 10, 0))
        right = ttk.Frame(main)
        main.add(left, weight=0)
        main.add(right, weight=1)

        self.build_inputs(left)
        self.build_outputs(right)

    def on_mousewheel(self, event):
        self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def build_inputs(self, parent):
        option_tabs = ttk.Notebook(parent)
        option_tabs.pack(fill=BOTH, expand=True, pady=(0, 8))

        setup_tab = ttk.Frame(option_tabs, padding=6)
        load_tab = ttk.Frame(option_tabs, padding=6)
        road_tab = ttk.Frame(option_tabs, padding=6)
        option_tabs.add(setup_tab, text="Chassis Setup")
        option_tabs.add(load_tab, text="Load Case (N / Pa / N-m)")
        option_tabs.add(road_tab, text="Road/Air Load (CFD)")

        # CAD
        file_box = ttk.LabelFrame(
            setup_tab,
            text="Chassis / CAD Input",
            padding=10,
            style="Panel.TLabelframe",
        )
        file_box.pack(fill="x", pady=(0, 8))
        ttk.Button(
            file_box, textvariable=self.cad_button_var, command=self.upload_part
        ).pack(fill="x")
        loaded_panel = ttk.Frame(file_box)
        loaded_panel.pack(fill="x", pady=(8, 0))
        ttk.Label(loaded_panel, text="CAD Status", style="Title.TLabel").pack(
            anchor="w"
        )
        self.cad_status_label = ttk.Label(
            loaded_panel,
            textvariable=self.cad_loaded_var,
            style="Metric.TLabel",
            wraplength=310,
        )
        self.cad_status_label.pack(anchor="w", pady=(2, 0))
        self.cad_detail_label = ttk.Label(
            loaded_panel,
            textvariable=self.cad_detail_var,
            style="Sub.TLabel",
            wraplength=310,
        )
        self.cad_detail_label.pack(anchor="w", pady=(2, 0))

        # Component
        comp_box = ttk.LabelFrame(
            setup_tab,
            text="Chassis Specification Table  [Units: m]",
            padding=10,
            style="Panel.TLabelframe",
        )
        comp_box.pack(fill="x", pady=(0, 8))
        ttk.Label(comp_box, text="Chassis Part").grid(
            row=0, column=0, sticky="w"
        )
        comp_combo = ttk.Combobox(
            comp_box,
            textvariable=self.component_name,
            values=list(CHASSIS_COMPONENTS),
            state="readonly",
        )
        comp_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=2)
        comp_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self.load_component_defaults()
        )

        for row, (label, var, unit) in enumerate(
            [
                ("Length (m)", self.length_var, "m"),
                ("Flange / width (m)", self.width_var, "m"),
                ("Section height (m)", self.thickness_var, "m"),
                ("FOS Target", self.fos_target_var, ""),
            ],
            start=1,
        ):
            ttk.Label(comp_box, text=label).grid(row=row, column=0, sticky="w")
            ttk.Entry(comp_box, textvariable=var, width=14).grid(
                row=row, column=1, sticky="ew", padx=(8, 0), pady=2
            )
            ttk.Label(comp_box, text=unit).grid(
                row=row, column=2, sticky="w", padx=(4, 0)
            )
        comp_box.columnconfigure(1, weight=1)

        self.component_note = ttk.Label(
            comp_box, text="", wraplength=300, style="Sub.TLabel"
        )
        self.component_note.grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

        # Material
        mat_box = ttk.LabelFrame(
            setup_tab,
            text="Material Used For Chassis  [Units: GPa, MPa, kg/m³]",
            padding=10,
            style="Panel.TLabelframe",
        )
        mat_box.pack(fill="x", pady=(0, 8))
        ttk.Label(mat_box, text="Primary").grid(row=0, column=0, sticky="w")
        mat_combo = ttk.Combobox(
            mat_box,
            textvariable=self.material_name,
            values=list(CHASSIS_MATERIALS),
            state="readonly",
        )
        mat_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=2)
        mat_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self.update_material_panel()
        )
        ttk.Label(mat_box, text="Compare").grid(row=1, column=0, sticky="w")
        cmp_combo = ttk.Combobox(
            mat_box,
            textvariable=self.compare_name,
            values=["None"] + list(CHASSIS_MATERIALS),
            state="readonly",
        )
        cmp_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=2)
        self.material_note = ttk.Label(
            mat_box, text="", wraplength=300, style="Sub.TLabel"
        )
        self.material_note.grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )
        mat_box.columnconfigure(1, weight=1)

        # Load
        load_box = ttk.LabelFrame(
            load_tab,
            text="Load Input Table  [Axial/Transverse = N, Pressure = Pa, Torque = N-m]",
            padding=10,
            style="Panel.TLabelframe",
        )
        load_box.pack(fill="both", pady=(0, 8), expand=True)
        ttk.Label(load_box, text="Type").grid(row=0, column=0, sticky="w")
        ttk.Label(load_box, text="Value").grid(row=0, column=1, sticky="w")
        ttk.Label(load_box, text="Zone").grid(row=0, column=2, sticky="w")
        for index in range(4):
            type_var = StringVar(value="Transverse")
            value_var = StringVar(value="0")
            zone_var = StringVar(value="Middle")
            ttk.Combobox(
                load_box,
                textvariable=type_var,
                values=CHASSIS_LOAD_TYPES,
                width=12,
                state="readonly",
            ).grid(row=index + 1, column=0, sticky="ew", pady=2)
            ttk.Entry(load_box, textvariable=value_var, width=10).grid(
                row=index + 1, column=1, sticky="ew", padx=4, pady=2
            )
            ttk.Combobox(
                load_box,
                textvariable=zone_var,
                values=CHASSIS_LOAD_ZONES,
                width=12,
                state="readonly",
            ).grid(row=index + 1, column=2, sticky="ew", pady=2)
            self.load_rows.append((type_var, value_var, zone_var))

        # Boundary
        bc_box = ttk.LabelFrame(
            load_tab,
            text="Boundary Condition",
            padding=10,
            style="Panel.TLabelframe",
        )
        bc_box.pack(fill="x", pady=(0, 8))
        ttk.Combobox(
            bc_box,
            textvariable=self.boundary,
            values=CHASSIS_BOUNDARIES,
            state="readonly",
        ).pack(fill="x")

        # CFD
        cfd_box = ttk.LabelFrame(
            road_tab,
            text="V5 Chassis CFD / Road-Air Load  [Units: km/h, kg/m³, m², deg]",
            padding=10,
            style="Panel.TLabelframe",
        )
        cfd_box.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(
            cfd_box,
            text="Use aerodynamic road load in analysis",
            variable=self.cfd_enabled,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Label(cfd_box, text="Preset").grid(row=1, column=0, sticky="w")
        preset_combo = ttk.Combobox(
            cfd_box,
            textvariable=self.cfd_preset,
            values=list(CFD_PRESETS),
            state="readonly",
        )
        preset_combo.grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=2
        )
        preset_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self.apply_cfd_preset()
        )

        cfd_fields = [
            ("Speed (km/h)", self.cfd_speed_var, "km/h"),
            ("Air density (kg/m³)", self.cfd_density_var, "kg/m³"),
            ("Drag Cd", self.cfd_cd_var, ""),
            ("Lift Cl", self.cfd_cl_var, ""),
            ("Projected area (m²)", self.cfd_area_var, "m²"),
            ("Wind angle (deg)", self.cfd_angle_var, "deg"),
            ("Gust factor", self.cfd_gust_var, ""),
        ]
        for row, (label, var, unit) in enumerate(cfd_fields, start=2):
            ttk.Label(cfd_box, text=label).grid(row=row, column=0, sticky="w")
            ttk.Entry(cfd_box, textvariable=var, width=10).grid(
                row=row, column=1, sticky="ew", padx=(8, 0), pady=2
            )
            ttk.Label(cfd_box, text=unit).grid(
                row=row, column=2, sticky="w", padx=(4, 0)
            )
        ttk.Button(
            cfd_box,
            text="Calculate and Add Road/Air Load",
            command=self.apply_cfd_load,
        ).grid(row=9, column=0, columnspan=3, sticky="ew", pady=(6, 4))
        ttk.Label(
            cfd_box,
            textvariable=self.cfd_summary,
            wraplength=300,
            style="Sub.TLabel",
        ).grid(row=10, column=0, columnspan=3, sticky="w")
        cfd_box.columnconfigure(1, weight=1)

        ttk.Button(
            parent, text="Run Chassis Analysis", command=self.run_analysis
        ).pack(fill="x", ipady=5)

    def build_outputs(self, parent):
        metrics = ttk.Frame(parent)
        metrics.pack(fill="x", pady=(0, 8))
        labels = [
            ("Max Stress", "stress", "MPa"),
            ("Max Strain", "strain", "× 10⁻³"),
            ("Max Deflection", "deflection", "mm"),
            ("Factor of Safety", "fos", ""),
            ("Part Mass", "mass", "kg"),
        ]
        for i, (title, key, unit) in enumerate(labels):
            card = ttk.LabelFrame(
                metrics, text=title, padding=8, style="Panel.TLabelframe"
            )
            card.grid(
                row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0)
            )
            ttk.Label(card, textvariable=self.metric_vars[key], style="Metric.TLabel").pack(
                anchor="w"
            )
            ttk.Label(card, text=unit, style="Sub.TLabel").pack(anchor="w")
            metrics.columnconfigure(i, weight=1)

        figure_size = (8.6, 5.7)
        self.figure = Figure(figsize=figure_size, dpi=100)
        self.axes = [
            self.figure.add_subplot(2, 2, 1),
            self.figure.add_subplot(2, 2, 2),
            self.figure.add_subplot(2, 2, 3),
            self.figure.add_subplot(2, 2, 4),
        ]
        self.figure.tight_layout(pad=3.0)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=True)

        formula_box = ttk.LabelFrame(
            parent,
            text="Strength of Materials Backend Formulas  [Units: N, m, Pa, MPa]",
            padding=10,
            style="Panel.TLabelframe",
        )
        formula_box.pack(fill="x", pady=(8, 0))
        text = (
            "Normal stress: σ = F/A (MPa)    |    Bending stress: σ = M·c/I (MPa)    |    "
            "Shear: τ = 1.5V/A (MPa)    |    Von Mises: σ_vm = √(σ² + 3τ²) (MPa)\n"
            "Strain: ε = σ/E    |    Deflection: SS = FL³/48EI, Cantilever = FL³/3EI, Fixed-Fixed = FL³/192EI  [mm]    |    "
            "FOS = yield (MPa) / max σ_vm (MPa)\n"
            "CFD: q = 0.5·ρ·V² (Pa), pressure = q·Cd·angle factor (Pa), drag = pressure·area (N)"
        )
        ttk.Label(formula_box, text=text, wraplength=900, style="Sub.TLabel").pack(
            anchor="w"
        )

        # Export buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(
            btn_frame, text="Open Graph Window", command=self.open_graph_window
        ).pack(side=RIGHT, padx=(6, 0))
        ttk.Button(
            btn_frame, text="Export PDF Report", command=self.export_pdf
        ).pack(side=RIGHT, padx=(6, 0))
        ttk.Button(
            btn_frame, text="Export PNG Graphs", command=self.export_graphs
        ).pack(side=RIGHT, padx=(6, 0))
        ttk.Button(
            btn_frame, text="Export CSV Results", command=self.export_csv
        ).pack(side=RIGHT)

    def load_component_defaults(self):
        comp = CHASSIS_COMPONENTS[self.component_name.get()]
        self.length_var.set(f"{comp.length_m:g}")
        self.width_var.set(f"{comp.width_m:g}")
        self.thickness_var.set(f"{comp.thickness_m:g}")
        self.cfd_area_var.set(f"{comp.length_m * comp.width_m:g}")
        self.component_note.configure(text=comp.description)
        presets = CHASSIS_LOAD_PRESETS.get(comp.name, [])
        for i, row in enumerate(self.load_rows):
            type_var, value_var, zone_var = row
            if i < len(presets):
                type_var.set(presets[i][0])
                value_var.set(f"{presets[i][1]:g}")
                zone_var.set(presets[i][2])
            else:
                type_var.set("Transverse")
                value_var.set("0")
                zone_var.set("Middle")

    def update_material_panel(self):
        mat = CHASSIS_MATERIALS[self.material_name.get()]
        self.material_note.configure(
            text=(
                f"Standard: {mat.standard}  |  E={mat.youngs_gpa:g} GPa, "
                f"Yield={mat.yield_mpa:g} MPa, Ultimate={mat.ultimate_mpa:g} MPa, "
                f"ν={mat.poisson:g}, ρ={mat.density:g} kg/m³\nUse: {mat.use}"
            )
        )

    def apply_cfd_preset(self):
        preset = CFD_PRESETS[self.cfd_preset.get()]
        self.cfd_speed_var.set(f"{preset['speed_kmh']:g}")
        self.cfd_density_var.set(f"{preset['air_density']:g}")
        self.cfd_cd_var.set(f"{preset['cd']:g}")
        self.cfd_cl_var.set(f"{preset['cl']:g}")
        self.cfd_angle_var.set(f"{preset['wind_angle']:g}")
        self.cfd_gust_var.set(f"{preset['gust']:g}")

    def calculate_cfd_from_inputs(self):
        try:
            speed_kmh = float(self.cfd_speed_var.get())
            air_density = float(self.cfd_density_var.get())
            drag_coefficient = float(self.cfd_cd_var.get())
            lift_coefficient = float(self.cfd_cl_var.get())
            projected_area = float(self.cfd_area_var.get())
            wind_angle = float(self.cfd_angle_var.get())
            gust_factor = float(self.cfd_gust_var.get())
            length_m = float(self.length_var.get())
        except ValueError as exc:
            raise ValueError("Please enter valid numeric CFD values.") from exc

        if (
            speed_kmh < 0
            or air_density <= 0
            or projected_area <= 0
            or gust_factor <= 0
        ):
            raise ValueError(
                "CFD speed, air density, projected area, and gust factor must be valid positive values."
            )
        if drag_coefficient < 0 or lift_coefficient < 0:
            raise ValueError(
                "Drag and lift coefficients cannot be negative."
            )

        return calculate_cfd_load(
            speed_kmh,
            air_density,
            drag_coefficient,
            lift_coefficient,
            projected_area,
            wind_angle,
            gust_factor,
            length_m,
        )

    def apply_cfd_load(self, show_status=True):
        try:
            self.last_cfd = self.calculate_cfd_from_inputs()
        except ValueError as exc:
            if show_status:
                messagebox.showerror("CFD input error", str(exc))
            raise

        pressure_row = self.load_rows[-1]
        pressure_row[0].set("Pressure")
        pressure_row[1].set(f"{self.last_cfd['pressure_pa']:.2f}")
        pressure_row[2].set("Full Span")
        self.cfd_summary.set(
            f"q={self.last_cfd['dynamic_pressure_pa']:.1f} Pa, "
            f"pressure={self.last_cfd['pressure_pa']:.1f} Pa, "
            f"drag={self.last_cfd['drag_n']:.1f} N, "
            f"side={self.last_cfd['side_force_n']:.1f} N, "
            f"Re={self.last_cfd['reynolds']:.2e}"
        )
        if show_status:
            self.status_var.set(
                "CFD aerodynamic pressure added to the last load row."
            )

    def detect_chassis_part_from_filename(self, filename):
        name = filename.lower()
        if "body" in name or "cab" in name or "fitting" in name:
            return "Body Mount Bracket Zone", "Detected body/cab/fitting mount keyword"
        if "cross" in name or "member" in name:
            return "Cross Member", "Detected cross member keyword"
        if (
            "suspension" in name
            or "bracket" in name
            or "mount" in name
        ):
            return (
                "Suspension Bracket Zone",
                "Detected suspension/bracket/mount keyword",
            )
        if "box" in name or "boxed" in name:
            return "Truck Chassis Box Rail", "Detected box/boxed rail keyword"
        if (
            "4x2" in name
            or "four" in name
            or "front" in name
            or "rear" in name
            or "main" in name
        ):
            return (
                "4x2 Truck Main Chassis Rail",
                "Detected 4x2/front/rear/main chassis keyword",
            )
        if (
            "rail" in name
            or "chassis" in name
            or "frame" in name
            or "beam" in name
        ):
            return (
                "Truck Chassis C-Section Rail",
                "Detected chassis/frame/rail keyword",
            )
        return (
            self.component_name.get(),
            "No filename keyword matched; current chassis selection kept",
        )

    def upload_part(self):
        path = filedialog.askopenfilename(
            title="Select part/CAD file",
            filetypes=[
                (
                    "CAD and mesh files",
                    "*.step *.stp *.iges *.igs *.stl *.obj *.prt *.catpart *.sldprt",
                ),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        cad_path = Path(path)
        detected_part, reason = self.detect_chassis_part_from_filename(
            cad_path.name
        )
        self.component_name.set(detected_part)
        self.loaded_cad_path = cad_path
        self.load_component_defaults()
        self.cad_button_var.set("CAD Part Loaded - Change File")
        self.cad_loaded_var.set("CAD PART LOADED")
        self.cad_detail_var.set(
            f"File: {cad_path.name}\n"
            f"Type: {cad_path.suffix.upper().lstrip('.') or 'Unknown'}\n"
            f"Detected part: {detected_part}\n"
            f"{reason}\n"
            f"Path: {cad_path}"
        )
        self.status_var.set(
            f"CAD part loaded: {cad_path.name} -> {detected_part}"
        )
        messagebox.showinfo(
            "CAD part loaded",
            f"Loaded: {cad_path.name}\nDetected: {detected_part}",
        )

    def read_inputs(self):
        comp = CHASSIS_COMPONENTS[self.component_name.get()]
        try:
            length_m = float(self.length_var.get())
            width_m = float(self.width_var.get())
            thickness_m = float(self.thickness_var.get())
            fos_target = float(self.fos_target_var.get())
        except ValueError as exc:
            raise ValueError(
                "Please enter valid numeric component dimensions and FOS target."
            ) from exc

        if (
            length_m <= 0
            or width_m <= 0
            or thickness_m <= 0
            or fos_target <= 0
        ):
            raise ValueError(
                "Length (m), width (m), thickness (m), and FOS target must be greater than zero."
            )

        loads = []
        for type_var, value_var, zone_var in self.load_rows:
            try:
                value = float(value_var.get())
            except ValueError as exc:
                raise ValueError(
                    "Please enter valid numeric load values."
                ) from exc
            loads.append((type_var.get(), value, zone_var.get()))

        return (
            comp.component_type,
            length_m,
            width_m,
            thickness_m,
            loads,
            fos_target,
        )

    def run_analysis(self):
        if self.cfd_enabled.get():
            try:
                self.apply_cfd_load(show_status=False)
            except ValueError as exc:
                messagebox.showerror("CFD input error", str(exc))
                return
        try:
            (
                component_type,
                length_m,
                width_m,
                thickness_m,
                loads,
                fos_target,
            ) = self.read_inputs()
        except ValueError as exc:
            messagebox.showerror("Input error", str(exc))
            return

        material = CHASSIS_MATERIALS[self.material_name.get()]
        self.current_result = calculate_chassis(
            component_type,
            length_m,
            width_m,
            thickness_m,
            material,
            loads,
            self.boundary.get(),
            fos_target,
        )
        result = self.current_result
        self.metric_vars["stress"].set(f"{result['max_stress_mpa']:.2f}")
        self.metric_vars["strain"].set(f"{result['max_strain'] * 1000.0:.4f}")
        self.metric_vars["deflection"].set(f"{result['max_deflection_mm']:.3f}")
        self.metric_vars["fos"].set(f"{result['fos']:.2f}")
        self.metric_vars["mass"].set(f"{result['mass_kg']:.2f}")
        self.draw_plots(material, result)

        if result["fos"] >= fos_target:
            condition = "SAFE"
        elif result["fos"] >= 1.5:
            condition = "MARGINAL"
        else:
            condition = "WEAK / CRITICAL"
        self.status_var.set(
            f"Chassis analysis: {condition}. Max pressure={result['pressure_pa']:.1f} Pa, "
            f"transverse={result['transverse_n']:.1f} N, axial={result['axial_n']:.1f} N."
        )

    def stress_strain_curve(self, material):
        points_x = []
        points_y = []
        yield_strain = material.yield_mpa / (material.youngs_gpa * 1000.0)
        max_strain = yield_strain * 3.0
        for i in range(25):
            eps = max_strain * i / 24.0
            if eps <= yield_strain:
                sig = eps * material.youngs_gpa * 1000.0
            else:
                plastic_ratio = (eps - yield_strain) / max(
                    max_strain - yield_strain, 1e-9
                )
                sig = material.yield_mpa + (
                    material.ultimate_mpa - material.yield_mpa
                ) * plastic_ratio
            points_x.append(eps * 1000.0)
            points_y.append(sig)
        return points_x, points_y

    def draw_plots(self, material, result):
        for ax in self.axes:
            ax.clear()

        ax = self.axes[0]
        ax.plot(
            result["x_mm"],
            result["bending_mpa"],
            label="Bending stress (MPa)",
            color="#2f7dc1",
            linewidth=1.8,
        )
        ax.plot(
            result["x_mm"],
            result["axial_mpa"],
            label="Axial stress (MPa)",
            color="#218c74",
            linewidth=1.5,
        )
        ax.plot(
            result["x_mm"],
            result["von_mises_mpa"],
            label="Von Mises stress (MPa)",
            color="#b36b16",
            linewidth=2.0,
        )
        ax.set_title("Stress Distribution Along Length")
        ax.set_xlabel("Position (mm)")
        ax.set_ylabel("Stress (MPa)")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)

        ax = self.axes[1]
        x1, y1 = self.stress_strain_curve(material)
        ax.plot(
            x1,
            y1,
            label=f"{material.name} ({material.standard})",
            color=material.color,
            linewidth=2.0,
        )
        compare_key = self.compare_name.get()
        if compare_key != "None":
            compare = CHASSIS_MATERIALS[compare_key]
            x2, y2 = self.stress_strain_curve(compare)
            ax.plot(
                x2,
                y2,
                label=f"{compare.name} ({compare.standard})",
                color=compare.color,
                linewidth=1.8,
                linestyle="--",
            )
        ax.set_title("Stress-Strain Material Comparison")
        ax.set_xlabel("Strain (× 10⁻³)")
        ax.set_ylabel("Stress (MPa)")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)

        ax = self.axes[2]
        ax.plot(
            result["load_kn"],
            result["deflection_mm"],
            color=material.color,
            marker="o",
            markersize=3,
            linewidth=1.8,
        )
        ax.set_title("Load vs Deformation")
        ax.set_xlabel("Load (kN)")
        ax.set_ylabel("Deflection (mm)")
        ax.grid(True, alpha=0.25)

        ax = self.axes[3]
        sample_indices = [0, 7, 15, 23, 30]
        labels = ["Z1 Front", "Z2 Quarter", "Z3 Middle", "Z4 Quarter", "Z5 Rear"]
        values = [result["fos_zone"][i] for i in sample_indices]
        colors = [
            "#218c74" if v >= result["fos_target"] else "#b36b16" if v >= 1.5 else "#a83a32"
            for v in values
        ]
        ax.bar(labels, values, color=colors)
        ax.axhline(
            result["fos_target"],
            color="#a83a32",
            linestyle="--",
            linewidth=1.2,
            label="Target FOS",
        )
        ax.set_title("Factor of Safety by Zone")
        ax.set_ylabel("FOS")
        ax.tick_params(axis="x", labelrotation=20)
        ax.grid(True, axis="y", alpha=0.25)
        ax.legend(fontsize=8)

        self.figure.tight_layout(pad=2.4)
        self.canvas.draw()

    def open_graph_window(self):
        if not self.current_result:
            messagebox.showwarning(
                "No results", "Run analysis before opening graphs."
            )
            return

        graph_window = Toplevel(self)
        graph_window.title(
            f"{COMPANY_NAME} - Chassis Analysis Graphs {APP_VERSION}"
        )
        graph_window.geometry("1500x850+120+80")
        graph_window.minsize(1100, 700)

        toolbar = ttk.Frame(graph_window, padding=8)
        toolbar.pack(fill="x")
        ttk.Label(
            toolbar,
            text=f"{COMPANY_NAME} | Graph View - Stress, Strain, Deformation, and FOS",
            style="Title.TLabel",
        ).pack(side=LEFT)
        ttk.Button(
            toolbar,
            text="Save PNG",
            command=lambda: self.save_figure_from_window(graph_fig),
        ).pack(side=RIGHT)

        graph_fig = Figure(figsize=(13.5, 7.2), dpi=100)
        graph_axes = [
            graph_fig.add_subplot(2, 2, 1),
            graph_fig.add_subplot(2, 2, 2),
            graph_fig.add_subplot(2, 2, 3),
            graph_fig.add_subplot(2, 2, 4),
        ]
        graph_canvas = FigureCanvasTkAgg(graph_fig, master=graph_window)
        graph_canvas.get_tk_widget().pack(
            fill=BOTH, expand=True, padx=8, pady=(0, 8)
        )

        old_axes = self.axes
        old_figure = self.figure
        old_canvas = self.canvas
        self.axes = graph_axes
        self.figure = graph_fig
        self.canvas = graph_canvas
        self.draw_plots(
            CHASSIS_MATERIALS[self.material_name.get()], self.current_result
        )
        self.axes = old_axes
        self.figure = old_figure
        self.canvas = old_canvas

    def save_figure_from_window(self, figure):
        path = filedialog.asksaveasfilename(
            title="Save ASM V5 graph window image",
            defaultextension=".png",
            initialfile="asm_v5_chassis_graph_window.png",
            filetypes=[("PNG image", "*.png")],
        )
        if path:
            figure.savefig(path, dpi=200)
            self.status_var.set(f"Saved graph window image: {path}")

    def export_graphs(self):
        if not self.current_result:
            messagebox.showwarning(
                "No results", "Run analysis before exporting graphs."
            )
            return
        path = filedialog.asksaveasfilename(
            title="Save ASM V5 chassis graph image",
            defaultextension=".png",
            initialfile="asm_v5_chassis_graphs.png",
            filetypes=[("PNG image", "*.png")],
        )
        if not path:
            return
        self.figure.savefig(path, dpi=200)
        self.status_var.set(f"Saved chassis graph image: {path}")

    def export_csv(self):
        if not self.current_result:
            messagebox.showwarning(
                "No results", "Run analysis before exporting CSV."
            )
            return
        path = filedialog.asksaveasfilename(
            title="Save ASM V5 chassis result table",
            defaultextension=".csv",
            initialfile="asm_v5_chassis_results.csv",
            filetypes=[("CSV file", "*.csv")],
        )
        if not path:
            return
        result = self.current_result
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "Position (mm)",
                    "Bending (MPa)",
                    "Axial (MPa)",
                    "Shear (MPa)",
                    "Torsion (MPa)",
                    "Von Mises (MPa)",
                    "Strain",
                    "FOS",
                ]
            )
            for row in zip(
                result["x_mm"],
                result["bending_mpa"],
                result["axial_mpa"],
                result["shear_mpa"],
                result["torsion_mpa"],
                result["von_mises_mpa"],
                result["strain"],
                result["fos_zone"],
            ):
                writer.writerow([f"{value:.6g}" for value in row])
            writer.writerow([])
            writer.writerow(["Summary"])
            writer.writerow(["Max stress (MPa)", f"{result['max_stress_mpa']:.6g}"])
            writer.writerow(["Max strain", f"{result['max_strain']:.6g}"])
            writer.writerow(
                ["Max deflection (mm)", f"{result['max_deflection_mm']:.6g}"]
            )
            writer.writerow(["Factor of safety", f"{result['fos']:.6g}"])
            writer.writerow(["Part mass (kg)", f"{result['mass_kg']:.6g}"])
            writer.writerow(["Area (m²)", f"{result['area_m2']:.6g}"])
            writer.writerow(
                ["Second moment (m⁴)", f"{result['inertia_m4']:.6g}"]
            )
            if self.last_cfd:
                writer.writerow([])
                writer.writerow(["CFD aerodynamic load"])
                writer.writerow(
                    [
                        "Effective speed (m/s)",
                        f"{self.last_cfd['effective_speed_ms']:.6g}",
                    ]
                )
                writer.writerow(
                    [
                        "Dynamic pressure (Pa)",
                        f"{self.last_cfd['dynamic_pressure_pa']:.6g}",
                    ]
                )
                writer.writerow(
                    ["Applied pressure (Pa)", f"{self.last_cfd['pressure_pa']:.6g}"]
                )
                writer.writerow(
                    ["Drag force (N)", f"{self.last_cfd['drag_n']:.6g}"]
                )
                writer.writerow(
                    ["Side force (N)", f"{self.last_cfd['side_force_n']:.6g}"]
                )
                writer.writerow(
                    ["Lift force (N)", f"{self.last_cfd['lift_n']:.6g}"]
                )
                writer.writerow(
                    ["Reynolds number", f"{self.last_cfd['reynolds']:.6g}"]
                )
        self.status_var.set(f"Saved chassis result table: {path}")

    def export_pdf(self):
        if not self.current_result:
            messagebox.showwarning(
                "No results", "Run analysis before exporting PDF."
            )
            return
        path = filedialog.asksaveasfilename(
            title="Save ASM V5 chassis PDF report",
            defaultextension=".pdf",
            initialfile="asm_v5_chassis_report.pdf",
            filetypes=[("PDF report", "*.pdf")],
        )
        if not path:
            return

        result = self.current_result
        material = CHASSIS_MATERIALS[self.material_name.get()]
        component = self.component_name.get()
        boundary = self.boundary.get()
        try:
            (
                _component_type,
                length_m,
                width_m,
                thickness_m,
                loads,
                fos_target,
            ) = self.read_inputs()
        except ValueError as exc:
            messagebox.showerror("Input error", str(exc))
            return

        with PdfPages(path) as pdf:
            summary_fig = Figure(figsize=(8.27, 11.69), dpi=120)
            summary_fig.patch.set_facecolor("white")
            ax = summary_fig.add_subplot(1, 1, 1)
            ax.axis("off")

            if result["fos"] >= fos_target:
                condition = "SAFE"
            elif result["fos"] >= 1.5:
                condition = "MARGINAL"
            else:
                condition = "WEAK / CRITICAL"

            load_lines = []
            for idx, (load_type, value, zone) in enumerate(loads, start=1):
                unit = "Pa" if load_type == "Pressure" else "N-m" if load_type == "Torque" else "N"
                load_lines.append(f"  {idx}. {load_type}: {value:g} {unit}, zone: {zone}")
            if self.last_cfd:
                cfd_text = (
                    "\n\nV5 CFD AERODYNAMIC LOAD\n"
                    f"Speed: {float(self.cfd_speed_var.get()):g} km/h\n"
                    f"Effective gust speed: {self.last_cfd['effective_speed_ms']:.3f} m/s\n"
                    f"Air density: {float(self.cfd_density_var.get()):g} kg/m³\n"
                    f"Cd: {float(self.cfd_cd_var.get()):g}, Cl: {float(self.cfd_cl_var.get()):g}\n"
                    f"Projected area: {self.last_cfd['projected_area_m2']:.3f} m²\n"
                    f"Wind angle: {self.last_cfd['wind_angle_deg']:.3f} deg, gust factor: {self.last_cfd['gust_factor']:.3f}\n"
                    f"Dynamic pressure q: {self.last_cfd['dynamic_pressure_pa']:.3f} Pa\n"
                    f"Applied structural pressure: {self.last_cfd['pressure_pa']:.3f} Pa\n"
                    f"Drag force: {self.last_cfd['drag_n']:.3f} N\n"
                    f"Side force estimate: {self.last_cfd['side_force_n']:.3f} N\n"
                    f"Lift/downforce estimate: {self.last_cfd['lift_n']:.3f} N\n"
                    f"Reynolds number estimate: {self.last_cfd['reynolds']:.3e}\n"
                )
            else:
                cfd_text = "\n\nV5 CFD AERODYNAMIC LOAD\nCFD load was not enabled for this report.\n"

            summary_text = (
                f"{COMPANY_NAME.upper()} - INTEGRATED CHASSIS & FRAME ANALYSIS REPORT V5\n"
                f"Module: Chassis CFD & Structural Analysis\n"
                f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
                "PROJECT INPUTS\n"
                f"CAD file: {self.loaded_cad_path.name if self.loaded_cad_path else 'Not loaded'}\n"
                f"CAD path: {self.loaded_cad_path if self.loaded_cad_path else 'Not loaded'}\n"
                f"Component: {component}\n"
                f"Material: {material.name}\n"
                f"Standard: {material.standard}\n"
                f"Material use: {material.use}\n"
                f"Boundary condition: {boundary}\n"
                f"Length: {length_m:g} m\n"
                f"Flange / width: {width_m:g} m\n"
                f"Section height: {thickness_m:g} m\n"
                f"Target factor of safety: {fos_target:g}\n\n"
                "APPLIED LOAD TABLE\n"
                + "\n".join(load_lines)
                + cfd_text
                + "\n\nRESULT SUMMARY\n"
                f"Design condition: {condition}\n"
                f"Maximum Von Mises stress: {result['max_stress_mpa']:.3f} MPa\n"
                f"Maximum strain: {result['max_strain'] * 1000.0:.5f} × 10⁻³\n"
                f"Maximum deflection: {result['max_deflection_mm']:.3f} mm\n"
                f"Factor of safety: {result['fos']:.3f}\n"
                f"Estimated part mass: {result['mass_kg']:.3f} kg\n"
                f"Effective transverse force: {result['transverse_n']:.3f} N\n"
                f"Effective axial force: {result['axial_n']:.3f} N\n"
                f"Applied pressure total: {result['pressure_pa']:.3f} Pa\n"
                f"Applied torque total: {result['torque_nm']:.3f} N-m\n\n"
                "BACKEND FORMULAS\n"
                "Normal stress: σ = F/A (MPa)\n"
                "Bending stress: σ = M·c/I (MPa)\n"
                "Shear stress: τ = 1.5V/A (MPa)\n"
                "Von Mises stress: σ_vm = √(σ² + 3τ²) (MPa)\n"
                "Strain: ε = σ/E\n"
                "Deflection: simply supported FL³/48EI, cantilever FL³/3EI, fixed-fixed FL³/192EI (mm)\n"
                "Factor of safety: FOS = yield (MPa) / max Von Mises (MPa)\n\n"
                "CFD dynamic pressure: q = 0.5·ρ·V² (Pa)\n"
                "Aerodynamic pressure: p = q·Cd·angle factor (Pa)\n"
                "Drag force: Fd = p·projected_area (N)\n"
                "Reynolds number: Re = ρ·V·L/μ\n\n"
                "NOTE\n"
                "This report is for first-pass strength of materials study and project presentation. "
                "Final vehicle structure approval should be done using full validated FEA with correct "
                "CAD geometry, mesh, contacts, welds/bolts, constraints, and load cases per IS 800:2007."
            )
            ax.text(
                0.06,
                0.96,
                summary_text,
                va="top",
                ha="left",
                fontsize=10,
                family="monospace",
                linespacing=1.25,
            )
            pdf.savefig(summary_fig, bbox_inches="tight")

            graph_fig = Figure(figsize=(11.69, 8.27), dpi=120)
            graph_axes = [
                graph_fig.add_subplot(2, 2, 1),
                graph_fig.add_subplot(2, 2, 2),
                graph_fig.add_subplot(2, 2, 3),
                graph_fig.add_subplot(2, 2, 4),
            ]
            old_axes = self.axes
            old_figure = self.figure
            self.axes = graph_axes
            self.figure = graph_fig
            self.draw_plots(material, result)
            pdf.savefig(graph_fig, bbox_inches="tight")
            self.axes = old_axes
            self.figure = old_figure
            self.draw_plots(material, result)

        self.status_var.set(f"Saved chassis PDF report: {path}")


# ==============================================================================
# UI: FRAME SECTION & LOAD ANALYSIS TAB
# ==============================================================================
class FrameLoadTab(ttk.Frame):
    def __init__(self, parent, status_var):
        super().__init__(parent)
        self.status_var = status_var
        self.current_result = None

        self.frame_length_var = StringVar(value="12")
        self.height_var = StringVar(value="400")
        self.flange_var = StringVar(value="100")
        self.thickness_var = StringVar(value="12")
        self.ffl_var = StringVar(value="1.2")
        self.rfl_var = StringVar(value="2.0")
        self.fap_var = StringVar(value="1.2")
        self.rap_var = StringVar(value="10.0")
        self.fa_load_var = StringVar(value="7500")
        self.ra_load_var = StringVar(value="7500")
        self.cab_load_var = StringVar(value="650")
        self.engine_type_var = StringVar(value="Medium diesel engine")
        self.material_var = StringVar(value="HSS 700 Steel (IS 4923:1997)")
        self.fos_target_var = StringVar(value="2.5")
        self.judgement_var = StringVar(value="Not checked")

        self.metric_vars = {
            "z": StringVar(value="-"),
            "moment": StringVar(value="-"),
            "deflection": StringVar(value="-"),
            "fos": StringVar(value="-"),
            "fa": StringVar(value="-"),
            "ra": StringVar(value="-"),
        }
        self.build_ui()
        self.run_analysis()

    def build_ui(self):
        shell = ttk.Frame(self)
        shell.pack(fill=BOTH, expand=True)
        self.scroll_canvas = Canvas(shell, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            shell, orient="vertical", command=self.scroll_canvas.yview
        )
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)
        self.scroll_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill="y")

        page = ttk.Frame(self.scroll_canvas, padding=10)
        window = self.scroll_canvas.create_window((0, 0), window=page, anchor="nw")
        page.bind(
            "<Configure>",
            lambda _e: self.scroll_canvas.configure(
                scrollregion=self.scroll_canvas.bbox("all")
            ),
        )
        self.scroll_canvas.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.itemconfigure(window, width=e.width),
        )
        self.bind_all("<MouseWheel>", self.on_mousewheel)

        # Standards note
        std_label = ttk.Label(
            page,
            text=INDIAN_STANDARDS_NOTE,
            wraplength=900,
            foreground=ASM_BLUE_DARK,
            background="#ffffff",
            font=("Segoe UI", 8, "italic"),
        )
        std_label.pack(fill="x", pady=(0, 8))

        main = ttk.Panedwindow(page, orient="horizontal")
        main.pack(fill=BOTH, expand=True)
        left = ttk.Frame(main, padding=(0, 0, 10, 0))
        right = ttk.Frame(main)
        main.add(left, weight=0)
        main.add(right, weight=1)

        self.build_inputs(left)
        self.build_outputs(right)

    def on_mousewheel(self, event):
        self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def build_inputs(self, parent):
        tabs = ttk.Notebook(parent)
        tabs.pack(fill=BOTH, expand=True, pady=(0, 8))
        frame_tab = ttk.Frame(tabs, padding=6)
        load_tab = ttk.Frame(tabs, padding=6)
        rule_tab = ttk.Frame(tabs, padding=6)
        tabs.add(frame_tab, text="Frame Section  [mm, m]")
        tabs.add(load_tab, text="FA/RA Loads  [kg, m]")
        tabs.add(rule_tab, text="Overhang Rules  [m]")

        section_box = ttk.LabelFrame(
            frame_tab,
            text="Frame Dimensions  [Units: mm for section, m for length]",
            padding=10,
            style="Panel.TLabelframe",
        )
        section_box.pack(fill="x", pady=(0, 8))
        self.add_entry(section_box, "Frame length (m)", self.frame_length_var, "m", 0)
        self.add_entry(
            section_box, "Frame thickness (mm)", self.thickness_var, "mm", 1
        )
        self.add_entry(
            section_box, "Width / flange (mm)", self.flange_var, "mm", 2
        )
        self.add_entry(section_box, "Height (mm)", self.height_var, "mm", 3)
        self.add_combo(
            section_box, "Material", self.material_var, list(FRAME_MATERIALS), 4
        )
        self.add_entry(section_box, "FOS target", self.fos_target_var, "", 5)

        axle_box = ttk.LabelFrame(
            load_tab,
            text="Axle Positions and Loads  [Units: m, kg]",
            padding=10,
            style="Panel.TLabelframe",
        )
        axle_box.pack(fill="x", pady=(0, 8))
        self.add_combo(
            axle_box,
            "Front axle position FAP (m)",
            self.fap_var,
            [str(x) for x in FRONT_AXLE_POSITIONS_M],
            0,
        )
        self.add_combo(
            axle_box,
            "Rear axle position RAP (m)",
            self.rap_var,
            [str(x) for x in REAR_AXLE_POSITIONS_M],
            1,
        )
        self.add_combo(
            axle_box,
            "FA load (kg)",
            self.fa_load_var,
            [str(x) for x in AXLE_LOADS_KG],
            2,
            "kg",
        )
        self.add_combo(
            axle_box,
            "RA load (kg)",
            self.ra_load_var,
            [str(x) for x in AXLE_LOADS_KG],
            3,
            "kg",
        )
        self.add_entry(
            axle_box, "Cab load (kg)", self.cab_load_var, "kg", 4
        )
        self.add_combo(
            axle_box,
            "Engine type",
            self.engine_type_var,
            list(ENGINE_LOADS_KG),
            5,
        )

        rule_box = ttk.LabelFrame(
            rule_tab,
            text="Overhang Rules  [Units: m]",
            padding=10,
            style="Panel.TLabelframe",
        )
        rule_box.pack(fill="x", pady=(0, 8))
        self.add_entry(
            rule_box, "FFL front frame length (m)", self.ffl_var, "m", 0
        )
        self.add_entry(
            rule_box, "RFL rear frame length (m)", self.rfl_var, "m", 1
        )
        ttk.Label(
            rule_box,
            text="Rule: total overhang FFL + RFL (m) cannot exceed 2 × wheelbase (m).",
            wraplength=320,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Button(
            parent, text="Run Frame Analysis", command=self.run_analysis
        ).pack(fill="x", ipady=5)

    def add_entry(self, parent, label, var, unit, row):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", pady=3
        )
        ttk.Entry(parent, textvariable=var, width=16).grid(
            row=row, column=1, sticky="ew", padx=(8, 4), pady=3
        )
        ttk.Label(parent, text=unit).grid(row=row, column=2, sticky="w")
        parent.columnconfigure(1, weight=1)

    def add_combo(self, parent, label, var, values, row, unit=""):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", pady=3
        )
        ttk.Combobox(
            parent, textvariable=var, values=values, width=18, state="readonly"
        ).grid(row=row, column=1, sticky="ew", padx=(8, 4), pady=3)
        ttk.Label(parent, text=unit).grid(row=row, column=2, sticky="w")
        parent.columnconfigure(1, weight=1)

    def build_outputs(self, parent):
        metrics = ttk.Frame(parent)
        metrics.pack(fill="x", pady=(0, 8))
        items = [
            ("Section Modulus", "z", "cm³"),
            ("Max Bending Moment", "moment", "kN-m"),
            ("Max Deflection", "deflection", "mm"),
            ("FOS", "fos", ""),
            ("Calc FA Reaction", "fa", "kg"),
            ("Calc RA Reaction", "ra", "kg"),
        ]
        for i, (title, key, unit) in enumerate(items):
            card = ttk.LabelFrame(
                metrics, text=title, padding=8, style="Panel.TLabelframe"
            )
            card.grid(
                row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0)
            )
            ttk.Label(
                card, textvariable=self.metric_vars[key], style="Metric.TLabel"
            ).pack(anchor="w")
            ttk.Label(card, text=unit).pack(anchor="w")
            metrics.columnconfigure(i, weight=1)

        judgement = ttk.LabelFrame(
            parent,
            text="Input Judgement  [IS 800:2007 / Design Rules]",
            padding=8,
            style="Panel.TLabelframe",
        )
        judgement.pack(fill="x", pady=(0, 8))
        self.judgement_label = ttk.Label(
            judgement, textvariable=self.judgement_var, style="Title.TLabel"
        )
        self.judgement_label.pack(anchor="w")
        self.check_text = ttk.Label(judgement, text="", wraplength=1050)
        self.check_text.pack(anchor="w", pady=(4, 0))

        self.figure = Figure(figsize=(10.5, 6.4), dpi=100)
        self.axes = [self.figure.add_subplot(2, 2, i + 1) for i in range(4)]
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=True)

        # Export buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(
            btn_frame, text="Open Graph Window", command=self.open_graph_window
        ).pack(side=RIGHT, padx=(6, 0))
        ttk.Button(
            btn_frame, text="Export PDF Report", command=self.export_pdf
        ).pack(side=RIGHT, padx=(6, 0))
        ttk.Button(
            btn_frame, text="Export CSV", command=self.export_csv
        ).pack(side=RIGHT)

    def read_inputs(self):
        material = FRAME_MATERIALS[self.material_var.get()]
        return {
            "length_m": float(self.frame_length_var.get()),
            "height_mm": float(self.height_var.get()),
            "flange_mm": float(self.flange_var.get()),
            "thickness_mm": float(self.thickness_var.get()),
            "ffl_m": float(self.ffl_var.get()),
            "rfl_m": float(self.rfl_var.get()),
            "fap_m": float(self.fap_var.get()),
            "rap_m": float(self.rap_var.get()),
            "front_axle_load_kg": float(self.fa_load_var.get()),
            "rear_axle_load_kg": float(self.ra_load_var.get()),
            "cab_load_kg": float(self.cab_load_var.get()),
            "engine_kg": ENGINE_LOADS_KG[self.engine_type_var.get()],
            "engine_load_kg": ENGINE_LOADS_KG[self.engine_type_var.get()],
            "material": material,
            "fos_target": float(self.fos_target_var.get()),
        }

    def run_analysis(self):
        try:
            inputs = self.read_inputs()
            if (
                inputs["length_m"] <= 0
                or inputs["fap_m"] < 0
                or inputs["rap_m"] <= 0
            ):
                raise ValueError(
                    "Frame length (m) and axle positions (m) must be valid positive values."
                )
            self.current_result = frame_analysis(inputs)
        except Exception as exc:
            messagebox.showerror("Input error", str(exc))
            return

        result = self.current_result
        self.metric_vars["z"].set(
            f"{result['section']['section_modulus_cm3']:.1f}"
        )
        self.metric_vars["moment"].set(
            f"{abs(result['max_moment_nm']) / 1000.0:.2f}"
        )
        self.metric_vars["deflection"].set(
            f"{result['max_deflection_mm']:.2f}"
        )
        self.metric_vars["fos"].set(f"{result['fos']:.2f}")
        self.metric_vars["fa"].set(f"{result['front_reaction_n'] / G:.0f}")
        self.metric_vars["ra"].set(f"{result['rear_reaction_n'] / G:.0f}")
        all_ok = all(item["ok"] for item in result["checks"])
        self.judgement_var.set(
            "OK - Inputs satisfy current V5 rules"
            if all_ok
            else "NOT OK - Review highlighted rules"
        )
        self.judgement_label.configure(
            style="Ok.TLabel" if all_ok else "Bad.TLabel"
        )
        self.check_text.configure(
            text="\n".join(
                [
                    ("OK: " if item["ok"] else "NOT OK: ") + item["text"]
                    for item in result["checks"]
                ]
            )
        )
        self.draw_plots()
        self.status_var.set(
            f"Frame analysis complete. Payload={result['payload_kg']:.0f} kg, "
            f"frame self weight={result['frame_self_weight_kg']:.0f} kg."
        )

    def draw_plots(self):
        result = self.current_result
        for ax in self.axes:
            ax.clear()

        ax = self.axes[0]
        ax.plot(
            result["sections_x_m"],
            result["section_modulus_cm3"],
            color=ASM_BLUE,
            linewidth=2,
        )
        ax.set_title("Frame Section Modulus by Cut Section")
        ax.set_xlabel("Frame section position (m)")
        ax.set_ylabel("Section modulus (cm³)")
        ax.grid(True, alpha=0.25)

        ax = self.axes[1]
        ax.plot(
            result["x_m"],
            result["deflection_mm"],
            color="#1f8a70",
            linewidth=2,
        )
        ax.set_title("Frame Deflection")
        ax.set_xlabel("Frame position (m)")
        ax.set_ylabel("Deflection (mm)")
        ax.grid(True, alpha=0.25)

        ax = self.axes[2]
        ax.plot(
            result["x_m"],
            [m / 1000.0 for m in result["moment_nm"]],
            color="#b36b16",
            linewidth=2,
        )
        ax.fill_between(
            result["x_m"],
            [m / 1000.0 for m in result["moment_nm"]],
            alpha=0.12,
            color="#b36b16",
        )
        ax.set_title("Frame Bending Moment Diagram")
        ax.set_xlabel("Frame position (m)")
        ax.set_ylabel("Bending moment (kN-m)")
        ax.grid(True, alpha=0.25)

        ax = self.axes[3]
        ax.step(
            result["x_m"],
            [v / 1000.0 for v in result["shear_n"]],
            where="post",
            color="#a83a32",
            linewidth=1.8,
        )
        ax.axhline(0, color="#222", linewidth=0.8)
        ax.set_title("Shear Force Diagram")
        ax.set_xlabel("Frame position (m)")
        ax.set_ylabel("Shear force (kN)")
        ax.grid(True, alpha=0.25)
        self.figure.tight_layout(pad=2.3)
        self.canvas.draw()

    def open_graph_window(self):
        if not self.current_result:
            return
        win = Toplevel(self)
        win.title(f"{COMPANY_NAME} - Frame Graphs {APP_VERSION}")
        win.geometry("1500x850+120+80")
        fig = Figure(figsize=(13.5, 7.2), dpi=100)
        old_figure, old_axes, old_canvas = self.figure, self.axes, self.canvas
        self.figure = fig
        self.axes = [fig.add_subplot(2, 2, i + 1) for i in range(4)]
        self.canvas = FigureCanvasTkAgg(fig, master=win)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=True, padx=8, pady=8)
        self.draw_plots()
        self.figure, self.axes, self.canvas = old_figure, old_axes, old_canvas

    def export_csv(self):
        if not self.current_result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="asm_v5_frame_results.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        result = self.current_result
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["x (m)", "shear (N)", "moment (N-m)", "deflection (mm)", "stress (MPa)"]
            )
            for row in zip(
                result["x_m"],
                result["shear_n"],
                result["moment_nm"],
                result["deflection_mm"],
                result["stress_mpa"],
            ):
                writer.writerow([f"{value:.6g}" for value in row])
            writer.writerow([])
            writer.writerow(
                ["Section modulus (cm³)", f"{result['section']['section_modulus_cm3']:.6g}"]
            )
            writer.writerow(["FOS", f"{result['fos']:.6g}"])
        self.status_var.set(f"Frame CSV saved: {path}")

    def export_pdf(self):
        if not self.current_result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile="asm_v5_frame_report.pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return
        result = self.current_result
        inputs = self.read_inputs()
        with PdfPages(path) as pdf:
            summary = Figure(figsize=(8.27, 11.69), dpi=120)
            ax = summary.add_subplot(1, 1, 1)
            ax.axis("off")
            text = (
                f"{COMPANY_NAME.upper()} - INTEGRATED CHASSIS & FRAME ANALYSIS REPORT V5\n"
                f"Module: Frame Section & Chassis Load Analysis\n"
                f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
                f"Frame length: {inputs['length_m']} m\n"
                f"Frame thickness: {inputs['thickness_mm']} mm\n"
                f"Width/flange: {inputs['flange_mm']} mm\n"
                f"Height: {inputs['height_mm']} mm\n"
                f"FAP: {inputs['fap_m']} m, RAP: {inputs['rap_m']} m\n"
                f"FFL: {inputs['ffl_m']} m, RFL: {inputs['rfl_m']} m\n"
                f"FA load: {inputs['front_axle_load_kg']} kg, RA load: {inputs['rear_axle_load_kg']} kg\n"
                f"Cab load: {inputs['cab_load_kg']} kg, Engine: {self.engine_type_var.get()} ({inputs['engine_load_kg']} kg)\n"
                f"Material: {inputs['material'].name}\n"
                f"Standard: {inputs['material'].standard}\n\n"
                f"Section modulus: {result['section']['section_modulus_cm3']:.2f} cm³\n"
                f"Max bending moment: {abs(result['max_moment_nm'])/1000:.2f} kN-m\n"
                f"Max deflection: {result['max_deflection_mm']:.2f} mm\n"
                f"FOS: {result['fos']:.2f}\n"
                f"Judgement: {self.judgement_var.get()}\n\n"
                + "\n".join(
                    [
                        ("OK: " if item["ok"] else "NOT OK: ") + item["text"]
                        for item in result["checks"]
                    ]
                )
            )
            ax.text(0.05, 0.96, text, va="top", family="monospace", fontsize=9)
            pdf.savefig(summary, bbox_inches="tight")

            graph_fig = Figure(figsize=(11.69, 8.27), dpi=120)
            old_figure, old_axes, old_canvas = self.figure, self.axes, self.canvas
            self.figure = graph_fig
            self.axes = [graph_fig.add_subplot(2, 2, i + 1) for i in range(4)]
            self.canvas = FigureCanvasTkAgg(self.figure, master=self)
            self.draw_plots()
            pdf.savefig(graph_fig, bbox_inches="tight")
            self.figure, self.axes, self.canvas = old_figure, old_axes, old_canvas
            self.draw_plots()
        self.status_var.set(f"Frame PDF saved: {path}")


# ==============================================================================
# MAIN APPLICATION
# ==============================================================================
class IntegratedAppV5:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(f"{COMPANY_NAME} - {APP_TITLE} {APP_VERSION}")
        self.configure_window()

        # Styles
        self.setup_styles()

        # Header
        self.build_header()

        # Notebook with both modules
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        self.status_var = StringVar(
            value="Welcome to ASM Integrated V5. Select a tab to begin analysis."
        )

        # Tab 1: Chassis
        self.chassis_tab = ChassisStructuralTab(self.notebook, self.status_var)
        self.notebook.add(
            self.chassis_tab, text="  Chassis CFD & Structural Analysis  "
        )

        # Tab 2: Frame
        self.frame_tab = FrameLoadTab(self.notebook, self.status_var)
        self.notebook.add(
            self.frame_tab, text="  Frame Section & Load Analysis  "
        )

        # Footer
        self.build_footer()

    def configure_window(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(1500, int(screen_w * 0.95))
        height = min(950, int(screen_h * 0.90))
        self.root.geometry(
            f"{width}x{height}+{max((screen_w - width) // 2, 0)}+{max((screen_h - height) // 2, 0)}"
        )
        self.root.minsize(1200, 750)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 9), background="#ffffff")
        style.configure("TFrame", background="#ffffff")
        style.configure("Brand.TFrame", background=ASM_BLUE)
        style.configure(
            "BrandTitle.TLabel",
            background=ASM_BLUE,
            foreground="#ffffff",
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "BrandSub.TLabel",
            background=ASM_BLUE,
            foreground="#e7f0fb",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Title.TLabel",
            background="#ffffff",
            foreground=ASM_BLUE_DARK,
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "Metric.TLabel",
            background="#ffffff",
            foreground=ASM_BLUE_DARK,
            font=("Segoe UI", 15, "bold"),
        )
        style.configure(
            "Ok.TLabel",
            background="#eaf7ee",
            foreground=ASM_GREEN,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "Bad.TLabel",
            background="#fdeceb",
            foreground=ASM_RED,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "Panel.TLabelframe",
            background=ASM_PANEL,
            bordercolor="#c9d6e6",
            relief="solid",
        )
        style.configure(
            "Panel.TLabelframe.Label",
            background=ASM_PANEL,
            foreground=ASM_BLUE_DARK,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure("Sub.TLabel", foreground="#4d5b6b", background="#ffffff")
        style.configure("TButton", padding=(10, 5))
        style.map("TButton", background=[("active", "#e7eef7")])
        style.configure("TNotebook", background="#ffffff", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(16, 10),
            foreground=ASM_BLUE_DARK,
            font=("Segoe UI", 9, "bold"),
        )

    def build_header(self):
        header = ttk.Frame(self.root, style="Brand.TFrame", padding=(14, 12))
        header.pack(fill="x", padx=10, pady=(10, 0))
        if LOGO_PATH.exists():
            try:
                logo = PhotoImage(file=str(LOGO_PATH))
                if logo.width() > 200:
                    factor = max(1, math.ceil(logo.width() / 200))
                    logo = logo.subsample(factor, factor)
                ttk.Label(header, image=logo, background=ASM_BLUE).pack(
                    side=LEFT, padx=(0, 16)
                )
                # Keep reference
                self.logo_image = logo
            except Exception:
                pass
        text_box = ttk.Frame(header, style="Brand.TFrame")
        text_box.pack(side=LEFT, fill="x", expand=True)
        ttk.Label(
            text_box, text=COMPANY_NAME, style="BrandTitle.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            text_box,
            text=f"{APP_TITLE} {APP_VERSION} | Integrated Chassis CFD + Frame Section & Load Analysis",
            style="BrandSub.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        ttk.Label(
            header,
            text="engineering innovation",
            style="BrandSub.TLabel",
        ).pack(side=RIGHT, padx=(10, 0))

    def build_footer(self):
        footer = ttk.Frame(self.root, padding=(10, 6))
        footer.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(footer, textvariable=self.status_var).pack(side=LEFT)
        ttk.Label(
            footer,
            text="Units: m, mm, cm³, MPa, N, kN, kg  |  Standards: IS 2062:2011, IS 800:2007, IS 4923:1997",
            foreground="#888888",
        ).pack(side=RIGHT)


def main():
    root = Tk()
    app = IntegratedAppV5(root)
    root.mainloop()
    return app


if __name__ == "__main__":
    main()