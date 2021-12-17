import networkx as nx
from enum import Enum, auto
from typing import Iterable, Optional, Dict, Any, Tuple

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5 import QtGui
from PyQt5.QtGui import (
    QPixmap, 
    QPainter,
    QPaintDevice,
    QPen,
    QBrush,
    QColor,
)
from commandbar.keyinput.modeman import instance
from graph_view_state import (
    DeleteEdgesState,
    DragViewState,
    GraphViewStateFactory,
    MoveVerticesState,
    PaintEdgesState,
    PaintVerticesState,
    SelectVerticesState
)
from responsive_graph import ResponsiveGraph
from commandbar.api import cmdutils
from commandbar.utils import objreg

class Mode(Enum):
    move_vertices = auto()
    delete_edges = auto()
    paint_vertices = auto()
    paint_edges = auto()
    select = auto()
    drag = auto()


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
        win_id=None,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._win_id = win_id
        objreg.register('graph-view', self, scope='window', window=self._win_id)
        self.setMinimumSize(1, 1)

        self.G = G or ResponsiveGraph()
        self.vertex_mapping = vertex_mapping or dict()
        self.float_vertex_mapping = self.vertex_mapping.copy()
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

        self.base_x = None
        self.base_y = None
        self.clicked_button = 0

        self.clear_canvas()
    
    def set_vertex_loc(self, u, loc):
        self.vertex_mapping[u] = loc
        self.float_vertex_mapping[u] = loc
    
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
        self.clicked_button = a0.button()
        if self.clicked_button == Qt.LeftButton:
            self.state.on_mouse_press(a0)
        elif self.clicked_button == Qt.RightButton:
            self.base_x = a0.x()
            self.base_y = a0.y()
    
    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.clicked_button = 0
        self.state.on_mouse_release(a0)
    
    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        if self.clicked_button == Qt.RightButton:
            self.clear_canvas()
            dx = a0.x() - self.base_x
            dy = a0.y() - self.base_y
            self.base_x = a0.x()
            self.base_y = a0.y()
            for u, (x, y) in self.vertex_mapping.items():
                self.vertex_mapping[u] = (x + dx, y + dy)
            for u, (x, y) in self.float_vertex_mapping.items():
                self.float_vertex_mapping[u] = (x + dx, y + dy)
            self.draw_graph()
        else:
            self.state.on_mouse_move(a0)
    
    def zoom(self, rel_x, rel_y, factor):
        self.cummultive_r *= factor
        self.r = max(3, int(self.cummultive_r))
        self.clear_canvas()
        for u, (x, y) in self.float_vertex_mapping.items():
            dx = x - rel_x
            dy = y - rel_y
            x, y = rel_x + factor * dx, rel_y + factor * dy
            self.float_vertex_mapping[u] = (x, y)
            self.vertex_mapping[u] = (int(x), int(y))
        self.draw_graph()
    
    def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:
        steps = a0.angleDelta().y() // 120
        factor = self.base_zoom_factor ** abs(steps)
        factor = factor if steps > 0 else 1 / factor
        self.zoom(a0.x(), a0.y(), factor)
    
    @cmdutils.register(name='paint-edges', instance='graph-view', scope='window')
    def paint_edges(self):
        self.set_mode(Mode.paint_edges)
    
    @cmdutils.register(name='set-gv-mode', instance='graph-view', scope='window')
    def set_mode(self, mode: str):
        mode = Mode[mode]
        print(mode)
        mode_to_state = {
            Mode.paint_vertices: PaintVerticesState,
            Mode.paint_edges: PaintEdgesState,
            Mode.select: SelectVerticesState,
            Mode.move_vertices: MoveVerticesState,
            Mode.delete_edges: DeleteEdgesState,
            Mode.drag: DragViewState,
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
    
    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        # print(a0.size())
        self.painter.end()
        self.setPixmap(self.pixmap().scaled(a0.size()))
        self.painter = MyPainter(self.pixmap())
        self.clear_canvas()
        self.draw_graph()
