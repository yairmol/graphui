from typing import Callable, Generic, Tuple, TypeVar
import networkx as nx

V = TypeVar('V')

EdgeCallback = Callable[[V, V], None]


class ResponsiveGraph(nx.Graph, Generic[V]):
    def __init__(self, incoming_graph_data=None, **attr):
        super().__init__(incoming_graph_data=incoming_graph_data, **attr)
        self.edge_remove_callbacks = list()
        self.edge_add_callbacks = list()
    
    def __bool__(self):
        return True
    
    def register_on_edge_remove_callback(self, cb: EdgeCallback):
        self.edge_remove_callbacks.append(cb)
    
    def register_on_edge_add_callback(self, cb: EdgeCallback):
        self.edge_add_callbacks.append(cb)

    def add_edge(self, u_of_edge, v_of_edge, **attr):
        super().add_edge(u_of_edge, v_of_edge, **attr)
        for cb in self.edge_add_callbacks:
            cb(u_of_edge, v_of_edge)
    
    def add_edges_from(self, ebunch_to_add, **attr):
        super().add_edges_from(ebunch_to_add, **attr)
        for cb in self.edge_add_callbacks:
            for u, v in ebunch_to_add:
                cb(u, v)
    
    def remove_edge(self, u, v):
        super().remove_edge(u, v)
        for cb in self.edge_remove_callbacks:
            cb(u, v)
    
    def remove_edges_from(self, ebunch):
        super().remove_edges_from(ebunch)
        for cb in self.edge_remove_callbacks:
            for u, v in ebunch:
                cb(u, v)