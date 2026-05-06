"""
Chassis fairing structural analysis desktop app.

This Python version is based on the supplied HTML concept and the chassis
reference documents. It is a calculation and visualization tool for early ASM
project study work. It is not a replacement for full FEA validation in ANSYS,
HyperMesh, Abaqus, or similar tools.
"""
#python chassis_fairing_analysis_app.py

from __future__ import annotations

import csv
import math
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, BooleanVar, Canvas, END, LEFT, RIGHT, StringVar, Tk, filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402


@dataclass(frozen=True)
class Material:
    name: str
    youngs_gpa: float
    yield_mpa: float
    ultimate_mpa: float
    poisson: float
    density: float
    color: str


@dataclass(frozen=True)
class Component:
    name: str
    length_m: float
    width_m: float
    thickness_m: float
    component_type: str
    description: str


MATERIALS = {
    "ASTM A36 Steel": Material("ASTM A36 Steel", 200.0, 250.0, 400.0, 0.30, 7850, "#2f7dc1"),
    "Aluminum 6061-T6": Material("Aluminum 6061-T6", 68.9, 276.0, 310.0, 0.33, 2700, "#218c74"),
    "CFRP Carbon Fiber": Material("CFRP Carbon Fiber", 70.0, 600.0, 700.0, 0.10, 1600, "#303030"),
    "Titanium Ti-6Al-4V": Material("Titanium Ti-6Al-4V", 113.8, 880.0, 950.0, 0.342, 4430, "#b36b16"),
    "HSS 700 Steel": Material("HSS 700 Steel", 200.0, 700.0, 780.0, 0.30, 7850, "#a83a32"),
    "Polypropylene": Material("Polypropylene", 1.5, 30.0, 35.0, 0.42, 900, "#7b63b8"),
}

COMPONENTS = {
    "Roof Fairing Panel": Component(
        "Roof Fairing Panel",
        2.0,
        0.80,
        0.003,
        "plate",
        "Thin roof fairing plate supported by roof/chassis frame. Typical aerodynamic pressure load.",
    ),
    "Side Fairing": Component(
        "Side Fairing",
        3.0,
        0.60,
        0.0025,
        "plate",
        "Side aerodynamic fairing mounted from chassis rails. Good for side wind and bracket load study.",
    ),
    "Chassis Beam C-Section": Component(
        "Chassis Beam C-Section",
        5.0,
        0.08,
        0.20,
        "cbeam",
        "C-section frame member, approximated from beam theory for bending and axial load checks.",
    ),
    "Mounting Bracket": Component(
        "Mounting Bracket",
        0.15,
        0.10,
        0.008,
        "block",
        "Fairing-to-chassis bracket. Useful for local force and bolt reaction approximation.",
    ),
    "Aerodynamic Deflector": Component(
        "Aerodynamic Deflector",
        1.2,
        0.40,
        0.002,
        "plate",
        "Thin external deflector surface, mostly pressure driven.",
    ),
}

LOAD_PRESETS = {
    "Roof Fairing Panel": [("Pressure", 1200.0, "Full Span"), ("Transverse", 2500.0, "Middle"), ("Axial", 500.0, "Front")],
    "Side Fairing": [("Pressure", 900.0, "Full Span"), ("Transverse", 1800.0, "Middle"), ("Torque", 350.0, "Rear")],
    "Chassis Beam C-Section": [("Transverse", 8000.0, "Middle"), ("Axial", 3000.0, "Front"), ("Torque", 1200.0, "Rear")],
    "Mounting Bracket": [("Transverse", 1500.0, "Bolt Area"), ("Axial", 800.0, "Base"), ("Pressure", 0.0, "Full Span")],
    "Aerodynamic Deflector": [("Pressure", 1400.0, "Full Span"), ("Transverse", 1200.0, "Middle"), ("Axial", 250.0, "Front")],
}

LOAD_TYPES = ("Axial", "Transverse", "Pressure", "Torque")
LOAD_ZONES = ("Front", "Middle", "Rear", "Full Span", "Bolt Area", "Base")
BOUNDARIES = ("Simply Supported", "Cantilever", "Fixed-Fixed")
CFD_PRESETS = {
    "Highway cruise": {"speed_kmh": 80.0, "air_density": 1.225, "cd": 0.70, "cl": 0.05, "wind_angle": 0.0, "gust": 1.0},
    "Highway gust": {"speed_kmh": 100.0, "air_density": 1.225, "cd": 0.85, "cl": 0.08, "wind_angle": 20.0, "gust": 1.25},
    "Crosswind study": {"speed_kmh": 90.0, "air_density": 1.225, "cd": 0.95, "cl": 0.10, "wind_angle": 35.0, "gust": 1.20},
    "Low speed yard": {"speed_kmh": 30.0, "air_density": 1.225, "cd": 0.60, "cl": 0.02, "wind_angle": 0.0, "gust": 1.0},
}


def calculate_cfd_load(speed_kmh, air_density, drag_coefficient, lift_coefficient, projected_area, wind_angle_deg, gust_factor, length_m):
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
    reynolds = air_density * effective_speed * max(length_m, 1e-6) / air_viscosity
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


def section_area(component_type: str, width_m: float, thickness_m: float) -> float:
    if component_type == "cbeam":
        web_height = thickness_m
        flange_width = width_m
        wall_t = 0.010
        return 2.0 * flange_width * wall_t + max(web_height - 2.0 * wall_t, wall_t) * wall_t
    return max(width_m * thickness_m, 1e-9)


def second_moment(component_type: str, width_m: float, thickness_m: float) -> float:
    if component_type == "cbeam":
        b = width_m
        h = thickness_m
        t = 0.010
        inner_b = max(b - 2.0 * t, t)
        inner_h = max(h - 2.0 * t, t)
        return max((b * h**3 / 12.0) - (inner_b * inner_h**3 / 12.0), 1e-12)
    return max(width_m * thickness_m**3 / 12.0, 1e-12)


def zone_factor(zone: str) -> float:
    return {
        "Front": 0.80,
        "Middle": 1.00,
        "Rear": 0.80,
        "Full Span": 0.65,
        "Bolt Area": 1.25,
        "Base": 1.15,
    }.get(zone, 1.0)


def calculate(component_type, length_m, width_m, thickness_m, material, loads, boundary, fos_target):
    area = section_area(component_type, width_m, thickness_m)
    inertia = second_moment(component_type, width_m, thickness_m)
    c = max(thickness_m / 2.0, 1e-6)
    e_pa = material.youngs_gpa * 1e9

    axial_n = 0.0
    transverse_n = 0.0
    pressure_pa = 0.0
    torque_nm = 0.0
    weighted_transverse = 0.0

    for load_type, value, zone in loads:
        factor = zone_factor(zone)
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
        max_deflection_mm = total_force * length_m**3 / (3.0 * e_pa * inertia) * 1000.0
    elif boundary == "Fixed-Fixed":
        max_deflection_mm = total_force * length_m**3 / (192.0 * e_pa * inertia) * 1000.0
    else:
        max_deflection_mm = total_force * length_m**3 / (48.0 * e_pa * inertia) * 1000.0

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

    result = {
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
    return result


class ChassisApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Chassis Fairing Structural Analysis V2")
        self.root.geometry("1280x820")
        self.root.minsize(1120, 720)
        self.current_result = None

        self.component_name = StringVar(value="Roof Fairing Panel")
        self.material_name = StringVar(value="ASTM A36 Steel")
        self.compare_name = StringVar(value="Aluminum 6061-T6")
        self.boundary = StringVar(value="Simply Supported")
        self.status_text = StringVar(value="Upload/select a part, edit the table, then run analysis.")

        self.length_var = StringVar()
        self.width_var = StringVar()
        self.thickness_var = StringVar()
        self.fos_target_var = StringVar(value="2.5")
        self.cfd_enabled = BooleanVar(value=True)
        self.cfd_preset = StringVar(value="Highway gust")
        self.cfd_speed_var = StringVar(value="100")
        self.cfd_density_var = StringVar(value="1.225")
        self.cfd_cd_var = StringVar(value="0.85")
        self.cfd_cl_var = StringVar(value="0.08")
        self.cfd_area_var = StringVar(value="1.6")
        self.cfd_angle_var = StringVar(value="20")
        self.cfd_gust_var = StringVar(value="1.25")
        self.cfd_summary = StringVar(value="CFD load not calculated yet.")
        self.last_cfd = None

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
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Sub.TLabel", foreground="#555")
        style.configure("Metric.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Warn.TLabel", foreground="#a83a32")

        scroll_shell = ttk.Frame(self.root)
        scroll_shell.pack(fill=BOTH, expand=True)

        self.scroll_canvas = Canvas(scroll_shell, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(scroll_shell, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scroll_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.scrollbar.pack(side=RIGHT, fill="y")

        container = ttk.Frame(self.scroll_canvas, padding=12)
        self.scroll_window = self.scroll_canvas.create_window((0, 0), window=container, anchor="nw")
        container.bind(
            "<Configure>",
            lambda event: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")),
        )
        self.scroll_canvas.bind(
            "<Configure>",
            lambda event: self.scroll_canvas.itemconfigure(self.scroll_window, width=event.width),
        )
        self.root.bind_all("<MouseWheel>", self.on_mousewheel)

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="Daimler Trucks - Chassis Fairing Structural Analysis V2", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="CFD-style aerodynamic loading plus stress, strain, deformation, factor of safety, and material comparison.",
            style="Sub.TLabel",
        ).pack(anchor="w")

        main = ttk.Panedwindow(container, orient="horizontal")
        main.pack(fill=BOTH, expand=True)

        left = ttk.Frame(main, padding=(0, 0, 10, 0))
        right = ttk.Frame(main)
        main.add(left, weight=0)
        main.add(right, weight=1)

        self.build_inputs(left)
        self.build_outputs(right)

        footer = ttk.Frame(container)
        footer.pack(fill="x", pady=(8, 0))
        ttk.Label(footer, textvariable=self.status_text).pack(side=LEFT)
        ttk.Button(footer, text="Export PDF Report", command=self.export_pdf).pack(side=RIGHT, padx=(6, 0))
        ttk.Button(footer, text="Export PNG Graphs", command=self.export_graphs).pack(side=RIGHT, padx=(6, 0))
        ttk.Button(footer, text="Export CSV Results", command=self.export_csv).pack(side=RIGHT)

    def on_mousewheel(self, event):
        self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def build_inputs(self, parent):
        file_box = ttk.LabelFrame(parent, text="Part / CAD Input", padding=10)
        file_box.pack(fill="x", pady=(0, 8))
        ttk.Button(file_box, text="Upload Part File", command=self.upload_part).pack(fill="x")
        ttk.Label(
            file_box,
            text="Supported for preset selection: file names containing roof, side, beam, bracket, deflector, chassis.",
            wraplength=300,
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        comp_box = ttk.LabelFrame(parent, text="Component Specification Table", padding=10)
        comp_box.pack(fill="x", pady=(0, 8))
        ttk.Label(comp_box, text="Machine Part").grid(row=0, column=0, sticky="w")
        comp_combo = ttk.Combobox(comp_box, textvariable=self.component_name, values=list(COMPONENTS), state="readonly")
        comp_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=2)
        comp_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_component_defaults())

        for row, (label, var, unit) in enumerate(
            [
                ("Length", self.length_var, "m"),
                ("Width / flange", self.width_var, "m"),
                ("Thickness / height", self.thickness_var, "m"),
                ("FOS Target", self.fos_target_var, ""),
            ],
            start=1,
        ):
            ttk.Label(comp_box, text=label).grid(row=row, column=0, sticky="w")
            ttk.Entry(comp_box, textvariable=var, width=14).grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=2)
            ttk.Label(comp_box, text=unit).grid(row=row, column=2, sticky="w", padx=(4, 0))
        comp_box.columnconfigure(1, weight=1)

        self.component_note = ttk.Label(comp_box, text="", wraplength=300, style="Sub.TLabel")
        self.component_note.grid(row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))

        mat_box = ttk.LabelFrame(parent, text="Material", padding=10)
        mat_box.pack(fill="x", pady=(0, 8))
        ttk.Label(mat_box, text="Primary").grid(row=0, column=0, sticky="w")
        mat_combo = ttk.Combobox(mat_box, textvariable=self.material_name, values=list(MATERIALS), state="readonly")
        mat_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=2)
        mat_combo.bind("<<ComboboxSelected>>", lambda _event: self.update_material_panel())
        ttk.Label(mat_box, text="Compare").grid(row=1, column=0, sticky="w")
        cmp_combo = ttk.Combobox(mat_box, textvariable=self.compare_name, values=["None"] + list(MATERIALS), state="readonly")
        cmp_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=2)
        self.material_note = ttk.Label(mat_box, text="", wraplength=300, style="Sub.TLabel")
        self.material_note.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        mat_box.columnconfigure(1, weight=1)

        load_box = ttk.LabelFrame(parent, text="Load Input Table", padding=10)
        load_box.pack(fill="both", pady=(0, 8), expand=True)
        ttk.Label(load_box, text="Type").grid(row=0, column=0, sticky="w")
        ttk.Label(load_box, text="Value").grid(row=0, column=1, sticky="w")
        ttk.Label(load_box, text="Zone").grid(row=0, column=2, sticky="w")
        for index in range(4):
            type_var = StringVar(value="Transverse")
            value_var = StringVar(value="0")
            zone_var = StringVar(value="Middle")
            ttk.Combobox(load_box, textvariable=type_var, values=LOAD_TYPES, width=12, state="readonly").grid(
                row=index + 1, column=0, sticky="ew", pady=2
            )
            ttk.Entry(load_box, textvariable=value_var, width=10).grid(row=index + 1, column=1, sticky="ew", padx=4, pady=2)
            ttk.Combobox(load_box, textvariable=zone_var, values=LOAD_ZONES, width=12, state="readonly").grid(
                row=index + 1, column=2, sticky="ew", pady=2
            )
            self.load_rows.append((type_var, value_var, zone_var))
        ttk.Label(load_box, text="Units: Axial/Transverse = N, Pressure = Pa, Torque = N-m", style="Sub.TLabel").grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

        cfd_box = ttk.LabelFrame(parent, text="V2 CFD Aerodynamic Load", padding=10)
        cfd_box.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(cfd_box, text="Use CFD load in analysis", variable=self.cfd_enabled).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        ttk.Label(cfd_box, text="Preset").grid(row=1, column=0, sticky="w")
        preset_combo = ttk.Combobox(cfd_box, textvariable=self.cfd_preset, values=list(CFD_PRESETS), state="readonly")
        preset_combo.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=2)
        preset_combo.bind("<<ComboboxSelected>>", lambda _event: self.apply_cfd_preset())

        cfd_fields = [
            ("Speed", self.cfd_speed_var, "km/h"),
            ("Air density", self.cfd_density_var, "kg/m3"),
            ("Drag Cd", self.cfd_cd_var, ""),
            ("Lift Cl", self.cfd_cl_var, ""),
            ("Projected area", self.cfd_area_var, "m2"),
            ("Wind angle", self.cfd_angle_var, "deg"),
            ("Gust factor", self.cfd_gust_var, ""),
        ]
        for row, (label, var, unit) in enumerate(cfd_fields, start=2):
            ttk.Label(cfd_box, text=label).grid(row=row, column=0, sticky="w")
            ttk.Entry(cfd_box, textvariable=var, width=10).grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=2)
            ttk.Label(cfd_box, text=unit).grid(row=row, column=2, sticky="w", padx=(4, 0))
        ttk.Button(cfd_box, text="Calculate and Add CFD Load", command=self.apply_cfd_load).grid(
            row=9, column=0, columnspan=3, sticky="ew", pady=(6, 4)
        )
        ttk.Label(cfd_box, textvariable=self.cfd_summary, wraplength=300, style="Sub.TLabel").grid(
            row=10, column=0, columnspan=3, sticky="w"
        )
        cfd_box.columnconfigure(1, weight=1)

        bc_box = ttk.LabelFrame(parent, text="Boundary Condition", padding=10)
        bc_box.pack(fill="x", pady=(0, 8))
        ttk.Combobox(bc_box, textvariable=self.boundary, values=BOUNDARIES, state="readonly").pack(fill="x")

        ttk.Button(parent, text="Run Analysis", command=self.run_analysis).pack(fill="x", ipady=5)

    def build_outputs(self, parent):
        metrics = ttk.Frame(parent)
        metrics.pack(fill="x", pady=(0, 8))
        labels = [
            ("Max Stress", "stress", "MPa"),
            ("Max Strain", "strain", "x 10^-3"),
            ("Max Deflection", "deflection", "mm"),
            ("Factor of Safety", "fos", ""),
            ("Part Mass", "mass", "kg"),
        ]
        for i, (title, key, unit) in enumerate(labels):
            card = ttk.LabelFrame(metrics, text=title, padding=8)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            ttk.Label(card, textvariable=self.metric_vars[key], style="Metric.TLabel").pack(anchor="w")
            ttk.Label(card, text=unit, style="Sub.TLabel").pack(anchor="w")
            metrics.columnconfigure(i, weight=1)

        self.figure = Figure(figsize=(9.6, 6.4), dpi=100)
        self.axes = [
            self.figure.add_subplot(2, 2, 1),
            self.figure.add_subplot(2, 2, 2),
            self.figure.add_subplot(2, 2, 3),
            self.figure.add_subplot(2, 2, 4),
        ]
        self.figure.tight_layout(pad=3.0)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=True)

        formula_box = ttk.LabelFrame(parent, text="Strength of Materials Backend Formulas", padding=10)
        formula_box.pack(fill="x", pady=(8, 0))
        text = (
            "Normal stress: sigma = F/A    |    Bending stress: sigma = M*c/I    |    "
            "Shear: tau = 1.5V/A    |    Von Mises: sigma_vm = sqrt(sigma^2 + 3*tau^2)\n"
            "Strain: epsilon = sigma/E    |    Deflection: SS FL^3/48EI, Cantilever FL^3/3EI, Fixed-Fixed FL^3/192EI    |    "
            "FOS = yield strength / max von Mises stress\n"
            "CFD load: q = 0.5*rho*V^2, pressure = q*Cd*angle factor, drag = pressure*projected area"
        )
        ttk.Label(formula_box, text=text, wraplength=900, style="Sub.TLabel").pack(anchor="w")

    def load_component_defaults(self):
        comp = COMPONENTS[self.component_name.get()]
        self.length_var.set(f"{comp.length_m:g}")
        self.width_var.set(f"{comp.width_m:g}")
        self.thickness_var.set(f"{comp.thickness_m:g}")
        self.cfd_area_var.set(f"{comp.length_m * comp.width_m:g}")
        self.component_note.configure(text=comp.description)
        presets = LOAD_PRESETS.get(comp.name, [])
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
        mat = MATERIALS[self.material_name.get()]
        self.material_note.configure(
            text=(
                f"E={mat.youngs_gpa:g} GPa, Yield={mat.yield_mpa:g} MPa, "
                f"Ultimate={mat.ultimate_mpa:g} MPa, nu={mat.poisson:g}, Density={mat.density:g} kg/m3"
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

        if speed_kmh < 0 or air_density <= 0 or projected_area <= 0 or gust_factor <= 0:
            raise ValueError("CFD speed, air density, projected area, and gust factor must be valid positive values.")
        if drag_coefficient < 0 or lift_coefficient < 0:
            raise ValueError("Drag and lift coefficients cannot be negative.")

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
            f"q={self.last_cfd['dynamic_pressure_pa']:.1f} Pa, pressure={self.last_cfd['pressure_pa']:.1f} Pa, "
            f"drag={self.last_cfd['drag_n']:.1f} N, side={self.last_cfd['side_force_n']:.1f} N, "
            f"Re={self.last_cfd['reynolds']:.2e}"
        )
        if show_status:
            self.status_text.set("CFD aerodynamic pressure added to the last load row.")

    def upload_part(self):
        path = filedialog.askopenfilename(
            title="Select part/CAD file",
            filetypes=[
                ("CAD and mesh files", "*.step *.stp *.iges *.igs *.stl *.obj *.prt *.catpart *.sldprt"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        name = Path(path).name.lower()
        if "roof" in name:
            self.component_name.set("Roof Fairing Panel")
        elif "side" in name or "fairing" in name:
            self.component_name.set("Side Fairing")
        elif "beam" in name or "chassis" in name or "frame" in name:
            self.component_name.set("Chassis Beam C-Section")
        elif "bracket" in name or "mount" in name:
            self.component_name.set("Mounting Bracket")
        elif "deflector" in name:
            self.component_name.set("Aerodynamic Deflector")
        self.load_component_defaults()
        self.status_text.set(f"Loaded preset from file name: {Path(path).name}")

    def read_inputs(self):
        comp = COMPONENTS[self.component_name.get()]
        try:
            length_m = float(self.length_var.get())
            width_m = float(self.width_var.get())
            thickness_m = float(self.thickness_var.get())
            fos_target = float(self.fos_target_var.get())
        except ValueError as exc:
            raise ValueError("Please enter valid numeric component dimensions and FOS target.") from exc

        if length_m <= 0 or width_m <= 0 or thickness_m <= 0 or fos_target <= 0:
            raise ValueError("Length, width, thickness, and FOS target must be greater than zero.")

        loads = []
        for type_var, value_var, zone_var in self.load_rows:
            try:
                value = float(value_var.get())
            except ValueError as exc:
                raise ValueError("Please enter valid numeric load values.") from exc
            loads.append((type_var.get(), value, zone_var.get()))

        return comp.component_type, length_m, width_m, thickness_m, loads, fos_target

    def run_analysis(self):
        if self.cfd_enabled.get():
            try:
                self.apply_cfd_load(show_status=False)
            except ValueError as exc:
                messagebox.showerror("CFD input error", str(exc))
                return
        try:
            component_type, length_m, width_m, thickness_m, loads, fos_target = self.read_inputs()
        except ValueError as exc:
            messagebox.showerror("Input error", str(exc))
            return

        material = MATERIALS[self.material_name.get()]
        self.current_result = calculate(
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
        self.status_text.set(
            f"Analysis complete: {condition}. Max pressure={result['pressure_pa']:.1f} Pa, "
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
                plastic_ratio = (eps - yield_strain) / max(max_strain - yield_strain, 1e-9)
                sig = material.yield_mpa + (material.ultimate_mpa - material.yield_mpa) * plastic_ratio
            points_x.append(eps * 1000.0)
            points_y.append(sig)
        return points_x, points_y

    def draw_plots(self, material, result):
        for ax in self.axes:
            ax.clear()

        ax = self.axes[0]
        ax.plot(result["x_mm"], result["bending_mpa"], label="Bending stress", color="#2f7dc1", linewidth=1.8)
        ax.plot(result["x_mm"], result["axial_mpa"], label="Axial stress", color="#218c74", linewidth=1.5)
        ax.plot(result["x_mm"], result["von_mises_mpa"], label="Von Mises stress", color="#b36b16", linewidth=2.0)
        ax.set_title("Stress Distribution Along Length")
        ax.set_xlabel("Position (mm)")
        ax.set_ylabel("Stress (MPa)")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)

        ax = self.axes[1]
        x1, y1 = self.stress_strain_curve(material)
        ax.plot(x1, y1, label=material.name, color=material.color, linewidth=2.0)
        compare_key = self.compare_name.get()
        if compare_key != "None":
            compare = MATERIALS[compare_key]
            x2, y2 = self.stress_strain_curve(compare)
            ax.plot(x2, y2, label=compare.name, color=compare.color, linewidth=1.8, linestyle="--")
        ax.set_title("Stress-Strain Material Comparison")
        ax.set_xlabel("Strain (x 10^-3)")
        ax.set_ylabel("Stress (MPa)")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)

        ax = self.axes[2]
        ax.plot(result["load_kn"], result["deflection_mm"], color=material.color, marker="o", markersize=3, linewidth=1.8)
        ax.set_title("Load vs Deformation")
        ax.set_xlabel("Load (kN)")
        ax.set_ylabel("Deflection (mm)")
        ax.grid(True, alpha=0.25)

        ax = self.axes[3]
        sample_indices = [0, 7, 15, 23, 30]
        labels = ["Z1 Front", "Z2 Quarter", "Z3 Middle", "Z4 Quarter", "Z5 Rear"]
        values = [result["fos_zone"][i] for i in sample_indices]
        colors = ["#218c74" if v >= result["fos_target"] else "#b36b16" if v >= 1.5 else "#a83a32" for v in values]
        ax.bar(labels, values, color=colors)
        ax.axhline(result["fos_target"], color="#a83a32", linestyle="--", linewidth=1.2, label="Target FOS")
        ax.set_title("Factor of Safety by Zone")
        ax.set_ylabel("FOS")
        ax.tick_params(axis="x", labelrotation=20)
        ax.grid(True, axis="y", alpha=0.25)
        ax.legend(fontsize=8)

        self.figure.tight_layout(pad=2.4)
        self.canvas.draw()

    def export_graphs(self):
        if not self.current_result:
            messagebox.showwarning("No results", "Run analysis before exporting graphs.")
            return
        path = filedialog.asksaveasfilename(
            title="Save non-editable graph image",
            defaultextension=".png",
            initialfile="chassis_fairing_analysis_graphs.png",
            filetypes=[("PNG image", "*.png")],
        )
        if not path:
            return
        self.figure.savefig(path, dpi=200)
        self.status_text.set(f"Saved non-editable graph image: {path}")

    def export_csv(self):
        if not self.current_result:
            messagebox.showwarning("No results", "Run analysis before exporting CSV.")
            return
        path = filedialog.asksaveasfilename(
            title="Save result table",
            defaultextension=".csv",
            initialfile="chassis_fairing_analysis_results.csv",
            filetypes=[("CSV file", "*.csv")],
        )
        if not path:
            return
        result = self.current_result
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Position mm", "Bending MPa", "Axial MPa", "Shear MPa", "Torsion MPa", "Von Mises MPa", "Strain", "FOS"])
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
            writer.writerow(["Max stress MPa", f"{result['max_stress_mpa']:.6g}"])
            writer.writerow(["Max strain", f"{result['max_strain']:.6g}"])
            writer.writerow(["Max deflection mm", f"{result['max_deflection_mm']:.6g}"])
            writer.writerow(["Factor of safety", f"{result['fos']:.6g}"])
            writer.writerow(["Part mass kg", f"{result['mass_kg']:.6g}"])
            writer.writerow(["Area m2", f"{result['area_m2']:.6g}"])
            writer.writerow(["Second moment m4", f"{result['inertia_m4']:.6g}"])
            if self.last_cfd:
                writer.writerow([])
                writer.writerow(["CFD aerodynamic load"])
                writer.writerow(["Effective speed m/s", f"{self.last_cfd['effective_speed_ms']:.6g}"])
                writer.writerow(["Dynamic pressure Pa", f"{self.last_cfd['dynamic_pressure_pa']:.6g}"])
                writer.writerow(["Applied pressure Pa", f"{self.last_cfd['pressure_pa']:.6g}"])
                writer.writerow(["Drag force N", f"{self.last_cfd['drag_n']:.6g}"])
                writer.writerow(["Side force N", f"{self.last_cfd['side_force_n']:.6g}"])
                writer.writerow(["Lift force N", f"{self.last_cfd['lift_n']:.6g}"])
                writer.writerow(["Reynolds number", f"{self.last_cfd['reynolds']:.6g}"])
        self.status_text.set(f"Saved result table: {path}")

    def export_pdf(self):
        if not self.current_result:
            messagebox.showwarning("No results", "Run analysis before exporting PDF.")
            return
        path = filedialog.asksaveasfilename(
            title="Save PDF report",
            defaultextension=".pdf",
            initialfile="chassis_fairing_analysis_report.pdf",
            filetypes=[("PDF report", "*.pdf")],
        )
        if not path:
            return

        result = self.current_result
        material = MATERIALS[self.material_name.get()]
        component = self.component_name.get()
        boundary = self.boundary.get()
        try:
            _component_type, length_m, width_m, thickness_m, loads, fos_target = self.read_inputs()
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
                    "\n\nV2 CFD AERODYNAMIC LOAD\n"
                    f"Speed: {float(self.cfd_speed_var.get()):g} km/h\n"
                    f"Effective gust speed: {self.last_cfd['effective_speed_ms']:.3f} m/s\n"
                    f"Air density: {float(self.cfd_density_var.get()):g} kg/m3\n"
                    f"Cd: {float(self.cfd_cd_var.get()):g}, Cl: {float(self.cfd_cl_var.get()):g}\n"
                    f"Projected area: {self.last_cfd['projected_area_m2']:.3f} m2\n"
                    f"Wind angle: {self.last_cfd['wind_angle_deg']:.3f} deg, gust factor: {self.last_cfd['gust_factor']:.3f}\n"
                    f"Dynamic pressure q: {self.last_cfd['dynamic_pressure_pa']:.3f} Pa\n"
                    f"Applied structural pressure: {self.last_cfd['pressure_pa']:.3f} Pa\n"
                    f"Drag force: {self.last_cfd['drag_n']:.3f} N\n"
                    f"Side force estimate: {self.last_cfd['side_force_n']:.3f} N\n"
                    f"Lift/downforce estimate: {self.last_cfd['lift_n']:.3f} N\n"
                    f"Reynolds number estimate: {self.last_cfd['reynolds']:.3e}\n"
                )
            else:
                cfd_text = "\n\nV2 CFD AERODYNAMIC LOAD\nCFD load was not enabled for this report.\n"

            summary_text = (
                "CHASSIS FAIRING STRUCTURAL ANALYSIS REPORT\n"
                f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
                "PROJECT INPUTS\n"
                f"Component: {component}\n"
                f"Material: {material.name}\n"
                f"Boundary condition: {boundary}\n"
                f"Length: {length_m:g} m\n"
                f"Width / flange: {width_m:g} m\n"
                f"Thickness / height: {thickness_m:g} m\n"
                f"Target factor of safety: {fos_target:g}\n\n"
                "APPLIED LOAD TABLE\n"
                + "\n".join(load_lines)
                + cfd_text
                + "\n\nRESULT SUMMARY\n"
                f"Design condition: {condition}\n"
                f"Maximum Von Mises stress: {result['max_stress_mpa']:.3f} MPa\n"
                f"Maximum strain: {result['max_strain'] * 1000.0:.5f} x 10^-3\n"
                f"Maximum deflection: {result['max_deflection_mm']:.3f} mm\n"
                f"Factor of safety: {result['fos']:.3f}\n"
                f"Estimated part mass: {result['mass_kg']:.3f} kg\n"
                f"Effective transverse force: {result['transverse_n']:.3f} N\n"
                f"Effective axial force: {result['axial_n']:.3f} N\n"
                f"Applied pressure total: {result['pressure_pa']:.3f} Pa\n"
                f"Applied torque total: {result['torque_nm']:.3f} N-m\n\n"
                "BACKEND FORMULAS\n"
                "Normal stress: sigma = F/A\n"
                "Bending stress: sigma = M*c/I\n"
                "Shear stress: tau = 1.5V/A\n"
                "Von Mises stress: sigma_vm = sqrt(sigma^2 + 3*tau^2)\n"
                "Strain: epsilon = sigma/E\n"
                "Deflection: simply supported FL^3/48EI, cantilever FL^3/3EI, fixed-fixed FL^3/192EI\n"
                "Factor of safety: FOS = yield strength / maximum Von Mises stress\n\n"
                "CFD dynamic pressure: q = 0.5*rho*V^2\n"
                "Aerodynamic pressure: p = q*Cd*angle factor\n"
                "Drag force: Fd = p*projected area\n"
                "Reynolds number: Re = rho*V*L/mu\n\n"
                "NOTE\n"
                "This report is for first-pass strength of materials study and project presentation. "
                "Final vehicle structure approval should be done using full validated FEA with correct "
                "CAD geometry, mesh, contacts, welds/bolts, constraints, and load cases."
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

        self.status_text.set(f"Saved PDF report: {path}")


def main():
    root = Tk()
    app = ChassisApp(root)
    root.mainloop()
    return app


if __name__ == "__main__":
    main()
