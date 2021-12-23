import sys
import datetime
import functools

from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import pyqtSlot, QObject, pyqtSignal, Qt

import mainwindow.mainwindow as mainwindow
from commandbar.config import qtargs
from commandbar.utils import log
from commandbar.misc import objects
from commandbar.utils import utils


class Application(QApplication):

    """Main application instance.

    Attributes:
        _args: ArgumentParser instance.
        _last_focus_object: The last focused object's repr.

    Signals:
        new_window: A new window was created.
        window_closing: A window is being closed.
    """

    new_window = pyqtSignal(mainwindow.MainWindow)
    window_closing = pyqtSignal(mainwindow.MainWindow)

    def __init__(self, args):
        """Constructor.

        Args:
            Argument namespace from argparse.
        """
        self._last_focus_object = None

        qt_args = qtargs.qt_args(args)
        log.init.debug("Commandline args: {}".format(sys.argv[1:]))
        log.init.debug("Parsed: {}".format(args))
        log.init.debug("Qt arguments: {}".format(qt_args[1:]))
        super().__init__(qt_args)

        objects.args = args

        log.init.debug("Initializing application...")

        self.launch_time = datetime.datetime.now()
        self.focusObjectChanged.connect(  # type: ignore[attr-defined]
            self.on_focus_object_changed)
        self.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.new_window.connect(self._on_new_window)

    @pyqtSlot(mainwindow.MainWindow)
    def _on_new_window(self, window):
        window.tabbed_browser.shutting_down.connect(functools.partial(
            self.window_closing.emit, window))

    @pyqtSlot(QObject)
    def on_focus_object_changed(self, obj):
        """Log when the focus object changed."""
        output = repr(obj)
        if self._last_focus_object != output:
            log.misc.debug("Focus object changed: {}".format(output))
        self._last_focus_object = output

    def __repr__(self):
        return utils.get_repr(self)
