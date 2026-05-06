Chassis Fairing Structural Analysis Python App
=============================================

File:
  chassis_fairing_analysis_app.py

How to run:
  python chassis_fairing_analysis_app.py

What it does:
  - Select or upload a machine part / chassis fairing part.
  - Automatically fills common load presets based on the part.
  - Version 2 adds CFD-style aerodynamic load calculation from speed, air
    density, drag coefficient, lift coefficient, projected area, wind angle,
    and gust factor.
  - Automatically inserts calculated aerodynamic pressure into the load table
    before structural analysis.
  - Lets you edit component dimensions, material, load value, load type, load zone, boundary condition, and target factor of safety.
  - Generates non-editable Matplotlib graph output for:
      1. Stress distribution along length
      2. Stress-strain material comparison
      3. Load vs deformation
      4. Factor of safety by zone
  - Exports graph PNG image and CSV result table.
  - Exports a PDF report with input table, result summary, formulas, and graphs.

Material database included:
  - ASTM A36 Steel
  - Aluminum 6061-T6
  - CFRP Carbon Fiber
  - Titanium Ti-6Al-4V
  - HSS 700 Steel
  - Polypropylene

Backend formulas included:
  - Normal stress: sigma = F/A
  - Bending stress: sigma = M*c/I
  - Shear stress approximation: tau = 1.5V/A
  - Torsional shear approximation: tau = T*c/J, using a simplified J relation
  - Von Mises stress: sigma_vm = sqrt(sigma^2 + 3*tau^2)
  - Strain: epsilon = sigma/E
  - Simply supported deflection: delta = F*L^3/(48EI)
  - Cantilever deflection: delta = F*L^3/(3EI)
  - Fixed-fixed deflection: delta = F*L^3/(192EI)
  - Factor of safety: FOS = yield strength / max Von Mises stress
  - CFD dynamic pressure: q = 0.5*rho*V^2
  - Aerodynamic drag force: Fd = pressure*projected area
  - Reynolds number estimate: Re = rho*V*L/mu

Important note:
  This is an engineering study and project demonstration tool. It is suitable
  for comparing materials, checking first-pass strength, and generating project
  graphs. For final truck chassis/fairing validation, use full FEA with correct
  geometry, meshing, contacts, welds/bolts, constraints, and validated loads.
