import numpy as np
import itertools
from typing import List
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtWidgets import QLabel
from commandbar.api import cmdutils
from commandbar.commands.cmdexc import PrerequisitesError
from commandbar.utils import objreg

from mainwindow.painters import tools
from mainwindow.painters.painter import CustomPainter


canvas_id_gen = itertools.count(0)



class Canvas(QLabel):
    ZOOM_FACTOR = 1.1

    def __init__(self, win_id: int, w: int = 600, h: int = 800, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._win_id = win_id
        self.canvas_id = next(canvas_id_gen)
        print("canvas id", self.canvas_id)

        canvas = QtGui.QPixmap(w, h)
        self.setPixmap(canvas)
        self.setMouseTracking(True)
        self.setMinimumSize(1, 1)

        self._init_registry()

        self.qpainter = CustomPainter(self.pixmap())
        # self.state = GridCanvasState(self, 10, 10)
        self.content_managers: List[CanvasContentManager] = []
        self.painter: CanvasPainter = None
        self.last_drag_point = None
    
    def _init_registry(self):
        self.registry = objreg.ObjectRegistry()
        canvas_registry = objreg.get('canvas-registry', scope='window', window=self._win_id)
        canvas_registry[self.canvas_id] = self
        objreg.register('canvas', self, registry=self.registry)
        objreg.register('painters', dict(), registry=self.registry)
    
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.buttons() == QtCore.Qt.RightButton:
            self.last_drag_point = e.pos()
        self.painter and self.painter.on_mouse_press(e)
        self.update()
    
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if e.buttons() == QtCore.Qt.NoButton:
            self.painter and self.painter.on_mouse_hover(e)
        elif e.buttons() == QtCore.Qt.LeftButton:
            self.painter and self.painter.on_mouse_left_click_drag(e)
        elif e.buttons() == QtCore.Qt.RightButton:
            self.on_drag(e)
        self.update()
            # self.painter.on_mouse_right_click_drag(e)
    
    def on_drag(self, e: QtGui.QMouseEvent):
        self.clear_canvas()
        dp: QtCore.QPoint = e.pos() - self.last_drag_point
        self.last_drag_point = e.pos()
        for cm in self.content_managers:
            cm.on_canvas_move(dp)
        self.update()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        self.painter and self.painter.on_mouse_release(e)
        self.update()
    
    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self.clear_canvas()
        self.qpainter.end()
        self.setPixmap(self.pixmap().scaled(e.size()))
        self.qpainter = CustomPainter(self.pixmap())
        if self.painter:
            self.painter.painter = self.qpainter
        for cm in self.content_managers:
            cm.on_canvas_resize(e)
        self.update()
    
    def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
        steps = e.angleDelta().y() // 120
        if steps == 0:
            return
        factor = self.ZOOM_FACTOR * abs(steps)
        factor = factor if steps > 0 else 1 / factor
        self.clear_canvas()
        for cm in self.content_managers:
            cm.on_zoom(factor, e)
        self.update()
    
    def add_content_manager(self, name: str, cm: 'CanvasContentManager'):
        self.content_managers.append(cm)
        objreg.register(name, cm, registry=self.registry)
        self.update()
    
    def clear_canvas(self):
        self.qpainter.set(tools.BLACK_PEN, tools.BLACK_BRUSH)
        self.qpainter.drawRect(0, 0, self.width(), self.height())
        self.update()
    
    def set_painter(self, painter: 'CanvasPainter'):
        if self.painter:
            self.painter.on_unset()
        self.painter: CanvasPainter = painter
        self.painter.painter = self.qpainter
        self.painter.on_set()
        self.update()


    @cmdutils.register(name='set-painter', instance='canvas', scope='canvas')
    def set_painter_command(self, painter: str):
        """
        sets the canvas painter to the given painter
        """
        painters = objreg.get('painters', scope='canvas')
        if painter not in painters:
            raise PrerequisitesError(f"There is no such painter {painter}")
        self.set_painter(painters[painter])


class CanvasContentManager:
    def __init__(self, canvas: Canvas) -> None:
        self.canvas = canvas
    
    def on_canvas_resize(self, e: QtGui.QResizeEvent):
        """
        repaint the content to match the new window size
        """
        pass

    def on_zoom(self, factor: float, e: QtGui.QWheelEvent):
        """
        repaint content resized by the zoom factor
        """
        pass

    def on_canvas_move(self, offset: QtCore.QPoint):
        """
        relocate and repaint the content with respect to the 
        new given offset
        """
        pass


class CanvasPainter:
    def __init__(self, painter: CustomPainter) -> None:
        self.painter = painter
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        pass

    def on_mouse_release(self, e: QtGui.QMouseEvent):
        pass

    def on_mouse_right_click_drag(self, e: QtGui.QMouseEvent):
        pass

    def on_mouse_left_click_drag(self, e: QtGui.QMouseEvent):
        pass

    def on_mouse_hover(self, e: QtGui.QMouseEvent):
        pass

    def on_set(self):
        """
        called when the painter is set as the canvas painter
        """
        pass

    def on_unset(self):
        """
        called when the painter is unset as the canvas painter
        """
        pass