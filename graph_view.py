import networkx as nx
from enum import Enum, auto
from typing import Iterable, Optional, Dict, Any, Tuple

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QLabel
from PyQt5 import QtGui
from PyQt5.QtGui import (
    QPixmap, 
    QPainter,
    QPaintDevice,
    QPen,
    QBrush,
    QColor,
)
from shapely.geometry import LineString
from itertools import combinations
from shapely.geometry.multipoint import MultiPoint
from shapely.geometry.point import Point
from graph_view_state import DeleteEdgesState, DragViewState, GraphViewStateFactory, MoveVerticesState, PaintEdgesState, PaintVerticesState, SelectVerticesState


class Mode(Enum):
    MOVE = auto()
    DELETE = auto()
    PAINT_VERTICES = auto()
    PAINT_EDGES = auto()
    SELECT = auto()
    DRAG = auto()


class MyPainter(QPainter):
    def __init__(self, pd: QPaintDevice):
        super().__init__(pd)
    
    def __call__(self, pen: Optional[QPen] = None, brush: Optional[QBrush] = None):
        if pen:
            self.setPen(pen)
        if brush:
            self.setBrush(brush)
        return self
    
    def __enter__(self):
        pass

    def __exit__(self, *args, **kwargs) -> None:
        pass


class GraphView(QLabel):
    def __init__(
        self,
        w: int, h: int,
        G: Optional[nx.Graph] = None,
        vertex_mapping: Optional[Dict[Any, Tuple[int, int]]] = None,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.G = G or nx.Graph()
        self.vertex_mapping = vertex_mapping or dict()
        self.state_factory = GraphViewStateFactory()
        self.state = self.state_factory.initial_state(self)

        canvas = QPixmap(w, h)
        self.setPixmap(canvas)
        
        self.r = 5
        self.cummultive_r = self.r
        self.painter = MyPainter(self.pixmap())

        self.white_pen = QPen(QColor('white'))
        self.black_pen = QPen(QColor('black'))
        self.white_brush = QBrush(QColor('white'), Qt.SolidPattern)
        self.black_brush = QBrush(QColor('black'), Qt.SolidPattern)
        self.blue_pen = QPen(QColor(0x3895d3))
        self.blue_brush = QBrush(QColor(0x3895d3), Qt.SolidPattern)
        self.gray_pen = QPen(QColor('gray'))

        self.base_zoom_factor = 1.1

        self.clear_canvas()
    
    def clear_canvas(self):
        with self.painter(self.black_pen, self.black_brush):
            self.painter.drawRect(0, 0, self.pixmap().width(), self.pixmap().height())
        self.update()
    
    def draw_vertex(self, u, pen=None, brush=None):
        pen = pen or self.white_pen
        brush = brush or self.white_brush
        with self.painter(pen, brush):
            self.painter.drawEllipse(QPoint(*self.vertex_mapping[u]), self.r, self.r)
        self.update()
    
    def draw_edge(self, u, v, pen=None, brush=None):
        pen = pen or self.white_pen
        brush = brush or self.white_brush
        with self.painter(pen, brush):
            self.painter.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
        self.update()
    
    def delete_vertex(self, u):
        with self.painter(self.black_pen, self.black_brush):
            self.painter.drawEllipse(QPoint(*self.vertex_mapping[u]), self.r, self.r)
        self.update()
    
    def delete_edge(self, u, v):
        with self.painter(self.black_pen, self.black_brush):
            self.painter.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
        self.update()
    
    def delete_vertices(self, vertices):
        self.draw_vertices(vertices, self.black_pen, self.black_brush)
    
    def delete_edges(self, edges):
        self.draw_edges(edges, self.black_pen, self.black_brush)
    
    def draw_vertices(self, vertices: Iterable, pen=None, brush=None):
        pen = pen or self.white_pen
        brush = brush or self.white_brush
        with self.painter(pen, brush):
            for u in vertices:
                self.painter.drawEllipse(QPoint(*self.vertex_mapping[u]), self.r, self.r)
        self.update()
    
    def draw_edges(self, edges: Iterable[Tuple[Any, Any]], pen=None, brush=None):
        pen = pen or self.white_pen
        brush = brush or self.white_brush
        with self.painter(pen, brush):
            for u, v in edges:
                self.painter.drawLine(*self.vertex_mapping[u], *self.vertex_mapping[v])
        self.update()
    
    def draw_selected_vertex(self, u):
        self.r += 2
        self.draw_vertex(u, self.blue_pen, self.blue_brush)
        self.r -= 2
        self.draw_vertex(u)
    
    def draw_selected_vertices(self, vertices):
        self.r += 2
        self.draw_vertices(vertices, self.blue_pen, self.blue_brush)
        self.r -= 2
        self.draw_vertices(vertices)
    
    def delete_selected_vertices(self, vertices):
        self.r += 2
        self.delete_vertices(vertices)
        self.r -= 2
        self.draw_vertices(vertices)
    
    def draw_graph(self):
        self.draw_vertices(self.G.nodes)
        self.draw_edges(self.G.edges)
    
    def delete_graph(self):
        self.delete_vertices(self.G.nodes)
        self.delete_edges(self.G.edges)
    
    def draw_vertex_edges(self, u):
        self.draw_edges((u, v) for v in self.G[u])
    
    def delete_vertex_edges(self, u):
        self.delete_edges((u, v) for v in self.G[u])

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.state.on_mouse_press(a0)
    
    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.state.on_mouse_release(a0)
    
    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.state.on_mouse_move(a0)
    
    def zoom(self, rel_x, rel_y, factor):
        self.cummultive_r *= factor
        self.r = max(3, int(self.cummultive_r))
        self.clear_canvas()
        for u, (x, y) in self.vertex_mapping.items():
            dx = x - rel_x
            dy = y - rel_y
            self.vertex_mapping[u] = (rel_x + int(factor * dx), rel_y + int(factor * dy))
        self.draw_graph()
    
    def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:
        steps = a0.angleDelta().y() // 120
        factor = self.base_zoom_factor ** abs(steps)
        factor = factor if steps > 0 else 1 / factor
        self.zoom(a0.x(), a0.y(), factor)
    
    def set_mode(self, mode):
        mode_to_state = {
            Mode.PAINT_VERTICES: PaintVerticesState,
            Mode.PAINT_EDGES: PaintEdgesState,
            Mode.SELECT: SelectVerticesState,
            Mode.MOVE: MoveVerticesState,
            Mode.DELETE: DeleteEdgesState,
            Mode.DRAG: DragViewState,
        }
        new_state = mode_to_state[mode](self)
        self.state.transition_out(new_state)
        new_state.transition_in(self.state)
        self.state = new_state
        # if self.mode == Mode.SELECT and self.selected_vertices:
        #     self.unmark_vertices(self.selected_vertices)
        #     if mode == Mode.PAINT_EDGES:
        #         self.get_non_edges = lambda: filter(
        #             lambda e: set(e).issubset(self.selected_vertices) and not self.G.has_edge(*e),
        #             combinations(self.G.nodes, 2)
        #         )
        #         self.draw_missing_edges(self.get_non_edges())
        # elif mode == Mode.PAINT_EDGES:
        #     self.get_non_edges = lambda: filter(
        #         lambda e: not self.G.has_edge(*e),
        #         combinations(self.G.nodes, 2)
        #     )
        #     self.draw_missing_edges(self.get_non_edges())
        # elif self.mode == Mode.PAINT_EDGES and mode != Mode.PAINT_EDGES:
        #     self.delete_missing_edges()
        # self.mode = mode
    