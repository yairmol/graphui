from abc import abstractmethod
from enum import Enum, auto
import sys
from typing import Any, Dict, Optional, Tuple
from PyQt5 import QtGui, QtWidgets  # , uic
from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtWidgets import QBoxLayout, QGridLayout, QHBoxLayout, QPushButton, QVBoxLayout, QWidget
from time import sleep
import networkx as nx
import numpy as np
from shapely.geometry import LineString
from itertools import combinations
from shapely.geometry.multipoint import MultiPoint

from shapely.geometry.point import Point
# from fa2l import force_atlas2_layout


def rescale_mapping(
    mapping: Dict[Any, Tuple[int, int]],
    old_rx: Tuple[int, int],
    old_ry: Tuple[int, int],
    new_rx: Tuple[int, int],
    new_ry: Tuple[int, int]
):
    return {
        u: (int(normalise(x, old_rx, new_rx)), int(normalise(y, old_ry, new_ry)))
        for u, (x, y) in mapping.items()
    }


def rescale_origin_mapping(mapping: Dict[Any, Tuple[int, int]], old_w, old_h, w, h):
    return rescale_mapping(mapping, (0, old_w), (0, old_h), (0, w), (0, h))

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


class GraphViewState:
    class_name: str

    def __init__(self, graph_view: 'GraphView') -> None:
        self.graph_view = graph_view

    def on_mouse_move(self, e: QtGui.QMouseEvent):
        raise NotImplementedError()

    def on_mouse_press(self, e: QtGui.QMouseEvent):
        raise NotImplementedError()

    def on_mouse_release(self, e: QtGui.QMouseEvent):
        raise NotImplementedError()

    def transition_to(self, other: 'GraphViewState'):
        return getattr(other, f"tranition_from_{other.class_name}", lambda _: other)(self)


class PaintVerticesState(GraphViewState):
    class_name = "paint_vertices"
    
    def  __init__(self, graph_view: 'GraphView') -> None:
        super().__init__(graph_view)



class PaintEdgesState(GraphViewState):
    class_name = "paint_edges"

    def __init__(self, graph_view: 'GraphView') -> None:
        super().__init__(graph_view)
    


class MoveVerticesState(GraphViewState):
    class_name = "move_vertices"
    
    def __init__(self, graph_view: 'GraphView') -> None:
        super().__init__(graph_view)
        self.moving_vertex = None
    
    def in_vertex(self, x, y):
        try:
            return next(u for u, (ux, uy) in self.vertex_mapping.items() if np.linalg.norm([ux - x, uy - y]) <= self.r + 5)
        except StopIteration:
            return None
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.moving_vertex = self.in_vertex(e.x(), e.y())
        


class DeleteEdgesState(GraphViewState):
    class_name = "delete_edges"
     
    def __init__(self, graph_view: 'GraphView') -> None:
        super().__init__(graph_view)


class GraphView(QtWidgets.QLabel):
    def __init__(
        self,
        w: int, h: int,
        G: Optional[nx.Graph] = None,
        vertex_mapping: Optional[Dict[Any, Tuple[int, int]]] = None,
        mode: Optional[Mode] = None,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.canvas = QtGui.QPixmap(w, h)
        self.setPixmap(self.canvas)
        self.G: nx.Graph = G or nx.Graph()
        
        self.r = 5
        self.painter = None
        self.eraser = None

        self.vertex_mapping = vertex_mapping or dict()
        self.moving_vertex = None
        self.mode: Mode = mode or Mode.MOVE
        self.state = MoveVerticesState(self)
        self.last_point = None
        self.selected_points = list()
        self.selected_vertices = set()
        self.get_non_edges = None

        self.clear_canvas()
        # self.painter = self.init_painter()
        # self.draw_graph()
        # self.painter.end()
        # self.update()
    
    def init_painter(self, color: str = 'white', fill=True):
        painter = QtGui.QPainter(self.pixmap())
        pen = QtGui.QPen()
        pen.setColor(QtGui.QColor(color))
        painter.setPen(pen)
        if fill:
            brush = QtGui.QBrush(QtGui.QColor(color), Qt.SolidPattern)
            painter.setBrush(brush)
        return painter
    
    def init_eraser(self):
        return self.init_painter('black')
    
    def clear_canvas(self):
        self.eraser = self.init_eraser()
        self.eraser.drawRect(0, 0, self.canvas.width(), self.canvas.height())
        self.eraser.end()
        self.update()
    
    def draw_vertex(self, u):
        self.painter.drawEllipse(QPoint(*self.vertex_mapping[u]), self.r, self.r)
    
    def draw_edge(self, u, v):
        self.painter.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
    
    def delete_vertex(self, u):
        self.eraser.drawEllipse(QPoint(*self.vertex_mapping[u]), self.r, self.r)
    
    def delete_edge(self, u, v):
        self.eraser.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
    
    def draw_vertex_edges(self, u):
        for v in self.G[u]:
            self.painter.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
    
    def delete_vertex_edges(self, u):
        for v in self.G[u]:
            self.eraser.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
    
    def draw_selected_vertex(self, u):
        whitepen = self.painter.pen()
        whitebrush = self.painter.brush()
        bluepen = QtGui.QPen(QtGui.QColor(0x3895d3))
        bluebrush = QtGui.QBrush(QtGui.QColor(0x3895d3), Qt.SolidPattern)
        self.painter.setPen(bluepen)
        self.painter.setBrush(bluebrush)
        orig_r = self.r
        self.r = 7
        self.draw_vertex(u)
        self.r = orig_r
        self.painter.setPen(whitepen)
        self.painter.setBrush(whitebrush)
        self.draw_vertex(u)
    
    def draw_graph(self):
        for u in self.G.nodes:
            self.draw_vertex(u)
        for u, v in self.G.edges:
            loc_u, loc_v = self.vertex_mapping[u], self.vertex_mapping[v]
            self.painter.drawLine(*loc_u, *loc_v)
    
    def unmark_vertices(self, vertices):
        self.eraser = self.init_eraser()
        self.r = 7
        for u in vertices:
            self.delete_vertex(u)
        self.eraser.end()
        self.r = 5
        self.painter = self.init_painter()
        for u in self.selected_vertices:
            self.draw_vertex(u)
        self.painter.end()
        self.update()
    
    def handle_mouse_press_paint_vertices(self, p):
        u = max(self.G.nodes or [0]) + 1
        self.G.add_node(u)
        self.vertex_mapping[u] = p
        self.painter = self.init_painter()
        self.draw_vertex(u)
        self.painter.end()
        self.update()
    
    def in_vertex(self, x, y):
        try:
            return next(u for u, (ux, uy) in self.vertex_mapping.items() if np.linalg.norm([ux - x, uy - y]) <= self.r + 5)
        except StopIteration:
            return None

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        # self.state.on_mouse_press(a0)
        p = a0.pos()
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
    
    def relocate_vertex(self, u, x, y):
        self.eraser = self.init_eraser()
        self.delete_vertex(u)
        self.delete_vertex_edges(u)
        self.eraser.end()
        self.painter = self.init_painter()
        self.vertex_mapping[u] = (x, y)
        self.draw_vertex(u)
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
        p = a0.pos()
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
    


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._main = QWidget()
        self.grid = QGridLayout(self._main)
        self.graph_views_dim = 1200, 800
        self.graph_views = [GraphView(*self.graph_views_dim)]  # , GraphView(*graph_views_dim)]
        gvwidget = QWidget()
        self.graph_views_widget = QGridLayout(gvwidget)
        self.num_rows, self.num_cols = 1, 1
        self.graph_views_widget.addWidget(self.graph_views[0])
        self.grid.addWidget(gvwidget, 0, 0)
        self.setCentralWidget(self._main)
        # self.setCentralWidget(self.label)
        self.init_buttons()
        # print("layout", )
    
    def init_buttons(self):
        buttons_widget = QWidget()
        self.buttons = QVBoxLayout(buttons_widget)
        self.grid.addWidget(buttons_widget, 0, 1)
        delete_edges_button = QPushButton('Delete', self)
        self.buttons.addWidget(delete_edges_button)
        move_vertices_button = QPushButton('Move', self)
        self.buttons.addWidget(move_vertices_button)
        paint_vertices_button = QPushButton('Paint Vertices', self)
        self.buttons.addWidget(paint_vertices_button)
        paint_edges_button = QPushButton('Paint Edges', self)
        self.buttons.addWidget(paint_edges_button)
        select_vertices_buttom = QPushButton('Select Vertices', self)
        self.buttons.addWidget(select_vertices_buttom)
        add_graph_view_button = QPushButton('Add Graph View', self)
        self.buttons.addWidget(add_graph_view_button)
        # button.setToolTip('This is an example button')
        # button.move(100,70)
        delete_edges_button.clicked.connect(lambda: self.set_mode(Mode.DELETE))
        move_vertices_button.clicked.connect(lambda: self.set_mode(Mode.MOVE))
        paint_vertices_button.clicked.connect(lambda: self.set_mode(Mode.PAINT_VERTICES))
        paint_edges_button.clicked.connect(lambda: self.set_mode(Mode.PAINT_EDGES))
        select_vertices_buttom.clicked.connect(lambda: self.set_mode(Mode.SELECT))
        add_graph_view_button.clicked.connect(self.add_graph_view)
    
    def set_mode(self, mode):
        for gv in self.graph_views:
            gv.set_mode(mode)
    
    def add_graph_view0(self):
        for gv in self.graph_views:
            self.graph_views_widget.removeWidget(gv)
        graph_views_dim = 600, 400
        w, h = graph_views_dim
        num_cols = 2
        row, col = 0, 0
        self.graph_views = [GraphView(w, h, gv.G, gv.vertex_mapping, gv.mode) for gv in self.graph_views]
        self.graph_views.append(GraphView(w, h))
        for gv in self.graph_views:
            print(row, col)
            self.graph_views_widget.addWidget(gv, row, col)
            row += ((col + 1) // num_cols)
            col = (col + 1) % num_cols
        self.update()
    
    def add_graph_view(self):
        old_w = self.graph_views_dim[0] // self.num_cols
        old_h = self.graph_views_dim[1] // self.num_rows
        ngraph_views = len(self.graph_views) + 1
        if ngraph_views > self.num_cols * self.num_rows:
            if self.num_rows == self.num_cols:
                self.num_cols += 1
            else:
                self.num_rows += 1
        
        w = self.graph_views_dim[0] // self.num_cols
        h = self.graph_views_dim[1] // self.num_rows

        print(old_w, old_h, w, h)

        for gv in self.graph_views:
            print(f"removing {gv}")
            gv.clear_canvas()
            self.graph_views_widget.removeWidget(gv)

        self.graph_views = [
            GraphView(
                w, h, gv.G,
                rescale_origin_mapping(gv.vertex_mapping, old_w, old_h, w, h),
                gv.mode
            )
            for gv in self.graph_views
        ]

        self.graph_views.append(GraphView(w, h))
        
        row, col = 0, 0
        for gv in self.graph_views:
            self.graph_views_widget.addWidget(gv, row, col)
            row += ((col + 1) // self.num_cols)
            col = (col + 1) % self.num_cols
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