from typing import List
from PyQt5 import QtGui
import networkx as nx
from commandbar.api import cmdutils
from commandbar.commands.cmdexc import PrerequisitesError
from commandbar.utils import objreg
from mainwindow.graph_view import GraphView
from mainwindow.mainwindow import MainWindow
from tree_covers.pygraph.metric_spaces import tree_cover_bad_pairs, tree_cover_embedding_distortion


@cmdutils.register(name='calc-stretch', instance='main-window', scope='window', maxsplit=0)
def calculate_stretch(self: MainWindow):
    """
    calculate the stretch of the first graph in the window with respect to the cover
    that is induced by all other graphs in the window
    """
    if len(self.canvases) <= 1:
        raise PrerequisitesError("Number of graph view must be more then 1 to calculate stretch")
    V = set(self.canvases[0].G.nodes)
    if not all(V.issubset(gv.G.nodes) for gv in self.canvases[1:]):
        raise PrerequisitesError("the set of verticies of the first graph must"
                                 "be a subset of the vertices of tje other graphs")
    sc = StretchCalculator(self.canvases)
    objreg.register('stretch-calculator', sc, scope='window', window=self.win_id)


class StretchCalculator:
    def __init__(self, graph_views: List[GraphView]) -> None:
        self.graph_views = graph_views
        self.bad_pairs = self.calc_and_display_strecth_cb()
        # for gv in self.graph_views:
        #     gv.G.register_on_edge_add_callback(self.calc_and_display_strecth_cb)
        #     gv.G.register_on_edge_remove_callback(self.calc_and_display_strecth_cb)
        self.last_bad_pair = None
    
    def calc_and_display_strecth_cb(self, *args):
        dist = tree_cover_embedding_distortion(self.graph_views[0].G, [gv.G for gv in self.graph_views[1:]])
        print(dist)
        self.bad_pairs = tree_cover_bad_pairs(self.graph_views[0].G, [gv.G for gv in self.graph_views[1:]], 1.1)
        self.bad_pairs = list(self.bad_pairs)
        print(self.bad_pairs)
        self.bad_pairs = iter(self.bad_pairs)
        return self.bad_pairs

    @cmdutils.register(instance='stretch-calculator', name='next-stetch-pair', scope='window')
    def next_pair(self):
        """
        displays the next pair that has high stretch 
        and its respective paths in each graph view
        """
        if self.last_bad_pair:
            u, v = self.last_bad_pair
            for gv in self.graph_views:
                p = nx.shortest_path(gv.G, u, v)
                gv.draw_edges(zip(p, p[1:]))
                gv.draw_vertices(p)
        try:
            u, v = next(self.bad_pairs)
            self.last_bad_pair = u, v
            for gv in self.graph_views:
                p = nx.shortest_path(gv.G, u, v)
                red_pen = QtGui.QPen(QtGui.QColor('red'))
                gv.draw_edges(zip(p, p[1:]), red_pen, None)
                gv.draw_vertices(p, red_pen)
        except StopIteration:
            raise PrerequisitesError("Out of bad pairs")