from enum import Enum, auto
import sys
from typing import Any, Dict, Optional, Tuple
from PyQt5 import QtGui, QtWidgets  # , uic
from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtWidgets import QGridLayout, QPushButton, QVBoxLayout, QWidget
from time import sleep
import networkx as nx
import numpy as np
from graph_view import Mode, GraphView
# from graph_view2 import GraphView2 as GraphView


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


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._main = QWidget()
        self.grid = QGridLayout(self._main)
        self.graph_views_dim = 1200, 800
        self.graph_views = [GraphView(*self.graph_views_dim)]  # , GraphView(*graph_views_dim)]
        self.gvwidget = QWidget()
        self.graph_views_widget = QGridLayout(self.gvwidget)
        self.num_rows, self.num_cols = 1, 1
        self.graph_views_widget.addWidget(self.graph_views[0])
        self.grid.addWidget(self.gvwidget, 0, 0)
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
        drag_graph_view_button = QPushButton('Drag View', self)
        self.buttons.addWidget(drag_graph_view_button)
        # button.setToolTip('This is an example button')
        # button.move(100,70)
        delete_edges_button.clicked.connect(lambda: self.set_mode(Mode.DELETE))
        move_vertices_button.clicked.connect(lambda: self.set_mode(Mode.MOVE))
        paint_vertices_button.clicked.connect(lambda: self.set_mode(Mode.PAINT_VERTICES))
        paint_edges_button.clicked.connect(lambda: self.set_mode(Mode.PAINT_EDGES))
        select_vertices_buttom.clicked.connect(lambda: self.set_mode(Mode.SELECT))
        drag_graph_view_button.clicked.connect(lambda: self.set_mode(Mode.DRAG))
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

        for gv in self.graph_views:
            gv.painter.end()
            self.graph_views_widget.removeWidget(gv)
        
        self.grid.removeWidget(self.gvwidget)
        
        self.gvwidget = QWidget()
        self.graph_views_widget = QGridLayout(self.gvwidget)

        self.graph_views = [
            GraphView(
                w, h, gv.G,
                rescale_origin_mapping(gv.vertex_mapping, old_w, old_h, w, h),
            )
            for gv in self.graph_views
        ]
        self.graph_views.append(GraphView(w, h))
        
        row, col = 0, 0
        for gv in self.graph_views:
            self.graph_views_widget.addWidget(gv, row, col)
            gv.draw_graph()
            row += ((col + 1) // self.num_cols)
            col = (col + 1) % self.num_cols

        self.grid.addWidget(self.gvwidget, 0, 0)
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