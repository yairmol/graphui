import numpy as np

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QPen, QBrush, QColor
import networkx as nx

from graph_view import Mode, MyPainter

class GraphView2(QtWidgets.QLabel):
    def __init__(self, w: int, h: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.canvas = QtGui.QPixmap(w, h)
        self.setPixmap(self.canvas)
        self.G: nx.Graph = nx.Graph()
        
        self.r = 5

        self.painter = MyPainter(self.pixmap())

        self.white_pen = QPen(QColor('white'))
        self.black_pen = QPen(QColor('black'))
        self.white_brush = QBrush(QColor('white'), Qt.SolidPattern)
        self.black_brush = QBrush(QColor('black'), Qt.SolidPattern)
        self.blue_pen = QPen(QColor(0x3895d3))
        self.blue_brush = QBrush(QColor(0x3895d3), Qt.SolidPattern)
        self.gray_pen = QPen(QColor('gray'))

        self.vertex_mapping = dict()
        self.mode = Mode.PAINT_VERTICES
        self.clear_canvas()
    
    def draw_vertex(self, u):
        with self.painter(self.white_pen, self.white_brush):
            self.painter.drawEllipse(QPoint(*self.vertex_mapping[u]), self.r, self.r)
        self.update()
    
    def delete_vertex(self, u):
        with self.painter(self.black_pen, self.black_brush):
            self.painter.drawEllipse(QPoint(*self.vertex_mapping[u]), self.r, self.r)
        self.update()
    
    def in_vertex(self, x, y):
        try:
            return next(
                u for u, (ux, uy) in self.vertex_mapping.items() 
                if np.linalg.norm([ux - x, uy - y]) <= self.r + 5
            )
        except StopIteration:
            return None
    
    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if self.mode == Mode.PAINT_VERTICES:
            u = max(self.G.nodes or [-1]) + 1
            self.G.add_node(u)
            self.vertex_mapping[u] = (e.x(), e.y())
            self.draw_vertex(u)
            self.update()
        elif self.mode == Mode.DELETE:
            u = self.in_vertex(e.x(), e.y())
            if u is not None:
                self.delete_vertex(u)
                self.vertex_mapping.pop(u)
                self.G.remove_node(u)
    
    def clear_canvas(self):
        with self.painter(self.black_pen, self.black_brush):
            self.painter.drawRect(0, 0, self.pixmap().width(), self.pixmap().height())
        self.update()
    
    def set_mode(self, mode):
        if mode in [Mode.PAINT_VERTICES, Mode.DELETE]:
            self.mode = mode