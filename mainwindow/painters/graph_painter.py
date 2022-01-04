import math
from itertools import combinations
from PyQt5 import QtGui
from PyQt5 import QtCore
from shapely.geometry import MultiPoint

from typing import Any, Dict, Iterable, Tuple
from shapely.geometry.linestring import LineString

from shapely.geometry.point import Point
from commandbar.api import cmdutils
from mainwindow.canvas import Canvas, CanvasContentManager, CanvasPainter
from mainwindow.painters.painter import CustomPainter

from commandbar.utils import objreg
from mainwindow.painters import tools
from graph.responsive_graph import ResponsiveGraph


GRAPH_CONTENT = 'graph-content'
VERTICES_PAINTER = 'vertices-painter'
EDGES_PAINTER = 'edges-painter'
VERTICES_SELECTOR = 'vertices-selector'
GRAPH_ERASER = 'graph-eraser'
VERTICES_MOVER = 'vertices-mover'


def norm(p: QtCore.QPoint):
    return math.sqrt(p.x() ** 2 + p.y() ** 2)


@cmdutils.register(name='draw-vertices', instance='canvas', scope='canvas')
def draw_vertices(self: Canvas):
    if GRAPH_CONTENT not in self.registry:
        self.add_content_manager(GRAPH_CONTENT, GraphContent(self))
    painters = self.registry['painters']
    if VERTICES_PAINTER not in painters:
        painters[VERTICES_PAINTER] = VerticesPainter(self.qpainter)
    self.set_painter(painters[VERTICES_PAINTER])


@cmdutils.register(name='draw-edges', instance='canvas', scope='canvas')
def draw_edges(self: Canvas):
    if GRAPH_CONTENT not in self.registry:
        self.add_content_manager(GRAPH_CONTENT, GraphContent(self))
    painters = self.registry['painters']
    if EDGES_PAINTER not in painters:
        painters[EDGES_PAINTER] = EdgesPainter(self.qpainter)
    self.set_painter(painters[EDGES_PAINTER])


@cmdutils.register(name='select-vertices', instance='canvas', scope='canvas')
def select_vertices(self: Canvas):
    if GRAPH_CONTENT not in self.registry:
        self.add_content_manager(GRAPH_CONTENT, GraphContent(self))
    painters = self.registry['painters']
    if VERTICES_SELECTOR not in painters:
        painters[VERTICES_SELECTOR] = VerticesSelector(self.qpainter)
    self.set_painter(painters[VERTICES_SELECTOR])


@cmdutils.register(name='erase-graph', instance='canvas', scope='canvas')
def erase_graph(self: Canvas):
    if GRAPH_CONTENT not in self.registry:
        self.add_content_manager(GRAPH_CONTENT, GraphContent(self))
    painters = self.registry['painters']
    if GRAPH_ERASER not in painters:
        painters[GRAPH_ERASER] = GraphEraser(self.qpainter)
    self.set_painter(painters[GRAPH_ERASER])


@cmdutils.register(name='move-vertices', instance='canvas', scope='canvas')
def move_vertices(self: Canvas):
    if GRAPH_CONTENT not in self.registry:
        self.add_content_manager(GRAPH_CONTENT, GraphContent(self))
    painters = self.registry['painters']
    if VERTICES_MOVER not in painters:
        painters[VERTICES_MOVER] = MoveVertices(self.qpainter)
    self.set_painter(painters[VERTICES_MOVER])


class GraphContent(CanvasContentManager):
    R = 5
    MIN_R = 3

    def __init__(self, canvas: Canvas) -> None:
        super().__init__(canvas)
        self.graph = ResponsiveGraph()
        self.locations: Dict[Any, QtCore.QPoint] = dict()
        self.continuous_locations: Dict[Any, Tuple[float, float]] = dict()
        self.r = self.R
        self.continuous_r = self.R
        self.selected_vertices = set()
    
    def on_zoom(self, factor: float, e: QtGui.QWheelEvent):
        self.continuous_r *= factor
        self.r = max(self.MIN_R, int(self.continuous_r))
        rel_x, rel_y = e.x(), e.y()
        for u, (x, y) in self.continuous_locations.items():
            dx, dy = x - rel_x, y - rel_y
            x, y = rel_x + factor * dx, rel_y + factor * dy
            self.continuous_locations[u] = (x, y)
            self.locations[u] = QtCore.QPoint(int(x), int(y))
        self.draw_graph()
    
    def on_canvas_move(self, offset: QtCore.QPoint):
        for u, p in self.locations.items():
            self.locations[u] = p + offset
        for u, (x, y) in self.continuous_locations.items():
            self.continuous_locations[u] = (x + offset.x(), y + offset.y())
        self.draw_graph()

    def on_canvas_resize(self, e: QtGui.QResizeEvent):
        self.draw_graph()

    def intersecting_edges(self, line: QtCore.QLine, edges: Iterable[Tuple[Any, Any]]):
        intersecting = set()
        line = LineString([(line.x1(), line.y1()), (line.x2(), line.y2())])
        for u, v in edges:
            if line.intersects(LineString([self.continuous_locations[u], self.continuous_locations[v]])):
                intersecting.add((u, v))
        return intersecting

    def vertex_at(self, p: QtCore.QPoint):
        return next((u for u, loc in self.locations.items() if norm(p - loc) <= self.r), None)
            
    def draw_vertex(self, u, pen=None, brush=None, r=None):
        r = r or self.r
        self.canvas.qpainter.set(pen or tools.WHITE_PEN, brush or tools.WHITE_BRUSH)
        self.canvas.qpainter.drawEllipse(self.locations[u], r, r)
    
    def draw_edge(self, u, v, pen=None, brush=None):
        self.canvas.qpainter.set(pen or tools.WHITE_PEN, brush or tools.WHITE_BRUSH)
        self.canvas.qpainter.drawLine(self.locations[u], self.locations[v])
    
    def delete_vertex(self, u, r=None):
        r = r or self.r
        self.canvas.qpainter.set(tools.BLACK_PEN, tools.BLACK_BRUSH)
        self.canvas.qpainter.drawEllipse(self.locations[u], r, r)
    
    def delete_edge(self, u, v):
        self.canvas.qpainter.set(tools.BLACK_PEN, tools.BLACK_BRUSH)
        self.canvas.qpainter.drawLine(self.locations[u], self.locations[v])
    
    def draw_vertices(self, vertices: Iterable, pen=None, brush=None, r=None):
        r = r or self.r
        self.canvas.qpainter.set(pen or tools.WHITE_PEN, brush or tools.WHITE_BRUSH)
        for u in vertices:
            self.canvas.qpainter.drawEllipse(self.locations[u], r, r)
    
    def delete_vertices(self, vertices, r=None):
        r = r or self.r
        self.draw_vertices(vertices, tools.BLACK_PEN, tools.BLACK_BRUSH, r)
    
    def delete_edges(self, edges: Iterable):
        self.draw_edges(edges, tools.BLACK_PEN, tools.BLACK_BRUSH)
    
    def draw_edges(self, edges: Iterable[Tuple[Any, Any]], pen=None, brush=None):
        self.canvas.qpainter.set(pen or tools.WHITE_PEN, brush or tools.WHITE_BRUSH)
        for u, v in edges:
            self.canvas.qpainter.drawLine(self.locations[u], self.locations[v])
    
    def draw_selected_vertex(self, u):
        self.draw_vertex(u, tools.BLUE_PEN, tools.BLUE_BRUSH, self.r + 2)
        self.draw_vertex(u)
    
    def draw_selected_vertices(self, vertices):
        self.draw_vertices(vertices, tools.BLUE_PEN, tools.BLUE_BRUSH, self.r + 2)
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
    
    def next_vertex(self):
        return max(self.graph.nodes or [-1]) + 1
    
    def set_vertex_loc(self, u, loc: QtCore.QPoint):
        self.locations[u] = loc
        self.continuous_locations[u] = (loc.x(), loc.y())
    
    def remove_vertex(self, u):
        if u not in self.graph.nodes:
            return
        self.delete_vertex_edges(u)
        self.delete_vertex(u)
        self.graph.remove_node(u)
        self.locations.pop(u)
        self.continuous_locations.pop(u)
        if u in self.selected_vertices:
            self.selected_vertices.remove(u)


class BaseGraphPainter(CanvasPainter):
    def __init__(self, painter: CustomPainter) -> None:
        super().__init__(painter)
        self.content: GraphContent = objreg.get(
            GRAPH_CONTENT, scope='canvas', canvas='current'
        )


class VerticesPainter(BaseGraphPainter):
    def __init__(self, painter: CustomPainter) -> None:
        super().__init__(painter)
        self.last_hover = None
    
    def on_mouse_hover(self, e: QtGui.QMouseEvent):
        if self.last_hover and self.content.vertex_at(self.last_hover) is None:
            self.painter.set(tools.BLACK_PEN, tools.BLACK_BRUSH)
            self.painter.drawEllipse(self.last_hover, self.content.r, self.content.r)
        self.last_hover = e.pos()
        if self.content.vertex_at(e.pos()) is None:
            self.painter.set(tools.GRAY_PEN, tools.GRAY_BRUSH)
            self.painter.drawEllipse(self.last_hover, self.content.r, self.content.r)
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        u = self.content.next_vertex()
        self.content.graph.add_node(u)
        self.content.set_vertex_loc(u, e.pos())
        self.content.draw_vertex(u)


class EdgesPainter(BaseGraphPainter):
    def __init__(self, painter: CustomPainter) -> None:
        super().__init__(painter)
        self.last_point = None
    
    def on_set(self):
        self.content.draw_edges(
            filter(lambda e: e not in self.content.graph.edges, 
                   combinations(self.content.graph.nodes, 2)),
            tools.GRAY_PEN, tools.GRAY_BRUSH
        )
    
    def on_unset(self):
        self.content.delete_edges(
            filter(lambda e: e not in self.content.graph.edges, 
                   combinations(self.content.graph.nodes, 2)),
        )
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.last_point = e.pos()
    
    def on_mouse_left_click_drag(self, e: QtGui.QMouseEvent):
        intersecting = self.content.intersecting_edges(
            QtCore.QLine(self.last_point, e.pos()),
            filter(lambda e: e not in self.content.graph.edges,
                   combinations(self.content.graph.nodes, 2))
        )
        self.content.graph.add_edges_from(intersecting)
        self.content.draw_edges(intersecting)
        self.last_point = e.pos()


class GraphEraser(BaseGraphPainter):
    def __init__(self, painter: CustomPainter) -> None:
        super().__init__(painter)
        self.clicked_pos = None
        self.last_point = None
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.clicked_pos = e.pos()
        self.last_point = self.clicked_pos
    
    def on_mouse_left_click_drag(self, e: QtGui.QMouseEvent):
        edges = self.content.intersecting_edges(
            QtCore.QLine(self.last_point, e.pos()), 
            self.content.graph.edges
        )
        self.content.graph.remove_edges_from(edges)
        self.content.delete_edges(edges)
        self.last_point = e.pos()
    
    def on_mouse_release(self, e: QtGui.QMouseEvent):
        if self.clicked_pos == e.pos():
            u = self.content.vertex_at(self.clicked_pos)
            if u is not None:
                self.content.remove_vertex(u)


class VerticesSelector(BaseGraphPainter):
    def __init__(self, painter: CustomPainter) -> None:
        super().__init__(painter)
        self.selection_points = list()
    
    def delete_selection_dots(self):
        self.painter.set(tools.BLACK_PEN, tools.BLACK_BRUSH)
        for p in self.selection_points:
            self.painter.drawPoint(p)
    
    def mark_selected_vertices(self):
        poly = MultiPoint([(p.x(), p.y()) for p in self.selection_points]).convex_hull
        for u, loc in self.content.locations.items():
            if poly.intersects(Point(loc.x(), loc.y())):
                self.content.selected_vertices.add(u)
        self.content.draw_selected_vertices(self.content.selected_vertices)

    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.content.delete_selected_vertices(self.content.selected_vertices)
        self.selection_points = [e.pos()]
        self.content.selected_vertices.clear()
        self.painter.set(tools.WHITE_PEN)
    
    def on_mouse_release(self, e: QtGui.QMouseEvent):
        self.delete_selection_dots()
        self.mark_selected_vertices()
        self.selection_points.clear()
    
    def on_mouse_left_click_drag(self, e: QtGui.QMouseEvent):
        p = e.pos()
        self.selection_points.append(p)
        self.painter.drawPoint(p)


class MoveVertices(BaseGraphPainter):
    def __init__(self, painter: CustomPainter) -> None:
        super().__init__(painter)
        self.moving_vertex = None
    
    def relocate_vertex(self, u, p):
        self.content.delete_vertex_edges(u)
        self.content.delete_vertex(u)
        self.content.set_vertex_loc(u, p)
        self.content.draw_graph()
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.moving_vertex = self.content.vertex_at(e.pos())
    
    def on_mouse_left_click_drag(self, e: QtGui.QMouseEvent):
        if self.moving_vertex is not None:
            self.relocate_vertex(self.moving_vertex, e.pos())
    
    def on_mouse_release(self, _: QtGui.QMouseEvent):
        self.moving_vertex = None
