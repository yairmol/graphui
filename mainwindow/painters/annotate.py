from typing import List, Optional, Set

from PyQt5 import QtCore, QtGui
from commandbar.api import cmdutils
from mainwindow.canvas import CanvasContentManager, Canvas, CanvasPainter
from mainwindow.painters.painter import CustomPainter
from mainwindow.painters import tools
from commandbar.utils import objreg


ANNOTATE_PAINTER = 'annotate-painter'
ANNOTATIONS = 'annotations'


@cmdutils.register(name='annotate', instance='canvas', scope='canvas')
def annotate(self: Canvas):
    if ANNOTATIONS not in self.registry:
        self.add_content_manager(ANNOTATIONS, AnnotationContentManager(self))
    painters = self.registry['painters']
    if ANNOTATE_PAINTER not in painters:
        painters[ANNOTATE_PAINTER] = AnnotatePainter(self.qpainter)
    self.set_painter(painters[ANNOTATE_PAINTER])


class AnnotationContentManager(CanvasContentManager):
    def __init__(self, canvas: Canvas) -> None:
        super().__init__(canvas)
        self.lines: List[QtCore.QLine] = list()


class AnnotatePainter(CanvasPainter):
    def __init__(self, painter: CustomPainter) -> None:
        super().__init__(painter)
        self.content: AnnotationContentManager = objreg.get(
            'annotations', scope='canvas', canvas='current'
        )
        self.last_point: Optional[QtCore.QPoint] = None
        self.pen, self.brush = tools.make_pen_and_brush('white')
        #tools.WHITE_PEN, tools.WHITE_BRUSH
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.last_point = e.pos()
    
    def on_mouse_left_click_drag(self, e: QtGui.QMouseEvent):
        new_point = e.pos()
        self.painter.set(self.pen, self.brush)
        line = QtCore.QLine(self.last_point, new_point)
        self.painter.drawLine(self.last_point, new_point)
        self.content.lines.append(line)
        self.last_point = new_point
    
    @cmdutils.register(name='set-color', instance='annotate-painter', scope='canvas')
    def set_color(self, color: str):
        color = QtGui.QColor(color)
        self.pen = QtGui.QPen(color)
        self.brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)