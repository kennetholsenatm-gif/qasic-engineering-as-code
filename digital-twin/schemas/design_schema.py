"""
QASIC Digital Twin Design Schema
JSON schema definitions for design.json files
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

class TopologyType(str, Enum):
    LINEAR_CHAIN = "linear_chain"
    TWO_DIMENSIONAL_GRID = "2d_grid"
    CUSTOM = "custom"

class ProcessCorner(str, Enum):
    TYPICAL = "typ"
    WORST_CASE = "wc"
    BEST_CASE = "bc"

class ControlBackend(str, Enum):
    QICK = "qick"
    ZURICH = "zurich"
    SIMULATOR = "simulator"

class SubstrateType(str, Enum):
    SILICON = "si"
    SILICON_DIOXIDE = "sio2"
    SAPPHIRE = "sapphire"
    CUSTOM = "custom"

class MaterialType(str, Enum):
    COPPER = "copper"
    SUPERCONDUCTOR = "superconductor"
    ALUMINUM = "aluminum"
    SILICON = "si"

class DesignMetadata(BaseModel):
    """Metadata for the design"""
    project_id: str = Field(..., description="Unique project identifier")
    version: str = Field("1.0", description="Design version")
    created_at: str = Field(..., description="ISO 8601 timestamp")
    owner: str = Field(..., description="Owner email or identifier")
    description: Optional[str] = Field(None, description="Optional description")

class QuantumDesign(BaseModel):
    """Quantum circuit and topology specification"""
    topology: TopologyType = Field(..., description="Qubit connectivity topology")
    qubit_count: int = Field(..., ge=1, le=64, description="Number of qubits")
    target_frequency_ghz: float = Field(..., gt=0, description="Target operating frequency in GHz")
    phase_range_degrees: List[float] = Field([0, 360], description="Phase range for metasurface")
    gate_set: List[str] = Field(["H", "X", "Z", "CNOT", "RX"], description="Supported quantum gates")
    circuit_intent: Optional[str] = Field("general_purpose", description="Circuit purpose (e.g., surface_code_distance_3)")

    @validator('phase_range_degrees')
    def validate_phase_range(cls, v):
        if len(v) != 2 or v[0] >= v[1]:
            raise ValueError("phase_range_degrees must be [min, max] with min < max")
        return v

class PackagingDesign(BaseModel):
    """Physical packaging and substrate specification"""
    die_material: MaterialType = Field(..., description="Die substrate material")
    die_size_mm: List[float] = Field(..., min_items=2, max_items=2, description="[width, height] in mm")
    substrate_stack: List[Dict[str, Any]] = Field(..., description="Layer stack specification")
    bond_pad_pitch_um: float = Field(..., gt=0, description="Bond pad pitch in microns")
    shield_material: MaterialType = Field(..., description="Magnetic shield material")
    target_thermal_stage: str = Field("10mK", description="Target cryogenic temperature")

    @validator('die_size_mm')
    def validate_die_size(cls, v):
        if any(x <= 0 for x in v):
            raise ValueError("Die dimensions must be positive")
        return v

class ControlDesign(BaseModel):
    """Control electronics and pulse specification"""
    backend: ControlBackend = Field(..., description="Control hardware backend")
    readout_resonance_ghz: float = Field(..., gt=0, description="Readout resonator frequency")
    control_line_count: int = Field(..., ge=0, description="Number of control lines")
    optimal_control_enabled: bool = Field(False, description="Enable GRAPE/CRAB optimization")
    pulse_library: Optional[str] = Field("standard", description="Pulse library to use")

class SimulationConfig(BaseModel):
    """Simulation configuration and parameters"""
    meep_full_wave: bool = Field(True, description="Run full-wave EM simulation")
    qubit_open_system: bool = Field(True, description="Run open quantum system simulation")
    thermal_fea: bool = Field(True, description="Run thermal finite element analysis")
    yield_samples: int = Field(100, ge=10, le=1000, description="Monte Carlo yield samples")
    process_corners: List[ProcessCorner] = Field([ProcessCorner.TYPICAL], description="Process corners to simulate")
    cache_enabled: bool = Field(True, description="Enable result caching")
    parallel_workers: int = Field(4, ge=1, le=16, description="Number of parallel workers")

class FabConfig(BaseModel):
    """Fabrication and tapeout configuration"""
    foundry: str = Field(..., description="Target foundry name")
    process_pdk: str = Field(..., description="PDK version")
    yield_target_percent: float = Field(85.0, ge=0, le=100, description="Target yield percentage")
    delivery_target_date: Optional[str] = Field(None, description="Target delivery date")

class DesignSpec(BaseModel):
    """Complete design specification"""
    metadata: DesignMetadata
    quantum_design: QuantumDesign
    packaging: PackagingDesign
    control: ControlDesign
    simulation: SimulationConfig
    fab: FabConfig

    class Config:
        use_enum_values = True

# Example design templates
def create_8qubit_linear_template() -> Dict[str, Any]:
    """Create a template for 8-qubit linear chain design"""
    return {
        "metadata": {
            "project_id": "qasic-v1.0-8q-linear-7ghz",
            "version": "1.0",
            "created_at": "2026-03-09T12:00:00Z",
            "owner": "hardware.team@company.com",
            "description": "8-qubit linear chain for quantum error correction"
        },
        "quantum_design": {
            "topology": "linear_chain",
            "qubit_count": 8,
            "target_frequency_ghz": 7.0,
            "phase_range_degrees": [0, 360],
            "gate_set": ["H", "X", "Z", "CNOT", "RX"],
            "circuit_intent": "surface_code_distance_3"
        },
        "packaging": {
            "die_material": "si",
            "die_size_mm": [5.0, 5.0],
            "substrate_stack": [
                {"material": "si", "thickness_um": 500},
                {"material": "sio2", "thickness_um": 200}
            ],
            "bond_pad_pitch_um": 100,
            "shield_material": "superconductor",
            "target_thermal_stage": "10mK"
        },
        "control": {
            "backend": "qick",
            "readout_resonance_ghz": 7.5,
            "control_line_count": 16,
            "optimal_control_enabled": True,
            "pulse_library": "standard"
        },
        "simulation": {
            "meep_full_wave": True,
            "qubit_open_system": True,
            "thermal_fea": True,
            "yield_samples": 100,
            "process_corners": ["typ", "wc", "bc"],
            "cache_enabled": True,
            "parallel_workers": 4
        },
        "fab": {
            "foundry": "internal_fab",
            "process_pdk": "pdk_v1.0",
            "yield_target_percent": 85.0,
            "delivery_target_date": "2026-q3"
        }
    }

def create_16qubit_grid_template() -> Dict[str, Any]:
    """Create a template for 16-qubit 2D grid design"""
    return {
        "metadata": {
            "project_id": "qasic-v1.0-16q-grid-6.5ghz",
            "version": "1.0",
            "created_at": "2026-03-09T12:00:00Z",
            "owner": "hardware.team@company.com",
            "description": "16-qubit 2D grid for advanced quantum algorithms"
        },
        "quantum_design": {
            "topology": "2d_grid",
            "qubit_count": 16,
            "target_frequency_ghz": 6.5,
            "phase_range_degrees": [0, 360],
            "gate_set": ["H", "X", "Z", "CNOT", "RX"],
            "circuit_intent": "quantum_algorithm_accelerator"
        },
        "packaging": {
            "die_material": "si",
            "die_size_mm": [8.0, 8.0],
            "substrate_stack": [
                {"material": "si", "thickness_um": 500},
                {"material": "sio2", "thickness_um": 300}
            ],
            "bond_pad_pitch_um": 100,
            "shield_material": "superconductor",
            "target_thermal_stage": "10mK"
        },
        "control": {
            "backend": "zurich",
            "readout_resonance_ghz": 7.0,
            "control_line_count": 32,
            "optimal_control_enabled": True,
            "pulse_library": "advanced"
        },
        "simulation": {
            "meep_full_wave": True,
            "qubit_open_system": True,
            "thermal_fea": True,
            "yield_samples": 200,
            "process_corners": ["typ", "wc", "bc"],
            "cache_enabled": True,
            "parallel_workers": 6
        },
        "fab": {
            "foundry": "internal_fab",
            "process_pdk": "pdk_v1.0",
            "yield_target_percent": 80.0,
            "delivery_target_date": "2026-q4"
        }
    }

def validate_design_json(design_dict: Dict[str, Any]) -> DesignSpec:
    """Validate a design dictionary against the schema"""
    return DesignSpec(**design_dict)

def save_design_template(template_name: str, design_dict: Dict[str, Any]) -> None:
    """Save a design template to disk"""
    import json
    from pathlib import Path

    templates_dir = Path("digital-twin/templates")
    templates_dir.mkdir(exist_ok=True)

    template_path = templates_dir / f"{template_name}.json"
    with open(template_path, 'w') as f:
        json.dump(design_dict, f, indent=2)

    print(f"Template saved to {template_path}")

if __name__ == "__main__":
    # Create and save templates
    save_design_template("8qubit_linear", create_8qubit_linear_template())
    save_design_template("16qubit_grid", create_16qubit_grid_template())

    # Validate templates
    template_8q = create_8qubit_linear_template()
    validated = validate_design_json(template_8q)
    print(f"✅ 8-qubit template validated: {validated.metadata.project_id}")

    template_16q = create_16qubit_grid_template()
    validated = validate_design_json(template_16q)
    print(f"✅ 16-qubit template validated: {validated.metadata.project_id}")