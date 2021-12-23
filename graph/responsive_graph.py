from typing import Callable, Generic, Optional, Tuple, TypeVar
import networkx as nx
from graph.hook import Hookable, hookable
from graph.responsive_iterators import ResponsiveIterator

from graph.views import ResponsiveAdjacencyView, ResponsiveEdgeView, ResponsiveNodeView

V = TypeVar('V')

EdgeCallback = Callable[[Tuple[V, V]], None]
NextVertexCallback = Callable[[Optional[V]], None]


@hookable()
class ResponsiveGraph(nx.Graph, Hookable, Generic[V]):
    def __init__(self, incoming_graph_data=None, **attr):
        super().__init__(incoming_graph_data=incoming_graph_data, **attr)
        self._vertex_iter_callbacks = []
        self._edge_iter_callbacks = []
        self.node_view = ResponsiveNodeView(self, self._vertex_iter_callbacks)
        self.adj_view = ResponsiveAdjacencyView(self._adj, self._vertex_iter_callbacks)

    def __iter__(self):
        return ResponsiveIterator(super().__iter__(), self._vertex_iter_callbacks)
    
    @property
    def nodes(self):
        return self.node_view
    
    @property
    def edges(self):
        return super().edges
        # return ResponsiveEdgeView(self, self._edge_iter_callbacks)
    
    @property
    def adj(self):
        return self.adj_view
    
    def regsiter_node_iter_callback(self, cb):
        self._vertex_iter_callbacks.append(cb)

    def regsiter_edges_iter_callback(self, cb):
        self._edge_iter_callbacks.append(cb)
    
    def clear_vertex_iterator_callbacks(self):
        self._vertex_iter_callbacks.clear()
    
    def clear_edge_iter_callbacks(self):
        self._edge_iter_callbacks.clear()


def main():
    G = ResponsiveGraph()
    G.register_callback(G.add_node, lambda self, n: print("adding node", n))
    G.add_node(1)
    G.add_node(2)
    G.add_edge(1, 2)
    G.adj.register_callback("__getitem__", lambda self, u: print("in cb", u))
    G.adj[1]


if __name__ == "__main__":
    main()