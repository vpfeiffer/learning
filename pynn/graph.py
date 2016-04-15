import copy


def _validate_edge(edge):
    if not isinstance(edge, tuple) or len(edge) != 2:
        raise TypeError('edge must be a (from_node, to_node) tuple')

        
def _reverse_edge(edge):
    return (edge[1], edge[0])
        
        
class Graph(object):
    def __init__(self, adjacency_dict):
        # Maps node to connected nodes
        if not isinstance(adjacency_dict, dict):
            raise TypeError('adjacency_dict must be a dict mapping node -> list of connected nodes')
        self.adjacency = copy.deepcopy(adjacency_dict)

        self.nodes = self._extract_nodes()
        self.edges = self._extract_edges()
        
    def _extract_nodes(self):
        """Return the set of all ndoes in this graph."""
        nodes = set()
        for from_node, connected_nodes in self.adjacency.iteritems():
            nodes.add(from_node)
            for node in connected_nodes:
                nodes.add(node)
        return nodes
        
    def _extract_edges(self):
        """Return the set of all edges in this graph."""
        edges = set()
        for from_node, connected_nodes in self.adjacency.iteritems():
            for node in connected_nodes:
                edges.add((from_node, node))
        return edges
        
    def add_edge(self, edge):
        """Add edge to graph.
        
        Args:
            edge: (from_node, to_node) tuple.
        """
        _validate_edge(edge)
        if edge in self.edges:
            raise ValueError('edge already in graph.')
        
        # Add to adjacency
        try:
            connected_nodes = self.adjacency[edge[0]]
            connected_nodes.append(edge[1])
        # from_node in edge is not yet a from_node in graph
        except KeyError:
            self.adjacency[edge[0]] = [edge[1]]
            
        # Add to set of edges, and set of nodes
        self.nodes.add(edge[0])
        self.nodes.add(edge[1])
        self.edges.add(edge)
        
    def remove_edge(self, edge):
        """Remove edge to graph.
        
        Args:
            edge: (from_node, to_node) tuple.
        """
        _validate_edge(edge)
        if not edge in self.edges:
            raise ValueError('edge not in graph.')
            
        # Remove from adjacency
        connected_nodes = self.adjacency[edge[0]]
        connected_nodes.remove(edge[1])
            
        # Remove from set of edges
        # Nodes remain in set of nodes, even if they have no edges left
        self.edges.remove(edge)

def find_path(graph, start, end, path=[]):
    """Search for a path from start to end.
    
    From: https://www.python.org/doc/essays/graphs/
    
    Returns:
        list / None; If path exists, return list of nodes in path order, otherwise return None.
    """
    path = path + [start]
    if start == end:
        return path
    if not graph.has_key(start):
        return None
    for node in graph[start]:
        if node not in path:
            newpath = _find_path(graph, node, end, path)
            if newpath: return newpath
    return None