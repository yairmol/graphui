from enum import Enum, auto
import sys
from typing import Tuple
from PyQt5 import QtGui, QtWidgets  # , uic
from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QPushButton, QVBoxLayout, QWidget
from time import sleep
import networkx as nx
import numpy as np
from shapely.geometry import LineString
from itertools import combinations
from shapely.geometry.multipoint import MultiPoint

from shapely.geometry.point import Point
# from fa2l import force_atlas2_layout


LINE = 0

class Mode(Enum):
    MOVE = auto()
    DELETE = auto()
    PAINT_VERTICES = auto()
    PAINT_EDGES = auto()
    SELECT = auto()
    DRAG = auto()


def normalise(p: float, r1: Tuple[float, float], r2: Tuple[float, float]):
    a, b = r1
    c, d = r2
    return c + ((p - a) * ((d - c) / (b - a)))


def grid_graph_layout(G: nx.Graph, w: int, h: int):    
    n = len(G.nodes)
    rows = int(n ** 0.5)
    node_to_loc_map = dict()
    x, y = 20, 20
    boundary = QRect(20, 20, w, h)
    spacing = boundary.width() // (n // rows) - 10
    print(boundary.right())
    print(spacing)
    for u in G.nodes:
        node_to_loc_map[u] = (x, y)
        print((x, y))
        if x + spacing >= boundary.right():
            x, y = 20, y + spacing
        else:
            x += spacing
    return node_to_loc_map


# class GraphView(QWidget):
#     def __init__(self, w: int, h: int):
#         self.label = QtWidgets.QLabel()
#         self.canvas = QtGui.QPixmap(w, h)
#         self.label.setPixmap(self.canvas)
#         self.G: nx.Graph = nx.Graph()
        
#         self.r = 5
#         self.painter = None
#         self.eraser = None

#         self.vertex_mapping = dict()
#         self.moving_vertex = None
#         self.mode: Mode = Mode.MOVE
#         self.last_point = None
#         self.selected_points = list()
#         self.selected_vertices = set()
#         self.get_non_edges = None


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._main = QWidget()
        self.grid = QGridLayout(self._main)
        self.label = QtWidgets.QLabel()
        self.canvas = QtGui.QPixmap(1200, 800)
        self.label.setPixmap(self.canvas)
        self.grid.addWidget(self.label, 0, 0)
        self.setCentralWidget(self._main)
        
        # self.setCentralWidget(self.label)
        self.init_buttons()

        self.G: nx.Graph = nx.Graph()
        
        self.r = 5
        self.painter = None
        self.eraser = None

        self.vertex_mapping = dict()
        self.moving_vertex = None
        self.mode: Mode = Mode.MOVE
        self.last_point = None
        self.selected_points = list()
        self.selected_vertices = set()
        self.get_non_edges = None
        # print("layout", )
    
    def init_buttons(self):
        buttons_widget = QWidget()
        self.buttons = QVBoxLayout(buttons_widget)
        self.grid.addWidget(buttons_widget, 0, 1)
        button = QPushButton('Delete', self)
        self.buttons.addWidget(button)
        button2 = QPushButton('Move', self)
        self.buttons.addWidget(button2)
        button3 = QPushButton('Paint Vertices', self)
        self.buttons.addWidget(button3)
        button4 = QPushButton('Paint Edges', self)
        self.buttons.addWidget(button4)
        button5 = QPushButton('Select Vertices', self)
        self.buttons.addWidget(button5)
        # button.setToolTip('This is an example button')
        # button.move(100,70)
        button.clicked.connect(self.on_delete_click)
        button2.clicked.connect(self.on_move_click)
        button3.clicked.connect(self.on_paintv_click)
        button4.clicked.connect(self.on_painte_click)
        button5.clicked.connect(lambda: self.set_mode(Mode.SELECT))
    
    def init_painter(self, color: str = 'white', fill=True):
        painter = QtGui.QPainter(self.label.pixmap())
        pen = QtGui.QPen()
        pen.setColor(QtGui.QColor(color))
        painter.setPen(pen)
        if fill:
            brush = QtGui.QBrush(QtGui.QColor(color), Qt.SolidPattern)
            painter.setBrush(brush)
        return painter
    
    def init_eraser(self):
        return self.init_painter('black')
    
    def draw_vertex(self, x, y):
        self.painter.drawEllipse(QPoint(x, y), self.r, self.r)
    
    def draw_graph(self, G: nx.Graph):
        node_to_loc_map = grid_graph_layout(G, 700, 600)
        print(type(G), G.nodes())
        for u in G.nodes():
            x, y = node_to_loc_map[u]
            self.draw_vertex(x, y)
        for u, v in G.edges():
            loc_u, loc_v = node_to_loc_map[u], node_to_loc_map[v]
            self.painter.drawLine(*loc_u, *loc_v)
            G[u][v][LINE] = LineString([loc_u, loc_v])
        self.painter.end()
        return node_to_loc_map

    def in_vertex(self, x, y):
        try: 
            return next(u for u, (ux, uy) in self.vertex_mapping.items() if np.linalg.norm([ux - x, uy - y]) <= self.r + 5)
        except StopIteration:
            return None
    
    def draw_selected_vertex(self, u):
        whitepen = self.painter.pen()
        whitebrush = self.painter.brush()
        bluepen = QtGui.QPen()
        bluebrush = QtGui.QBrush(QtGui.QColor(0x3895d3), Qt.SolidPattern)
        bluepen.setColor(QtGui.QColor(0x3895d3))
        self.painter.setPen(bluepen)
        self.painter.setBrush(bluebrush)
        orig_r = self.r
        self.r = 7
        self.draw_vertex(*self.vertex_mapping[u])
        self.r = orig_r
        self.painter.setPen(whitepen)
        self.painter.setBrush(whitebrush)
        self.draw_vertex(*self.vertex_mapping[u])
    
    def unmark_vertices(self, vertices):
        self.eraser = self.init_eraser()
        self.r = 7
        for u in vertices:
            self.delete_vertex(*self.vertex_mapping[u])
        self.eraser.end()
        self.r = 5
        self.painter = self.init_painter()
        for u in self.selected_vertices:
            self.draw_vertex(*self.vertex_mapping[u])
        self.painter.end()
        self.update()
    
    def handle_mouse_press_paint_vertices(self, p):
        u = max(self.G.nodes or [0]) + 1
        self.G.add_node(u)
        self.vertex_mapping[u] = p
        self.painter = self.init_painter()
        self.draw_vertex(*p)
        self.painter.end()
        self.update()
    
    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        p = self.label.mapFromParent(a0.pos())
        p = (p.x(), p.y())
        self.last_point = p
        match self.mode:
            case Mode.PAINT_VERTICES:
                self.handle_mouse_press_paint_vertices(p)
            case Mode.MOVE:
                self.moving_vertex = self.in_vertex(*p)
            case Mode.SELECT:
                self.unmark_vertices(self.selected_vertices)
                self.painter = self.init_painter()
                self.selected_points = [a0.pos()]
                self.selected_vertices = set()
    
    def finish_select(self):
        self.painter.end()
        self.update()
    
    def delete_selection_dots(self):
        self.eraser = self.init_eraser()
        for p in self.selected_points:
            self.eraser.drawPoint(p)
        self.eraser.end()
        self.update()
    
    def mark_selected_vertices(self):
        poly = MultiPoint([(p.x(), p.y()) for p in self.selected_points]).convex_hull
        self.selected_points.clear()
        for u, loc in self.vertex_mapping.items():
            if poly.intersects(Point(*loc)):
                self.selected_vertices.add(u)
        # print(self.selected_vertices)
        self.painter = self.init_painter()
        for u in self.selected_vertices:
            self.draw_selected_vertex(u)
        self.painter.end()
        self.update()

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        match self.mode:
            case Mode.MOVE:
                self.moving_vertex = None
            case Mode.SELECT:
                self.finish_select()
                self.delete_selection_dots()
                self.mark_selected_vertices()
    
    def delete_vertex(self, x, y):
        self.eraser.drawEllipse(QPoint(x, y), self.r, self.r)
    
    def delete_edge(self, u, v):
        self.eraser.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
    
    def delete_vertex_edges(self, u):
        for v in self.G[u]:
            self.eraser.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
    
    def draw_vertex_edges(self, u):
        for v in self.G[u]:
            self.painter.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
    
    def relocate_vertex(self, u, x, y):
        self.eraser = self.init_eraser()
        self.delete_vertex(*self.vertex_mapping[u])
        self.delete_vertex_edges(u)
        self.eraser.end()
        self.painter = self.init_painter()
        self.draw_vertex(x, y)
        self.vertex_mapping[u] = (x, y)
        self.draw_vertex_edges(u)
        self.painter.end()
        self.update()
    
    def delete_intersecting_edges(self, cur_point):
        edges = self.intersecting_edges(LineString([self.last_point, cur_point]))
        self.G.remove_edges_from(edges)
        self.eraser = self.init_eraser()
        for u, v in edges:
            self.delete_edge(u, v)
        self.eraser.end()
        self.update()
        self.last_point = cur_point
    
    def intersecting_non_edges(self, line: LineString, edges):
        intersecting_edges = set()
        for u, v in edges:
            if line.intersects(LineString([self.vertex_mapping[u], self.vertex_mapping[v]])):
                intersecting_edges.add((u, v))
        return intersecting_edges
    
    def add_intersecting_edges(self, cur_point):
        edges = self.intersecting_non_edges(LineString([self.last_point, cur_point]), self.get_non_edges())
        for u, v in edges:
            self.G.add_edge(u, v)
            self.G[u][v][LINE] = LineString([self.vertex_mapping[u], self.vertex_mapping[v]])
        self.painter = self.init_painter()
        for u, v in edges:
            self.draw_edge(u, v)
        self.painter.end()
        self.update()
        self.last_point = cur_point
    
    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        p = self.label.mapFromParent(a0.pos())
        match self.mode:
            case Mode.DELETE:
                self.delete_intersecting_edges((p.x(), p.y()))
            case Mode.MOVE:
                if self.moving_vertex:
                    self.relocate_vertex(self.moving_vertex, p.x(), p.y())
            case Mode.PAINT_EDGES:
                self.add_intersecting_edges((p.x(), p.y()))
            case Mode.SELECT:
                self.selected_points.append(p)
                self.painter.drawPoint(p)
                self.update()
            # case Mode.PAINT_VERTICES:
            #     pass

    def intersecting_edges(self, line: LineString):
        intersecting_edges = set()
        for u, v, e_line in self.G.edges(data=True):
            if line.intersects(e_line[0]):
                intersecting_edges.add((u, v))
        return intersecting_edges
    
    def set_mode(self, mode):
        if self.mode == Mode.SELECT and self.selected_vertices:
            self.unmark_vertices(self.selected_vertices)
            if mode == Mode.PAINT_EDGES:
                self.get_non_edges = lambda: filter(
                    lambda e: set(e).issubset(self.selected_vertices) and not self.G.has_edge(*e),
                    combinations(self.G.nodes, 2)
                )
                self.draw_missing_edges(self.get_non_edges())
        elif mode == Mode.PAINT_EDGES:
            self.get_non_edges = lambda: filter(
                lambda e: not self.G.has_edge(*e),
                combinations(self.G.nodes, 2)
            )
            self.draw_missing_edges(self.get_non_edges())
        elif self.mode == Mode.PAINT_EDGES and mode != Mode.PAINT_EDGES:
            self.delete_missing_edges()
        self.mode = mode
    
    def on_delete_click(self):
        self.set_mode(Mode.DELETE)
    
    def on_move_click(self):
        self.set_mode(Mode.MOVE)
    
    def on_paintv_click(self):
        self.set_mode(Mode.PAINT_VERTICES)
    
    def on_painte_click(self):
        self.set_mode(Mode.PAINT_EDGES)
    
    def draw_edge(self, u, v):
        """assume painter is initiated"""
        self.painter.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
    
    def draw_missing_edges(self, edges):
        self.painter = self.init_painter('gray')
        for u, v in edges:
            self.draw_edge(u, v)
        self.painter.end()
        self.update()
    
    def delete_missing_edges(self):
        self.eraser = self.init_eraser()
        for u, v in combinations(self.G.nodes, 2):
            if not self.G.has_edge(u, v):
                self.delete_edge(u, v)
        self.eraser.end()
        self.update()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()



# def force_atals_graph_layout(G: nx.Graph, w: int, h: int):
#     positions = force_atlas2_layout(G, iterations=1000)
#     r1 = (-10, 10)
#     return {
#         u: (int(normalise(x, r1, (20, w - 20))), int(normalise(y, r1, (20, h - 20))))
#         for u, (x, y) in positions.items()
#     }