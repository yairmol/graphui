import networkx as nx

from typing import Any, Iterable, Mapping, Tuple
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QPaintDevice
from mainwindow.painters.painter import CustomPainter

from commandbar.utils import objreg
from mainwindow.painters import tools


class GraphPainter(CustomPainter):

    def __init__(self, pd: QPaintDevice):
        super().__init__(pd)
        self.graph: nx.Graph = objreg.get('graph', scope='canvas', default=None)
        self.locations: Mapping[Any, QPoint] = objreg.get('vertex_mapping', scope='canvas', default=None)
        self.r = 5  # TODO: think about where to locate this 
        if not self.graph or not self.locations:
            raise ValueError("missing graph in registry at time of graph painter instantiation")
        
    def draw_vertex(self, u, pen=None, brush=None, r=None):
        r = r or self.r
        self.set(pen or tools.WHITE_PEN, brush or tools.WHITE_BRUSH)
        self.drawEllipse(self.locations[u], r, r)
    
    def draw_edge(self, u, v, pen=None, brush=None):
        self.set(pen or tools.WHITE_PEN, brush or tools.WHITE_BRUSH)
        self.drawLine(self.locations[u], self.locations[v])
    
    def delete_vertex(self, u, r=None):
        r = r or self.r
        self.set(tools.BLACK_PEN, tools.BLACK_BRUSH)
        self.drawEllipse(self.locations[u], r, r)
    
    def delete_edge(self, u, v):
        self.set(tools.BLACK_PEN, tools.BLACK_BRUSH)
        self.drawLine(self.locations[u], self.locations[v])
    
    def draw_vertices(self, vertices: Iterable, pen=None, brush=None, r=None):
        r = r or self.r
        self.set(pen or tools.WHITE_PEN, brush or tools.WHITE_BRUSH1)
        for u in vertices:
            self.drawEllipse(self.locations[u], r, r)
    
    def delete_vertices(self, vertices, r=None):
        r = r or self.r
        self.draw_vertices(vertices, tools.BLACK_PEN, tools.BLACK_BRUSH, r)
    
    def delete_edges(self, edges: Iterable):
        self.draw_edges(edges, tools.BLACK_PEN, tools.BLACK_BRUSH)
    
    def draw_edges(self, edges: Iterable[Tuple[Any, Any]], pen=None, brush=None):
        self.set(pen or tools.WHITE_PEN, brush or tools.WHITE_BRUSH)
        for u, v in edges:
            self.drawLine(self.locations[u], self.locations[v])
    
    def draw_selected_vertex(self, u):
        self.draw_vertex(u, self.blue_pen, self.blue_brush, self.r + 2)
        self.draw_vertex(u)
    
    def draw_selected_vertices(self, vertices):
        self.draw_vertices(vertices, self.blue_pen, self.blue_brush, self.r + 2)
        self.draw_vertices(vertices)
    
    def delete_selected_vertices(self, vertices):
        self.delete_vertices(vertices, self.r + 2)
        self.draw_vertices(vertices)
    
    def draw_graph(self):
        self.draw_vertices(self.graph.nodes)
        self.draw_edges(self.graph.edges)
    
    def delete_graph(self):
        self.delete_vertices(self.graph.nodes)
        self.delete_edges(self.graph.edges)
    
    def draw_vertex_edges(self, u):
        self.draw_edges((u, v) for v in self.graph[u])
    
    def delete_vertex_edges(self, u):
        self.delete_edges((u, v) for v in self.graph[u])