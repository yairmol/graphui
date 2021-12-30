import base64
import binascii
import functools
from typing import Any, Dict, MutableSequence, Tuple

from PyQt5 import QtWidgets  # , uic
from PyQt5.QtCore import QPoint, QRect, QSize, QTimer, pyqtBoundSignal
from PyQt5.QtWidgets import QGridLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget, QLabel
from PyQt5 import QtGui
import networkx as nx
from commandbar.api import cmdutils
from commandbar.commands.cmdexc import ArgumentTypeError
from mainwindow.canvas import Canvas

from mainwindow.graph_view import Mode, GraphView, rescale_origin_mapping
from tree_covers.pygraph.metric_spaces import (
    tree_cover_embedding_distortion,
    tree_cover_bad_pairs
)
from graph.responsive_graph import ResponsiveGraph

from commandbar.statusbar.bar import StatusBar
from commandbar.utils import objreg, log, qtutils
from commandbar.keyinput import modeman
from commandbar.commands import runners
from commandbar.completion import completionwidget, completer
from commandbar.config import configfiles, stylesheet, config
from commandbar.utils import message
import mainwindow.messageview as messageview

_OverlayInfoType = Tuple[QWidget, pyqtBoundSignal, bool, str]


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


class MainWindow(QWidget):

    STYLESHEET = """
        HintLabel {
            background-color: {{ conf.colors.hints.bg }};
            color: {{ conf.colors.hints.fg }};
            font: {{ conf.fonts.hints }};
            border: {{ conf.hints.border }};
            border-radius: {{ conf.hints.radius }}px;
            padding-top: {{ conf.hints.padding['top'] }}px;
            padding-left: {{ conf.hints.padding['left'] }}px;
            padding-right: {{ conf.hints.padding['right'] }}px;
            padding-bottom: {{ conf.hints.padding['bottom'] }}px;
        }

        QMenu {
            {% if conf.fonts.contextmenu %}
                font: {{ conf.fonts.contextmenu }};
            {% endif %}
            {% if conf.colors.contextmenu.menu.bg %}
                background-color: {{ conf.colors.contextmenu.menu.bg }};
            {% endif %}
            {% if conf.colors.contextmenu.menu.fg %}
                color: {{ conf.colors.contextmenu.menu.fg }};
            {% endif %}
        }

        QMenu::item:selected {
            {% if conf.colors.contextmenu.selected.bg %}
                background-color: {{ conf.colors.contextmenu.selected.bg }};
            {% endif %}
            {% if conf.colors.contextmenu.selected.fg %}
                color: {{ conf.colors.contextmenu.selected.fg }};
            {% endif %}
        }

        QMenu::item:disabled {
            {% if conf.colors.contextmenu.disabled.bg %}
                background-color: {{ conf.colors.contextmenu.disabled.bg }};
            {% endif %}
            {% if conf.colors.contextmenu.disabled.fg %}
                color: {{ conf.colors.contextmenu.disabled.fg }};
            {% endif %}
        }
    """

    def __init__(self, parent = None):
        super().__init__(parent)
        self.win_id = 0
        self._vbox = QVBoxLayout(self)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(0)
        self._overlays: MutableSequence[_OverlayInfoType] = []
        self.registry = objreg.ObjectRegistry()
        objreg.window_registry[self.win_id] = self
        objreg.register('main-window', self, scope='window',
                        window=self.win_id)
        gv_registry = objreg.ObjectRegistry()
        objreg.register('gv-registry', gv_registry, scope='window', window=self.win_id)
        # self._main = QWidget()
        # self.grid = QGridLayout(self._main)
        self.graph_views_dim = 800, 600
        self.graph_views = [Canvas(self.win_id, *self.graph_views_dim)]# [GraphView(*self.graph_views_dim, win_id=self.win_id)]  # , GraphView(*graph_views_dim)]
        objreg.register('graph-view', self.graph_views[0], scope='window', window=self.win_id)
        self.gvwidget = QWidget()
        self.graph_views_grid = QGridLayout(self.gvwidget)
        self.num_rows, self.num_cols = 1, 1
        self.graph_views_grid.addWidget(self.graph_views[0])
        self.graph_views_grid.setContentsMargins(0, 0, 0, 0)
        self.graph_views_grid.setSpacing(1)
        # self.grid.addWidget(self.gvwidget, 0, 0)
        self._vbox.addWidget(self.gvwidget)
        # self._vbox.addWidget(self.graph_views[0])
        # self._vbox.addWidget(self.graph_views[1])
        # self.setCentralWidget(self._main)
        self._init_geometry(None)
        # self.grid.addWidget(self.status, 1, 0)
                # self.setCentralWidget(self.label)
        self.status = StatusBar(win_id=self.win_id, private=False)
        self._vbox.addWidget(self.status)
        self._init_completion()

        self._messageview = messageview.MessageView(parent=self)
        self._add_overlay(self._messageview, self._messageview.update_geometry)

        log.init.debug("Initializing modes...")
        modeman.init(win_id=self.win_id, parent=self)

        self._commandrunner = runners.CommandRunner(self.win_id,
                                                    partial_match=True)
        # self.init_buttons()
        self._connect_signals()
        QTimer.singleShot(0, self._connect_overlay_signals)
        stylesheet.set_register(self)
        self.bad_pairs = None
        self.last_bad_pair = None
        # print("layout", )
    
    def _add_overlay(self, widget, signal, *, centered=False, padding=0):
        self._overlays.append((widget, signal, centered, padding))
    
    def _update_overlay_geometries(self):
        """Update the size/position of all overlays."""
        for w, _signal, centered, padding in self._overlays:
            self._update_overlay_geometry(w, centered, padding)

    def _update_overlay_geometry(self, widget, centered, padding):
        """Reposition/resize the given overlay."""
        if not widget.isVisible():
            return

        if widget.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding:
            width = self.width() - 2 * padding
            if widget.hasHeightForWidth():
                height = widget.heightForWidth(width)
            else:
                height = widget.sizeHint().height()
            left = padding
        else:
            size_hint = widget.sizeHint()
            width = min(size_hint.width(), self.width() - 2 * padding)
            height = size_hint.height()
            left = (self.width() - width) // 2 if centered else 0

        height_padding = 20
        status_position = config.val.statusbar.position
        if status_position == 'bottom':
            if self.status.isVisible():
                status_height = self.status.height()
                bottom = self.status.geometry().top()
            else:
                status_height = 0
                bottom = self.height()
            top = self.height() - status_height - height
            top = qtutils.check_overflow(top, 'int', fatal=False)
            topleft = QPoint(left, max(height_padding, top))
            bottomright = QPoint(left + width, bottom)
        elif status_position == 'top':
            if self.status.isVisible():
                status_height = self.status.height()
                top = self.status.geometry().bottom()
            else:
                status_height = 0
                top = 0
            topleft = QPoint(left, top)
            bottom = status_height + height
            bottom = qtutils.check_overflow(bottom, 'int', fatal=False)
            bottomright = QPoint(left + width,
                                 min(self.height() - height_padding, bottom))
        else:
            raise ValueError("Invalid position {}!".format(status_position))

        rect = QRect(topleft, bottomright)
        log.misc.debug('new geometry for {!r}: {}'.format(widget, rect))
        if rect.isValid():
            widget.setGeometry(rect)
    
    def _connect_overlay_signals(self):
        """Connect the resize signal and resize everything once."""
        for widget, signal, centered, padding in self._overlays:
            signal.connect(
                functools.partial(self._update_overlay_geometry, widget,
                                  centered, padding))
            self._update_overlay_geometry(widget, centered, padding)
    
    def restart_overlays(self):
        for _, signal, _, _ in self._overlays:
            signal.disconnect()
        self._connect_overlay_signals()
    
    def _init_geometry(self, geometry):
        """Initialize the window geometry or load it from disk."""
        if geometry is not None:
            self._load_geometry(geometry)
        elif self.win_id == 0:
            self._load_state_geometry()
        else:
            self._set_default_geometry()
        log.init.debug("Initial main window geometry: {}".format(
            self.geometry()))
    
    def _load_state_geometry(self):
        """Load the geometry from the state file."""
        try:
            data = configfiles.state['geometry']['mainwindow']
            geom = base64.b64decode(data, validate=True)
        except KeyError:
            # First start
            self._set_default_geometry()
        except binascii.Error:
            log.init.exception("Error while reading geometry")
            self._set_default_geometry()
        else:
            self._load_geometry(geom)
    
    def _load_geometry(self, geom):
        """Load geometry from a bytes object.

        If loading fails, loads default geometry.
        """
        log.init.debug("Loading mainwindow from {!r}".format(geom))
        ok = self.restoreGeometry(geom)
        if not ok:
            log.init.warning("Error while loading geometry.")
            self._set_default_geometry()
    
    def _set_default_geometry(self):
        """Set some sensible default geometry."""
        self.setGeometry(QRect(50, 50, 800, 600))
    
    def _init_completion(self):
        self._completion = completionwidget.CompletionView(cmd=self.status.cmd,
                                                           win_id=self.win_id,
                                                           parent=self)
        completer_obj = completer.Completer(cmd=self.status.cmd,
                                            win_id=self.win_id,
                                            parent=self._completion)
        self._completion.selection_changed.connect(
            completer_obj.on_selection_changed)
        objreg.register('completion', self._completion, scope='window',
                        window=self.win_id, command_only=True)
        self._add_overlay(self._completion, self._completion.update_geometry)
    
    def _connect_signals(self):
        """Connect all mainwindow signals."""
        mode_manager = modeman.instance(self.win_id)

        # status bar
        mode_manager.entered.connect(self.status.on_mode_entered)
        mode_manager.left.connect(self.status.on_mode_left)
        mode_manager.left.connect(self.status.cmd.on_mode_left)

        # messages
        message.global_bridge.show_message.connect(
            self._messageview.show_message)
        message.global_bridge.flush()
        message.global_bridge.clear_messages.connect(
            self._messageview.clear_messages)

        # commands
        mode_manager.keystring_updated.connect(
            self.status.keystring.on_keystring_updated)
        self.status.cmd.got_cmd[str].connect(self._commandrunner.run_safely)
        self.status.cmd.got_cmd[str, int].connect(self._commandrunner.run_safely)
        # self.status.cmd.got_search.connect(self._command_dispatcher.search)

        # key hint popup
        # mode_manager.keystring_updated.connect(self._keyhint.update_keyhint)

        # command input / completion
        self.status.cmd.clear_completion_selection.connect(
            self._completion.on_clear_completion_selection)
        self.status.cmd.hide_completion.connect(
            self._completion.hide)
    
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
        delete_edges_button.clicked.connect(lambda: self.set_mode(Mode.delete_edges))
        move_vertices_button.clicked.connect(lambda: self.set_mode(Mode.move_vertices))
        paint_vertices_button.clicked.connect(lambda: self.set_mode(Mode.paint_vertices))
        paint_edges_button.clicked.connect(lambda: self.set_mode(Mode.paint_edges))
        select_vertices_buttom.clicked.connect(lambda: self.set_mode(Mode.select))
        drag_graph_view_button.clicked.connect(lambda: self.set_mode(Mode.drag))
        add_graph_view_button.clicked.connect(self.add_graph_view)
    
    def set_mode(self, mode):
        for gv in self.graph_views:
            gv.set_mode(mode)
    
    def display_next_bad_pair(self):
        if not self.bad_pairs:
            print("no bad pairs")
            return
        try:
            if self.last_bad_pair:
                u, v = self.last_bad_pair
                for gv in self.graph_views:
                    p = nx.shortest_path(gv.G, u, v)
                    gv.draw_edges(zip(p, p[1:]))
                    gv.draw_vertices(p)

            u, v = next(self.bad_pairs)
            self.last_bad_pair = u, v
            for gv in self.graph_views:
                p = nx.shortest_path(gv.G, u, v)
                red_pen = QtGui.QPen(QtGui.QColor('red'))
                gv.draw_edges(zip(p, p[1:]), red_pen, None)
                gv.draw_vertices(p, red_pen)
        except:
            print("out of bad pairs")
            self.bad_pairs = None
            self.last_bad_pair = None
    
    def set_auto_stretch(self):
        if not self.calc_stretch:
            stretch_label = QLabel()
            stretch_label.setText("stretch: ")
            stretch_label.setFont(QtGui.QFont('calibry', 12, 1, False))
            self.buttons.addWidget(stretch_label)
            if len(self.graph_views) <= 1:
                return
            self.calc_stretch = True

            def calc_and_display_strecth_cb(*args):
                dist = tree_cover_embedding_distortion(self.graph_views[0].G, [gv.G for gv in self.graph_views[1:]])
                print(dist)
                stretch_label.setText(f"stretch: {dist}")
                self.bad_pairs = tree_cover_bad_pairs(self.graph_views[0].G, [gv.G for gv in self.graph_views[1:]], 2)
                self.bad_pairs = list(self.bad_pairs)
                print(self.bad_pairs)
                self.bad_pairs = iter(self.bad_pairs)
            
            for gv in self.graph_views:
                gv.G.register_on_edge_add_callback(calc_and_display_strecth_cb)
                gv.G.register_on_edge_remove_callback(calc_and_display_strecth_cb)

    def add_graph_view0(self):
        for gv in self.graph_views:
            self.graph_views_grid.removeWidget(gv)
        graph_views_dim = 600, 400
        w, h = graph_views_dim
        num_cols = 2
        row, col = 0, 0
        self.graph_views = [GraphView(w, h, gv.G, gv.vertex_mapping, gv.mode) for gv in self.graph_views]
        self.graph_views.append(GraphView(w, h))
        for gv in self.graph_views:
            print(row, col)
            self.graph_views_grid.addWidget(gv, row, col)
            row += ((col + 1) // num_cols)
            col = (col + 1) % num_cols
        self.update()
    
    def _add_graph_view(self, graph: ResponsiveGraph, mapping: Dict[Any, Tuple[int, int]]):
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
        # n = len(self.graph_views)
        # old_w, old_h = self.graph_views[0].width(), self.graph_views[0].height()
        # print(old_w, old_h)

        # h, w = old_h // (n + 1), old_w

        for gv in self.graph_views:
            self.graph_views_grid.removeWidget(gv)
        
        self.graph_views.append(GraphView(old_w, old_h, graph, mapping, win_id=self.win_id))
        
        for gv in self.graph_views:
            gv.scale(QSize(w, h))
        
        # self.grid.removeWidget(self.gvwidget)
        
        # self.gvwidget = QWidget()
        # self.graph_views_widget = QGridLayout(self.gvwidget)

        # self.graph_views = [
        #     GraphView(
        #         w, h, gv.G,
        #         rescale_origin_mapping(gv.vertex_mapping, old_w, old_h, w, h),
        #     )
        #     for gv in self.graph_views
        # ]
        
        
        row, col = 0, 0
        for gv in self.graph_views:
            self.graph_views_grid.addWidget(gv, row, col)
            gv.draw_graph()
            row += ((col + 1) // self.num_cols)
            col = (col + 1) % self.num_cols

        # self.grid.addWidget(self.gvwidget, 0, 0)
        # self._vbox.removeWidget(self.status)
        # self.graph_views[-1].stackUnder(self._completion)
        # self.graph_views[-1].stackUnder(self._messageview)
        # self._vbox.addWidget(self.graph_views[-1])
        # self._vbox.addWidget(self.status)
        
        # self.restart_overlays()
        # self._update_overlay_geometries()

    def add_graph_view(self):
        self._add_graph_view(ResponsiveGraph(), dict())
    
    @cmdutils.register(name='duplicate', instance='main-window', scope='window')
    def duplicate_view(self, gv_id: int = None):
        """
        Create another graph view which is identical to the current selected view
        """
        if gv_id is None:
            gv: GraphView = objreg.get('graph-view', scope='window', window=self.win_id)
            gv_id = gv.gv_id
        if not isinstance(gv_id, int):
            gv_id = int(gv_id)
        try:
            gv = [gv for gv in self.graph_views if gv.gv_id == gv_id][0]
        except IndexError:
            raise ArgumentTypeError(f"there is no graph-view with id {gv_id}")
        self._add_graph_view(gv.G.copy(), gv.vertex_mapping.copy())
    
    @cmdutils.register(name='set-active-graph-view', instance='main-window', scope='window')
    def set_active_graph_view(self, gv_idx: int):
        """
        Sets the current active graph view
        """
        if not isinstance(gv_idx, int):
            gv_idx = int(gv_idx)
        if len(self.graph_views) <= gv_idx:
            raise ArgumentTypeError(f"graph-view id must be within range of nummber of graph views: {len(self.graph_views)}")
        objreg.register('graph-view', self.graph_views[gv_idx], scope='window', window=self.win_id, update=True)