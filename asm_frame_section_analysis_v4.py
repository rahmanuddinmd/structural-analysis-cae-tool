"""
ASM Technologies Ltd - Frame Section & Chassis Load Analysis V4.

Dedicated frame/chassis calculator for FA/RA load checks, axle positions,
front/rear overhang validation, section modulus, deflection, bending moment,
and shear force diagrams.
"""
# python asm_frame_section_analysis_v4.py

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, Canvas, PhotoImage, StringVar, Tk, Toplevel, filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402


COMPANY_NAME = "ASM Technologies Ltd"
APP_TITLE = "Frame Section & Chassis Load Analysis"
APP_VERSION = "V4"
LOGO_PATH = Path(__file__).with_name("ASM-Logo.png")
ASM_BLUE = "#104984"
ASM_BLUE_DARK = "#0a2d52"
ASM_GREEN = "#167a3a"
ASM_RED = "#b3261e"
G = 9.80665


@dataclass(frozen=True)
class Material:
    name: str
    youngs_gpa: float
    yield_mpa: float
    density: float
    use: str


MATERIALS = {
    "IS 2062 E250 Mild Steel": Material("IS 2062 E250 Mild Steel", 200.0, 250.0, 7850.0, "Common chassis/frame fabrication steel."),
    "IS 2062 E350 Structural Steel": Material("IS 2062 E350 Structural Steel", 200.0, 350.0, 7850.0, "Higher strength chassis rail and cross-member material."),
    "HSS 550 Steel": Material("HSS 550 Steel", 200.0, 550.0, 7850.0, "High strength steel for weight-reduced frame study."),
    "HSS 700 Steel": Material("HSS 700 Steel", 200.0, 700.0, 7850.0, "Heavy-duty high strength truck frame comparison material."),
    "Domex 700 MC": Material("Domex 700 MC", 210.0, 700.0, 7850.0, "Automotive high strength steel for chassis and transport structures."),
}

ENGINE_LOADS_KG = {
    "Small diesel engine": 420.0,
    "Medium diesel engine": 650.0,
    "Heavy diesel engine": 900.0,
    "Electric motor + pack": 1200.0,
}
AXLE_LOADS_KG = [3000, 4000, 5000, 6000, 7500, 9000, 10500, 12000, 14000, 16000]
FRONT_AXLE_POSITIONS_M = [0.9, 1.0, 1.1, 1.2, 1.3, 1.5]
REAR_AXLE_POSITIONS_M = [3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0, 8.0, 9.0, 10.0]


def channel_section_properties(height_mm: float, flange_mm: float, thickness_mm: float):
    h = height_mm / 1000.0
    b = flange_mm / 1000.0
    t = thickness_mm / 1000.0
    if min(h, b, t) <= 0:
        raise ValueError("Frame height, flange width, and thickness must be greater than zero.")
    if t >= h / 2 or t >= b:
        raise ValueError("Thickness is too large for the selected C-channel dimensions.")

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
    corrected = [val - (y_f + slope_correction * (x - fap_m)) for x, val in zip(x_values, y)]
    return corrected


def frame_analysis(inputs):
    length = inputs["length_m"]
    fap = inputs["fap_m"]
    rap = inputs["rap_m"]
    ffl = inputs["ffl_m"]
    rfl = inputs["rfl_m"]
    material = inputs["material"]
    section = channel_section_properties(inputs["height_mm"], inputs["flange_mm"], inputs["thickness_mm"])
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
        {"name": "Cab load", "x": max(0.15, min(fap * 0.55, length)), "n": cab_load_n},
        {"name": "Engine load", "x": max(0.20, min(fap + 0.35, length)), "n": engine_load_n},
    ]

    udl_start = max(fap, 0.0)
    udl_end = min(length, rap + max(rfl * 0.60, 0.0))
    udl_length = max(udl_end - udl_start, 0.1)
    payload_udl_npm = payload_n / udl_length
    frame_udl_npm = frame_self_weight_n / length

    equivalent_loads = loads + [
        {"name": "Payload equivalent", "x": udl_start + udl_length / 2.0, "n": payload_n},
        {"name": "Frame self weight", "x": length / 2.0, "n": frame_self_weight_n},
    ]
    total_down = sum(load["n"] for load in equivalent_loads)
    moment_about_front = sum(load["n"] * (load["x"] - fap) for load in equivalent_loads)
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

    deflection_m = integrate_deflection(x_values, moment, e_pa, section["inertia_m4"], fap, rap)
    stress_mpa = [abs(m) / section["section_modulus_m3"] / 1e6 for m in moment]
    max_moment = max(moment, key=lambda value: abs(value))
    max_stress = max(stress_mpa)
    max_deflection_mm = max(abs(value) for value in deflection_m) * 1000.0
    fos = material.yield_mpa / max(max_stress, 1e-6)

    sections_x = [length * i / 24.0 for i in range(25)]
    section_modulus = [section["section_modulus_cm3"] for _ in sections_x]
    utilization = [min(abs(interpolate(x_values, stress_mpa, x)) / material.yield_mpa * 100.0, 999.0) for x in sections_x]

    checks = []
    checks.append(check_item(fap < rap, "FAP must be before RAP."))
    checks.append(check_item(abs(ffl - fap) <= 0.15, "FFL should approximately match front axle position."))
    checks.append(check_item(abs((length - rap) - rfl) <= 0.15, "RFL should approximately match length - rear axle position."))
    checks.append(check_item(ffl + rfl <= 2.0 * wheelbase, "Total overhang FFL + RFL must not be more than 2 x wheelbase."))
    checks.append(check_item(ffl <= wheelbase, "Front overhang should not exceed wheelbase."))
    checks.append(check_item(rfl <= wheelbase, "Rear overhang should not exceed wheelbase."))
    checks.append(check_item(fos >= inputs["fos_target"], "Factor of safety must meet target."))
    checks.append(check_item(max_deflection_mm <= length * 1000.0 / 300.0, "Frame deflection should be within L/300 guideline."))

    front_error = abs(front_reaction_n - front_axle_target_n) / max(front_axle_target_n, 1.0) * 100.0
    rear_error = abs(rear_reaction_n - rear_axle_target_n) / max(rear_axle_target_n, 1.0) * 100.0
    checks.append(check_item(front_error <= 15.0, "Calculated front reaction should be within 15% of selected FA load."))
    checks.append(check_item(rear_error <= 15.0, "Calculated rear reaction should be within 15% of selected RA load."))

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


def interpolate(xs, ys, x):
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


class FrameV4App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{COMPANY_NAME} - {APP_TITLE} {APP_VERSION}")
        self.logo_image = None
        self.current_result = None
        self.configure_window()

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
        self.material_var = StringVar(value="HSS 700 Steel")
        self.fos_target_var = StringVar(value="2.5")
        self.status_var = StringVar(value="Enter frame inputs and run V4 analysis.")
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

    def configure_window(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(1500, int(screen_w * 0.92))
        height = min(900, int(screen_h * 0.86))
        self.root.geometry(f"{width}x{height}+{max((screen_w-width)//2,0)}+{max((screen_h-height)//2,0)}")
        self.root.minsize(1180, 720)

    def build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 9), background="#ffffff")
        style.configure("TFrame", background="#ffffff")
        style.configure("Brand.TFrame", background=ASM_BLUE)
        style.configure("BrandTitle.TLabel", background=ASM_BLUE, foreground="#ffffff", font=("Segoe UI", 17, "bold"))
        style.configure("BrandSub.TLabel", background=ASM_BLUE, foreground="#e7f0fb")
        style.configure("Title.TLabel", background="#ffffff", foreground=ASM_BLUE_DARK, font=("Segoe UI", 11, "bold"))
        style.configure("Metric.TLabel", background="#ffffff", foreground=ASM_BLUE_DARK, font=("Segoe UI", 15, "bold"))
        style.configure("Ok.TLabel", background="#eaf7ee", foreground=ASM_GREEN, font=("Segoe UI", 12, "bold"))
        style.configure("Bad.TLabel", background="#fdeceb", foreground=ASM_RED, font=("Segoe UI", 12, "bold"))
        style.configure("Panel.TLabelframe", background="#f4f7fb", bordercolor="#c9d6e6")
        style.configure("Panel.TLabelframe.Label", background="#f4f7fb", foreground=ASM_BLUE_DARK, font=("Segoe UI", 9, "bold"))
        style.configure("TButton", padding=(10, 5))

        shell = ttk.Frame(self.root)
        shell.pack(fill=BOTH, expand=True)
        self.scroll_canvas = Canvas(shell, highlightthickness=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)
        self.scroll_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill="y")
        page = ttk.Frame(self.scroll_canvas, padding=10)
        window = self.scroll_canvas.create_window((0, 0), window=page, anchor="nw")
        page.bind("<Configure>", lambda _event: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))
        self.scroll_canvas.bind("<Configure>", lambda event: self.scroll_canvas.itemconfigure(window, width=event.width))
        self.root.bind_all("<MouseWheel>", lambda event: self.scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        header = ttk.Frame(page, style="Brand.TFrame", padding=(14, 10))
        header.pack(fill="x", pady=(0, 10))
        if LOGO_PATH.exists():
            self.logo_image = PhotoImage(file=str(LOGO_PATH)).subsample(4, 4)
            ttk.Label(header, image=self.logo_image, background=ASM_BLUE).pack(side=LEFT, padx=(0, 16))
        text_box = ttk.Frame(header, style="Brand.TFrame")
        text_box.pack(side=LEFT, fill="x", expand=True)
        ttk.Label(text_box, text=COMPANY_NAME, style="BrandTitle.TLabel").pack(anchor="w")
        ttk.Label(text_box, text=f"{APP_TITLE} {APP_VERSION} | Section modulus, deflection, BMD, SFD, and rule judgement", style="BrandSub.TLabel").pack(anchor="w")

        main = ttk.Panedwindow(page, orient="horizontal")
        main.pack(fill=BOTH, expand=True)
        left = ttk.Frame(main, padding=(0, 0, 10, 0))
        right = ttk.Frame(main)
        main.add(left, weight=0)
        main.add(right, weight=1)
        self.build_inputs(left)
        self.build_outputs(right)

        footer = ttk.Frame(page)
        footer.pack(fill="x", pady=(8, 0))
        ttk.Label(footer, textvariable=self.status_var).pack(side=LEFT)
        ttk.Button(footer, text="Open Graph Window", command=self.open_graph_window).pack(side=RIGHT, padx=(6, 0))
        ttk.Button(footer, text="Export PDF Report", command=self.export_pdf).pack(side=RIGHT, padx=(6, 0))
        ttk.Button(footer, text="Export CSV", command=self.export_csv).pack(side=RIGHT)

    def build_inputs(self, parent):
        tabs = ttk.Notebook(parent)
        tabs.pack(fill=BOTH, expand=True, pady=(0, 8))
        frame_tab = ttk.Frame(tabs, padding=6)
        load_tab = ttk.Frame(tabs, padding=6)
        rule_tab = ttk.Frame(tabs, padding=6)
        tabs.add(frame_tab, text="Frame Section")
        tabs.add(load_tab, text="FA/RA Loads")
        tabs.add(rule_tab, text="Rules")

        section_box = ttk.LabelFrame(frame_tab, text="Frame Thickness, Width (Flange), Height", padding=10, style="Panel.TLabelframe")
        section_box.pack(fill="x", pady=(0, 8))
        self.add_entry(section_box, "Frame length", self.frame_length_var, "m", 0)
        self.add_entry(section_box, "Frame thickness", self.thickness_var, "mm", 1)
        self.add_entry(section_box, "Width (flange)", self.flange_var, "mm", 2)
        self.add_entry(section_box, "Height", self.height_var, "mm", 3)
        self.add_combo(section_box, "Material", self.material_var, list(MATERIALS), 4)
        self.add_entry(section_box, "FOS target", self.fos_target_var, "", 5)

        axle_box = ttk.LabelFrame(load_tab, text="Axle Positions and Loads", padding=10, style="Panel.TLabelframe")
        axle_box.pack(fill="x", pady=(0, 8))
        self.add_combo(axle_box, "Front axle position (FAP)", self.fap_var, [str(x) for x in FRONT_AXLE_POSITIONS_M], 0)
        self.add_combo(axle_box, "Rear axle position (RAP)", self.rap_var, [str(x) for x in REAR_AXLE_POSITIONS_M], 1)
        self.add_combo(axle_box, "FA load", self.fa_load_var, [str(x) for x in AXLE_LOADS_KG], 2, "kg")
        self.add_combo(axle_box, "RA load", self.ra_load_var, [str(x) for x in AXLE_LOADS_KG], 3, "kg")
        self.add_entry(axle_box, "Cab load", self.cab_load_var, "kg", 4)
        self.add_combo(axle_box, "Engine type", self.engine_type_var, list(ENGINE_LOADS_KG), 5)

        rule_box = ttk.LabelFrame(rule_tab, text="Overhang Rules", padding=10, style="Panel.TLabelframe")
        rule_box.pack(fill="x", pady=(0, 8))
        self.add_entry(rule_box, "FFL front frame length", self.ffl_var, "m", 0)
        self.add_entry(rule_box, "RFL rear frame length", self.rfl_var, "m", 1)
        ttk.Label(rule_box, text="Rule: total overhang FFL + RFL cannot be more than 2 x wheelbase.", wraplength=320).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Button(parent, text="Run Frame Analysis", command=self.run_analysis).pack(fill="x", ipady=5)

    def add_entry(self, parent, label, var, unit, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(parent, textvariable=var, width=16).grid(row=row, column=1, sticky="ew", padx=(8, 4), pady=3)
        ttk.Label(parent, text=unit).grid(row=row, column=2, sticky="w")
        parent.columnconfigure(1, weight=1)

    def add_combo(self, parent, label, var, values, row, unit=""):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        ttk.Combobox(parent, textvariable=var, values=values, width=18, state="readonly").grid(row=row, column=1, sticky="ew", padx=(8, 4), pady=3)
        ttk.Label(parent, text=unit).grid(row=row, column=2, sticky="w")
        parent.columnconfigure(1, weight=1)

    def build_outputs(self, parent):
        metrics = ttk.Frame(parent)
        metrics.pack(fill="x", pady=(0, 8))
        items = [
            ("Section Modulus", "z", "cm3"),
            ("Max Bending Moment", "moment", "kN-m"),
            ("Max Deflection", "deflection", "mm"),
            ("FOS", "fos", ""),
            ("Calc FA Reaction", "fa", "kg"),
            ("Calc RA Reaction", "ra", "kg"),
        ]
        for i, (title, key, unit) in enumerate(items):
            card = ttk.LabelFrame(metrics, text=title, padding=8, style="Panel.TLabelframe")
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            ttk.Label(card, textvariable=self.metric_vars[key], style="Metric.TLabel").pack(anchor="w")
            ttk.Label(card, text=unit).pack(anchor="w")
            metrics.columnconfigure(i, weight=1)

        judgement = ttk.LabelFrame(parent, text="Input Judgement", padding=8, style="Panel.TLabelframe")
        judgement.pack(fill="x", pady=(0, 8))
        self.judgement_label = ttk.Label(judgement, textvariable=self.judgement_var, style="Title.TLabel")
        self.judgement_label.pack(anchor="w")
        self.check_text = ttk.Label(judgement, text="", wraplength=1050)
        self.check_text.pack(anchor="w", pady=(4, 0))

        self.figure = Figure(figsize=(10.5, 6.4), dpi=100)
        self.axes = [self.figure.add_subplot(2, 2, i + 1) for i in range(4)]
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    def read_inputs(self):
        material = MATERIALS[self.material_var.get()]
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
            if inputs["length_m"] <= 0 or inputs["fap_m"] < 0 or inputs["rap_m"] <= 0:
                raise ValueError("Frame length and axle positions must be valid positive values.")
            self.current_result = frame_analysis(inputs)
        except Exception as exc:
            messagebox.showerror("Input error", str(exc))
            return

        result = self.current_result
        self.metric_vars["z"].set(f"{result['section']['section_modulus_cm3']:.1f}")
        self.metric_vars["moment"].set(f"{abs(result['max_moment_nm']) / 1000.0:.2f}")
        self.metric_vars["deflection"].set(f"{result['max_deflection_mm']:.2f}")
        self.metric_vars["fos"].set(f"{result['fos']:.2f}")
        self.metric_vars["fa"].set(f"{result['front_reaction_n'] / G:.0f}")
        self.metric_vars["ra"].set(f"{result['rear_reaction_n'] / G:.0f}")
        all_ok = all(item["ok"] for item in result["checks"])
        self.judgement_var.set("OK - Inputs satisfy current V4 rules" if all_ok else "NOT OK - Review highlighted rules")
        self.judgement_label.configure(style="Ok.TLabel" if all_ok else "Bad.TLabel")
        self.check_text.configure(text="\n".join([("OK: " if item["ok"] else "NOT OK: ") + item["text"] for item in result["checks"]]))
        self.draw_plots()
        self.status_var.set(f"Analysis complete. Payload equivalent = {result['payload_kg']:.0f} kg, frame self weight = {result['frame_self_weight_kg']:.0f} kg.")

    def draw_plots(self):
        result = self.current_result
        for ax in self.axes:
            ax.clear()

        ax = self.axes[0]
        ax.plot(result["sections_x_m"], result["section_modulus_cm3"], color=ASM_BLUE, linewidth=2)
        ax.set_title("Frame Section Modulus by Cut Section")
        ax.set_xlabel("Frame section position (m)")
        ax.set_ylabel("Section modulus (cm3)")
        ax.grid(True, alpha=0.25)

        ax = self.axes[1]
        ax.plot(result["x_m"], result["deflection_mm"], color="#1f8a70", linewidth=2)
        ax.set_title("Frame Deflection")
        ax.set_xlabel("Frame position (m)")
        ax.set_ylabel("Deflection (mm)")
        ax.grid(True, alpha=0.25)

        ax = self.axes[2]
        ax.plot(result["x_m"], [m / 1000.0 for m in result["moment_nm"]], color="#b36b16", linewidth=2)
        ax.fill_between(result["x_m"], [m / 1000.0 for m in result["moment_nm"]], alpha=0.12, color="#b36b16")
        ax.set_title("Frame Bending Moment Diagram")
        ax.set_xlabel("Frame position (m)")
        ax.set_ylabel("Bending moment (kN-m)")
        ax.grid(True, alpha=0.25)

        ax = self.axes[3]
        ax.step(result["x_m"], [v / 1000.0 for v in result["shear_n"]], where="post", color="#a83a32", linewidth=1.8)
        ax.axhline(0, color="#222", linewidth=0.8)
        ax.set_title("Shear Force Drawing")
        ax.set_xlabel("Frame position (m)")
        ax.set_ylabel("Shear force (kN)")
        ax.grid(True, alpha=0.25)
        self.figure.tight_layout(pad=2.3)
        self.canvas.draw()

    def open_graph_window(self):
        if not self.current_result:
            return
        win = Toplevel(self.root)
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
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="asm_frame_section_analysis_v4_results.csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        result = self.current_result
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["x m", "shear N", "moment N-m", "deflection mm", "stress MPa"])
            for row in zip(result["x_m"], result["shear_n"], result["moment_nm"], result["deflection_mm"], result["stress_mpa"]):
                writer.writerow([f"{value:.6g}" for value in row])
            writer.writerow([])
            writer.writerow(["Section modulus cm3", f"{result['section']['section_modulus_cm3']:.6g}"])
            writer.writerow(["FOS", f"{result['fos']:.6g}"])
        self.status_var.set(f"CSV saved: {path}")

    def export_pdf(self):
        if not self.current_result:
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="asm_frame_section_analysis_v4_report.pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        result = self.current_result
        inputs = self.read_inputs()
        with PdfPages(path) as pdf:
            summary = Figure(figsize=(8.27, 11.69), dpi=120)
            ax = summary.add_subplot(1, 1, 1)
            ax.axis("off")
            text = (
                f"{COMPANY_NAME.upper()} - FRAME SECTION & CHASSIS LOAD ANALYSIS REPORT V4\n"
                f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
                f"Frame length: {inputs['length_m']} m\n"
                f"Frame thickness: {inputs['thickness_mm']} mm\n"
                f"Width/flange: {inputs['flange_mm']} mm\n"
                f"Height: {inputs['height_mm']} mm\n"
                f"FAP: {inputs['fap_m']} m, RAP: {inputs['rap_m']} m\n"
                f"FFL: {inputs['ffl_m']} m, RFL: {inputs['rfl_m']} m\n"
                f"FA load: {inputs['front_axle_load_kg']} kg, RA load: {inputs['rear_axle_load_kg']} kg\n"
                f"Cab load: {inputs['cab_load_kg']} kg, Engine: {self.engine_type_var.get()} ({inputs['engine_load_kg']} kg)\n"
                f"Material: {inputs['material'].name}\n\n"
                f"Section modulus: {result['section']['section_modulus_cm3']:.2f} cm3\n"
                f"Max bending moment: {abs(result['max_moment_nm'])/1000:.2f} kN-m\n"
                f"Max deflection: {result['max_deflection_mm']:.2f} mm\n"
                f"FOS: {result['fos']:.2f}\n"
                f"Judgement: {self.judgement_var.get()}\n\n"
                + "\n".join([("OK: " if item["ok"] else "NOT OK: ") + item["text"] for item in result["checks"]])
            )
            ax.text(0.05, 0.96, text, va="top", family="monospace", fontsize=9)
            pdf.savefig(summary, bbox_inches="tight")

            graph_fig = Figure(figsize=(11.69, 8.27), dpi=120)
            old_figure, old_axes, old_canvas = self.figure, self.axes, self.canvas
            self.figure = graph_fig
            self.axes = [graph_fig.add_subplot(2, 2, i + 1) for i in range(4)]
            self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
            self.draw_plots()
            pdf.savefig(graph_fig, bbox_inches="tight")
            self.figure, self.axes, self.canvas = old_figure, old_axes, old_canvas
            self.draw_plots()
        self.status_var.set(f"PDF saved: {path}")


def main():
    root = Tk()
    app = FrameV4App(root)
    root.mainloop()
    return app


if __name__ == "__main__":
    main()
