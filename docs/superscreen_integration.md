# SuperScreen integration (optional)

**Role in the stack:** SuperScreen solves the 2D London equation for thin-film superconductors and computes Meissner screening currents and self/mutual inductance matrices. It bridges quantum kinetics (e.g. scqubits) with macroscopic electrodynamics for metasurface array design. See [Engineering as Code: Distributed Computational Roadmap](Engineering_as_Code_Distributed_Computational_Roadmap.tex) and [Computational Materials Science and Simulation Architectures](Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.tex).

**Install (optional):** `pip install superscreen`  
**Run demo:** `python engineering/superscreen_demo.py` (exits with install message if SuperScreen is not installed).

## Minimal example (if SuperScreen is installed)

```python
import superscreen as sc
from superscreen.geometry import circle

length_units = "um"
layer = sc.Layer("base", london_lambda=0.1, thickness=0.025, z0=0)
ring = sc.Polygon(name="ring", layer="base", points=circle(3))
hole = sc.Polygon(points=circle(1))
film = ring.difference(hole)
device = sc.Device("ring", layers=[layer], films=[film], length_units=length_units)
# Then use device with sc.solve() and extract currents/inductance as needed.
```

For full usage (meshing, solve, inductance extraction), see [SuperScreen documentation](https://superscreen.readthedocs.io/).
