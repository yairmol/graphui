from PyQt5.QtCore import QTimer

import networkx as nx

from commandbar.api import cmdutils
from commandbar.commands.cmdexc import ArgumentTypeError, PrerequisitesError
from commandbar.utils import objreg
from graph.responsive_graph import ResponsiveGraph, V
from mainwindow import mainwindow
from mainwindow.graph_view import GraphView 
from graph.callbacks import BFSCallbacks, ColorVertexCallback, WaitCallback


@cmdutils.register(name='run-bfs', instance='main-window', scope='window')
def run_bfs(self: mainwindow.MainWindow, source=1, step_time=0.5):
    try:
        gv: GraphView = objreg.get('graph-view', scope='window', window=self.win_id)
    except KeyError:
        raise PrerequisitesError('There is no currently active graph view')
    if source is None and len(gv.G.nodes):
        source = next(iter(gv.G.nodes))
    if source not in gv.G.nodes:
        raise ArgumentTypeError("Invalid source vertex")
    print(gv.G.nodes)
    print(source)
    callbacks = BFSCallbacks(gv)
    gv.G.regsiter_node_iter_callback(callbacks.iter_next_callback)
    gv.G.adj.register_callback('__getitem__', callbacks.getitem_callback)
    gv.G.regsiter_node_iter_callback(WaitCallback(step_time))
    QTimer.singleShot(0, lambda: run_on_vertices(gv, source))
    print("finished command")


def run_on_vertices(gv: GraphView, source):
    print("starting")
    # for u in gv.G:
    #     print(u)
    nx.single_source_shortest_path_length(gv.G, source)
    gv.G.clear_vertex_iterator_callbacks()