from PyQt5.QtCore import QPoint
import numpy as np
from itertools import combinations

from PyQt5 import QtGui

from shapely.geometry import LineString
from shapely.geometry.multipoint import MultiPoint
from shapely.geometry.point import Point

# from graph_view import GraphView


class GraphViewState:

    def __init__(self, graph_view) -> None:
        self.graph_view = graph_view
        self.G = graph_view.G
        self.vertex_mapping = self.graph_view.vertex_mapping
        # self.factory = state_factory

    def on_mouse_move(self, e: QtGui.QMouseEvent):
        pass

    def on_mouse_press(self, e: QtGui.QMouseEvent):
        pass

    def on_mouse_release(self, e: QtGui.QMouseEvent):
        pass

    def transition_in(self, other: 'GraphViewState'):
        pass

    def transition_out(self, other: 'GraphViewState'):
        pass


class PaintVerticesState(GraphViewState):
    
    def  __init__(self, graph_view) -> None:
        super().__init__(graph_view)
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        u = max(self.graph_view.G.nodes or [0]) + 1
        self.G.add_node(u)
        self.graph_view.set_vertex_loc(u, (e.x(), e.y()))
        self.graph_view.draw_vertex(u)


class PaintEdgesState(GraphViewState):

    def __init__(self, graph_view) -> None:
        super().__init__(graph_view)

        self.get_non_edges = lambda: filter(
            lambda e: not self.G.has_edge(*e),
            combinations(self.G.nodes, 2)
        )
        self.last_point = None
    
    def intersecting_non_edges(self, line: LineString, edges):
        intersecting_edges = set()
        for u, v in edges:
            if line.intersects(LineString([self.vertex_mapping[u], self.vertex_mapping[v]])):
                intersecting_edges.add((u, v))
        return intersecting_edges
    
    def transition_from_select_vertices(self, other: 'SelectVerticesState'):
        if other.selected_vertices:
            self.get_non_edges = lambda: filter(
                lambda e: set(e).issubset(other.selected_vertices) and not self.graph_view.G.has_edge(*e),
                combinations(self.graph_view.G.nodes, 2)
            )
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.last_point = (e.x(), e.y())
    
    def on_mouse_move(self, e: QtGui.QMouseEvent):
        cur_point = (e.x(), e.y())
        edges = self.intersecting_non_edges(LineString([self.last_point, cur_point]), self.get_non_edges())
        self.last_point = cur_point
        if not edges:
            return
        self.G.add_edges_from(edges)
        self.graph_view.draw_edges(edges)
    
    def transition_out(self, other: 'GraphViewState'):
        self.graph_view.delete_edges(self.get_non_edges())
    
    def transition_in(self, other: 'GraphViewState'):
        if isinstance(other, SelectVerticesState) and other.selected_vertices:
            self.get_non_edges = lambda: filter(
                lambda e: not self.G.has_edge(*e) and other.selected_vertices.issuperset(e),
                combinations(self.G.nodes, 2)
            )
        self.graph_view.draw_edges(self.get_non_edges(), self.graph_view.gray_pen)


class MoveVerticesState(GraphViewState):
    
    def __init__(self, graph_view) -> None:
        super().__init__(graph_view)
        self.r = self.graph_view.r
        self.moving_vertex = None
    
    def in_vertex(self, x, y):
        try:
            return next(
                u for u, (ux, uy) in self.vertex_mapping.items()
                if np.linalg.norm([ux - x, uy - y]) <= self.r + 5
            )
        except StopIteration:
            return None
        
    def relocate_vertex(self, u, x, y):
        # self.graph_view.delete_vertex(u)
        # self.graph_view.delete_vertex_edges(u)
        self.graph_view.clear_canvas()
        self.graph_view.set_vertex_loc(u, (x, y))
        self.graph_view.draw_graph()
        # self.graph_view.draw_vertex(u)
        # self.graph_view.draw_vertex_edges(u)
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.moving_vertex = self.in_vertex(e.x(), e.y())
    
    def on_mouse_move(self, e: QtGui.QMouseEvent):
        if self.moving_vertex is not None:
            self.relocate_vertex(self.moving_vertex, e.x(), e.y())
    
    def on_mouse_release(self, _: QtGui.QMouseEvent):
        self.moving_vertex = None


class DeleteEdgesState(GraphViewState):
     
    def __init__(self, graph_view) -> None:
        super().__init__(graph_view)
        self.last_point = None
    
    def intersecting_edges(self, line: LineString):
        intersecting_edges = set()
        for u, v in self.G.edges:
            if line.intersects(LineString([self.vertex_mapping[u], self.vertex_mapping[v]])):
                intersecting_edges.add((u, v))
        return intersecting_edges
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.last_point = (e.x(), e.y())

    def on_mouse_move(self, e: QtGui.QMouseEvent):
        cur_point = (e.x(), e.y())
        edges = self.intersecting_edges(LineString([self.last_point, cur_point]))
        self.G.remove_edges_from(edges)
        self.graph_view.delete_edges(edges)
        self.last_point = cur_point


class SelectVerticesState(GraphViewState):

    def __init__(self, graph_view) -> None:
        super().__init__(graph_view)
        self.selected_points = list()
        self.selected_vertices = set()
    
    def delete_selection_dots(self):
        with self.graph_view.painter(self.graph_view.black_pen):
            for p in self.selected_points:
                self.graph_view.painter.drawPoint(p)
        self.graph_view.update()
    
    def mark_selected_vertices(self):
        poly = MultiPoint([(p.x(), p.y()) for p in self.selected_points]).convex_hull
        for u, loc in self.graph_view.vertex_mapping.items():
            if poly.intersects(Point(*loc)):
                self.selected_vertices.add(u)
        self.graph_view.draw_selected_vertices(self.selected_vertices)

    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.graph_view.delete_selected_vertices(self.selected_vertices)
        self.selected_points = [e.pos()]
        self.selected_vertices = set()
    
    def on_mouse_release(self, e: QtGui.QMouseEvent):
        self.delete_selection_dots()
        self.mark_selected_vertices()
        self.selected_points.clear()
    
    def on_mouse_move(self, e: QtGui.QMouseEvent):
        p = e.pos()
        self.selected_points.append(p)
        with self.graph_view.painter(self.graph_view.white_pen):
            self.graph_view.painter.drawPoint(p)
        self.graph_view.update()
    
    def transition_out(self, other):
        if self.selected_vertices:
            self.graph_view.delete_selected_vertices(self.selected_vertices)


class DragViewState(GraphViewState):
    def __init__(self, graph_view) -> None:
        super().__init__(graph_view)
        self.base_x = None
        self.base_y = None
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.base_x = e.x()
        self.base_y = e.y()
    
    def on_mouse_move(self, e: QtGui.QMouseEvent):
        self.graph_view.clear_canvas()
        dx = e.x() - self.base_x
        dy = e.y() - self.base_y
        self.base_x = e.x()
        self.base_y = e.y()
        for u, (x, y) in self.vertex_mapping.items():
            self.vertex_mapping[u] = (x + dx, y + dy)
        self.graph_view.draw_graph()        


class GridState(GraphViewState):
    def __init__(self, graph_view) -> None:
        super().__init__(graph_view)
        self.spacing = graph_view.spacing
        self.m = graph_view.m
        self.n = graph_view.n
    
    def get_clicked_box(self, p: QPoint):
        return p.x() // self.spacing, p.y() // self.spacing
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        i, j = self.get_clicked_box(e.pos())
        print("box:", i, j)
        self.graph_view.draw_filled_box(i, j)

class GraphViewStateFactory:
    def initial_state(self, gv) -> GraphViewState:
        return PaintVerticesState(gv)
