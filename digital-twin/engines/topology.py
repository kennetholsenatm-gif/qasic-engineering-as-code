"""
Topology Analysis Engine
Analyzes qubit connectivity topology and graph theory properties
"""

import networkx as nx
from typing import Dict, Any, List
from . import SimulationEngine

class TopologyEngine(SimulationEngine):
    """Engine for analyzing qubit topology connectivity and properties"""

    def validate_inputs(self, design_data: Dict[str, Any]) -> bool:
        """Validate topology analysis inputs"""
        quantum_design = design_data.get('quantum_design', {})
        return 'topology' in quantum_design and 'qubit_count' in quantum_design

    def run_simulation(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run topology analysis"""
        if self.logger:
            self.logger.info("Running topology analysis")

        quantum_design = design_data['quantum_design']
        topology = quantum_design['topology']
        qubit_count = quantum_design['qubit_count']

        # Create topology graph
        G = self._create_topology_graph(topology, qubit_count)

        # Analyze graph properties
        analysis = self._analyze_graph_properties(G)

        return {
            'topology': topology,
            'qubit_count': qubit_count,
            'graph_properties': analysis,
            'connectivity_matrix': self._get_connectivity_matrix(G),
            'shortest_paths': self._compute_shortest_paths(G)
        }

    def get_required_inputs(self) -> List[str]:
        """Required inputs for topology analysis"""
        return ['quantum_design.topology', 'quantum_design.qubit_count']

    def get_output_schema(self) -> Dict[str, Any]:
        """Output schema for topology analysis"""
        return {
            'topology': 'string',
            'qubit_count': 'integer',
            'graph_properties': {
                'is_connected': 'boolean',
                'diameter': 'integer',
                'average_degree': 'float',
                'clustering_coefficient': 'float'
            },
            'connectivity_matrix': 'array',
            'shortest_paths': 'object'
        }

    def _create_topology_graph(self, topology: str, qubit_count: int) -> nx.Graph:
        """Create NetworkX graph for given topology"""
        G = nx.Graph()

        # Add nodes
        for i in range(qubit_count):
            G.add_node(i)

        # Add edges based on topology
        if topology == 'linear_chain':
            for i in range(qubit_count - 1):
                G.add_edge(i, i + 1)
        elif topology == 'heavy_hex':
            # Simplified heavy hex - would need full implementation
            self._create_heavy_hex_topology(G, qubit_count)
        elif topology == 'grid_2d':
            self._create_grid_topology(G, qubit_count)
        else:
            # Default to linear chain
            for i in range(qubit_count - 1):
                G.add_edge(i, i + 1)

        return G

    def _create_heavy_hex_topology(self, G: nx.Graph, qubit_count: int):
        """Create heavy hex topology (simplified)"""
        # This is a simplified version - real implementation would be more complex
        edges = [(0,1), (1,2), (2,3), (3,4), (4,5), (5,0),  # Outer hexagon
                (0,6), (1,7), (2,8), (3,9), (4,10), (5,11),  # Inner connections
                (6,7), (7,8), (8,9), (9,10), (10,11), (11,6)]  # Inner hexagon

        for edge in edges:
            if edge[0] < qubit_count and edge[1] < qubit_count:
                G.add_edge(edge[0], edge[1])

    def _create_grid_topology(self, G: nx.Graph, qubit_count: int):
        """Create 2D grid topology"""
        import math
        grid_size = int(math.sqrt(qubit_count))

        for i in range(grid_size):
            for j in range(grid_size):
                node = i * grid_size + j
                if node >= qubit_count:
                    continue
                # Connect to right neighbor
                if j < grid_size - 1 and (i * grid_size + j + 1) < qubit_count:
                    G.add_edge(node, i * grid_size + j + 1)
                # Connect to bottom neighbor
                if i < grid_size - 1 and ((i + 1) * grid_size + j) < qubit_count:
                    G.add_edge(node, (i + 1) * grid_size + j)

    def _analyze_graph_properties(self, G: nx.Graph) -> Dict[str, Any]:
        """Analyze graph theory properties"""
        properties = {}

        # Basic connectivity
        properties['is_connected'] = nx.is_connected(G)
        properties['number_of_nodes'] = G.number_of_nodes()
        properties['number_of_edges'] = G.number_of_edges()

        if properties['is_connected']:
            properties['diameter'] = nx.diameter(G)
            properties['radius'] = nx.radius(G)
        else:
            properties['diameter'] = None
            properties['radius'] = None

        # Degree analysis
        degrees = [d for n, d in G.degree()]
        properties['average_degree'] = sum(degrees) / len(degrees) if degrees else 0
        properties['max_degree'] = max(degrees) if degrees else 0
        properties['min_degree'] = min(degrees) if degrees else 0

        # Clustering
        properties['average_clustering'] = nx.average_clustering(G)

        # Centrality measures (for small graphs)
        if G.number_of_nodes() <= 20:
            properties['betweenness_centrality'] = nx.betweenness_centrality(G)
            properties['closeness_centrality'] = nx.closeness_centrality(G)

        return properties

    def _get_connectivity_matrix(self, G: nx.Graph) -> List[List[int]]:
        """Get adjacency matrix as list of lists"""
        return nx.to_numpy_array(G).tolist()

    def _compute_shortest_paths(self, G: nx.Graph) -> Dict[str, Any]:
        """Compute shortest paths between all pairs"""
        if not nx.is_connected(G):
            return {'error': 'Graph is not connected'}

        # For larger graphs, this could be expensive
        if G.number_of_nodes() > 50:
            return {'note': 'Graph too large for full shortest path computation'}

        try:
            lengths = dict(nx.all_pairs_shortest_path_length(G))
            return {
                'average_shortest_path': nx.average_shortest_path_length(G),
                'shortest_path_lengths': lengths
            }
        except:
            return {'error': 'Could not compute shortest paths'}