"""
QASIC Digital Twin Simulation Engines
Specialized physics simulation engines for full-stack quantum ASIC validation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path

class SimulationEngine(ABC):
    """Abstract base class for all simulation engines"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = None  # Will be set by orchestrator

    @abstractmethod
    def validate_inputs(self, design_data: Dict[str, Any]) -> bool:
        """Validate that design data contains required inputs for this engine"""
        pass

    @abstractmethod
    def run_simulation(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the simulation and return results"""
        pass

    @abstractmethod
    def get_required_inputs(self) -> list:
        """Return list of required input parameters"""
        pass

    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        """Return schema of output results"""
        pass

    def set_logger(self, logger):
        """Set logger for this engine"""
        self.logger = logger

# Import engine implementations
from .topology import TopologyEngine
from .gnn import GNNEngine
from .meep import MeepEngine
from .qubit import QubitEngine
from .thermal import ThermalEngine
from .fea import FEAEngine
from .yield_mc import YieldMCEngine
from .routing import RoutingEngine
from .drc import DRCLEngine

__all__ = [
    'SimulationEngine',
    'TopologyEngine',
    'GNNEngine',
    'MeepEngine',
    'QubitEngine',
    'ThermalEngine',
    'FEAEngine',
    'YieldMCEngine',
    'RoutingEngine',
    'DRCLEngine'
]