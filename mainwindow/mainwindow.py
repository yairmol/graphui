import base64
import binascii
import functools
from typing import MutableSequence, Tuple

from PyQt5.QtCore import QPoint, QRect, QTimer, pyqtBoundSignal
from PyQt5.QtWidgets import QGridLayout, QSizePolicy, QVBoxLayout, QWidget
import networkx as nx
from mainwindow.canvas import Canvas

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
        self._overlays: MutableSequence[_OverlayInfoType] = []

        self._init_registries()
        
        self.canvases = [Canvas(self.win_id, 800, 600)]
        
        objreg.register('graph-view', self.canvases[0], scope='window', window=self.win_id)
        self._init_geometry(None)
        
        self.status = StatusBar(win_id=self.win_id, private=False)
        
        self._init_layout()
        self._init_completion()

        self._messageview = messageview.MessageView(parent=self)
        self._add_overlay(self._messageview, self._messageview.update_geometry)

        log.init.debug("Initializing modes...")
        modeman.init(win_id=self.win_id, parent=self)

        self._commandrunner = runners.CommandRunner(self.win_id,
                                                    partial_match=True)
        self._connect_signals()
        QTimer.singleShot(0, self._connect_overlay_signals)
        stylesheet.set_register(self)
    
    def _init_registries(self):
        self.registry = objreg.ObjectRegistry()
        objreg.window_registry[self.win_id] = self
        objreg.register('main-window', self, scope='window',
                        window=self.win_id)
        objreg.register('canvas-registry', objreg.ObjectRegistry(), scope='window', window=self.win_id)
    
    def _init_layout(self):
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(0)
        self.canvases_widget = QWidget()
        self.canvases_grid = QGridLayout(self.canvases_widget)
        self.canvases_grid.addWidget(self.canvases[0])
        self.canvases_grid.setContentsMargins(0, 0, 0, 0)
        self.canvases_grid.setSpacing(1)
        self._vbox.addWidget(self.canvases_widget)
        self._vbox.addWidget(self.status)
    
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
