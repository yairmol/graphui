from time import sleep

from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtCore import Qt
from mainwindow.graph_view import GraphView

class ColorVertexCallback:
    def __init__(self, graph_view: GraphView, color: QColor = None) -> None:
        self.last_u = None
        self.graph_view = graph_view
        if not color:
            self.pen = self.graph_view.blue_pen
            self.brush = self.graph_view.blue_brush
        else:
            self.pen = QPen(color)
            self.brush = QBrush(color, Qt.SolidPattern)
        
    
    def __call__(self, u) -> None:
        if self.last_u:
            print(f"coloring {self.last_u} in white")
            self.graph_view.draw_vertex(self.last_u, self.graph_view.white_pen, self.graph_view.white_brush)
        if u:
            print(f"coloring {u} in blue")
            self.graph_view.draw_vertex(u, self.pen, self.brush)
        self.last_u = u
        self.graph_view.repaint()


class WaitCallback:
    def __init__(self, seconds: float = 0.0) -> None:
        self.seconds = seconds
    
    def __call__(self, *_, **__):
        sleep(self.seconds)
    

class ColorEdgeCallback:
    def __init__(self, graph_view: GraphView, color: QColor = None) -> None:
        self.last_edge = None
        self.graph_view = graph_view
        if not color:
            self.pen = self.graph_view.blue_pen
            self.brush = self.graph_view.blue_brush
        else:
            self.pen = QPen(color)
            self.brush = QBrush(color, Qt.SolidPattern)
    
    def __call__(self, e) -> None:
        if self.last_edge:
            print(f"coloring {self.last_edge} in white")
            u, v = self.last_edge
            self.graph_view.draw_edge(u, v, self.graph_view.white_pen, self.graph_view.white_brush)
        if e:
            print(f"coloring {e} in blue")
            u, v = e
            self.graph_view.draw_edge(u, v, self.pen, self.brush)
        self.last_e = e
        self.graph_view.repaint()


class BFSCallbacks:
    def __init__(self, graph_view: GraphView) -> None:
        self.graph_view = graph_view
        self.u = None
        self.v = None

    def getitem_callback(self, u):
        print("in getitem callback with", u)
        if self.u:
            self.graph_view.draw_vertex(self.u, self.graph_view.white_pen, self.graph_view.white_brush)
        self.u = u
        self.graph_view.draw_vertex(u, self.graph_view.blue_pen, self.graph_view.blue_brush)
        self.graph_view.repaint()

    def iter_next_callback(self, v):
        print("in iter next callback with", v)
        if self.u and self.v:
            self.graph_view.draw_edge(self.u, self.v)
        if self.v:
            self.graph_view.draw_vertex(v, self.graph_view.white_pen, self.graph_view.white_brush)
        self.v = v
        if self.u and self.v:
            self.graph_view.draw_edge(self.u, self.v, self.graph_view.blue_pen, self.graph_view.blue_brush)
        self.graph_view.draw_vertex(v, self.graph_view.blue_pen, self.graph_view.blue_brush)
        self.graph_view.repaint()
