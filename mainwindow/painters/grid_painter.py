import itertools
import numpy as np

from PyQt5 import QtCore, QtGui
from commandbar.api import cmdutils
from commandbar.commands.cmdexc import PrerequisitesError
from commandbar.utils import objreg
from mainwindow.canvas import CanvasContentManager, Canvas, CanvasPainter
from mainwindow.painters.painter import CustomPainter
from mainwindow.painters import tools


GRID_CONTENT = 'grid'
GRID_PAINTER = 'grid-painter'


@cmdutils.register(name='draw-grid', instance='canvas', scope='canvas')
def draw_grid(self: Canvas, rows: int, columns: int):
    if GRID_CONTENT not in self.registry:
        grid_content = GridContentManager(self, rows, columns)
        self.add_content_manager(GRID_CONTENT, grid_content)
    else:
        grid_content = self.registry[GRID_CONTENT]
        grid_content.delete()
        grid_content.set_rows_and_columns(rows, columns)
    grid_content.draw_grid(fill=True)
    self.update()
    painters = self.registry['painters']
    if GRID_PAINTER not in painters:
        painters[GRID_PAINTER] = GridPainter(self.qpainter)
    self.set_painter(painters[GRID_PAINTER])


@cmdutils.register(name='edit-grid', instance='canvas', scope='canvas')
def edit_grid(self: Canvas):
    if GRID_CONTENT not in self.registry:
        raise PrerequisitesError("There is no grid to edit, please use draw-grid.")
    painters = self.registry['painters']
    self.set_painter(painters[GRID_PAINTER])


class GridPainter(CanvasPainter):
    def __init__(self, painter: CustomPainter) -> None:
        super().__init__(painter)
        self.content: GridContentManager = objreg.get(
            GRID_CONTENT, scope='canvas', canvas='current'
        )
        self.current_hover = None
    
    def on_mouse_hover(self, e: QtGui.QMouseEvent):
        i, j = self.content.get_indices(e.pos())
        if self.current_hover and self.current_hover != (i, j):
            last_i, last_j = self.current_hover
            if self.content.matrix[last_i][last_j] == 2:
                self.content.mark_rect(last_i, last_j, tools.BLACK_BRUSH)
                self.content.matrix[last_i][last_j] = 0
        if not 0 <= i < self.content.rows or not 0 <= j < self.content.columns:
            return
        if self.content.matrix[i][j] == 0:
            self.content.mark_rect(i, j, tools.GRAY_BRUSH)
            self.content.matrix[i][j] = 2
        self.current_hover = i, j
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        i, j = self.content.get_indices(e.pos())
        if not 0 <= i < self.content.rows or not 0 <= j < self.content.columns:
            return
        if self.content.matrix[i][j] == 1:
            self.content.mark_rect(i, j, tools.BLACK_BRUSH)
            self.content.matrix[i][j] = 0
        else:
            self.content.mark_rect(i, j, tools.WHITE_BRUSH)
            self.content.matrix[i][j] = 1


class GridContentManager(CanvasContentManager):
    def __init__(self, canvas: Canvas, rows: int, columns: int, spacing=50):
        super().__init__(canvas)
        self.offset = QtCore.QPoint(0, 0)
        self.rows = rows
        self.columns = columns
        self.spacing = spacing
        self.continuous_spacing = self.spacing
        self.matrix = np.zeros((rows, columns))
        self.font_size = 8
        self.canvas.qpainter.setFont(QtGui.QFont('monospace', self.font_size))
    
    def draw_grid(self, fill=False):
        row_width = self.columns * self.spacing
        column_width = self.rows * self.spacing
        self.canvas.qpainter(tools.WHITE_PEN, tools.WHITE_BRUSH)
        for i in range(self.rows + 1):
            self.canvas.qpainter.drawLine(
                self.offset + QtCore.QPoint(0, self.spacing * i),
                self.offset + QtCore.QPoint(row_width, self.spacing * i)
            )
        for i in range(self.columns + 1):
            self.canvas.qpainter.drawLine(
                self.offset + QtCore.QPoint(self.spacing * i, 0),
                self.offset + QtCore.QPoint(self.spacing * i, column_width)
            )
        if not fill:
            return
        for i, j in itertools.product(range(self.rows), range(self.columns)):
            if self.matrix[i][j] == 2:
                self.mark_rect(i, j, tools.GRAY_BRUSH)
            elif self.matrix[i][j]:
                self.mark_rect(i, j, tools.WHITE_BRUSH)
            else:
                x, y = self.get_location(i, j)
                self.canvas.qpainter.drawText(
                    QtCore.QRect(x, y, self.spacing, self.spacing), 
                    QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter,
                    f"({i}, {j})"
                )
    
    def delete(self):
        self.canvas.qpainter.drawRect(
            self.offset.x(), self.offset.y(),
            self.spacing * self.columns, self.spacing * self.rows
        )
    
    def set_rows_and_columns(self, rows, columns):
        self.rows = rows
        self.columns = columns
        self.matrix = np.zeros((self.rows, self.columns))
    
    def get_indices(self, p: QtCore.QPoint):
        return (p.y() - self.offset.y()) // self.spacing, (p.x() - self.offset.x()) // self.spacing
    
    def get_location(self, i, j):
        return self.offset.x() + j * self.spacing, self.offset.y() + i * self.spacing
    
    def mark_rect(self, i, j, brush):
        self.canvas.qpainter.set(tools.WHITE_PEN, brush)
        x, y = self.get_location(i, j)
        self.canvas.qpainter.drawRect(x, y, self.spacing, self.spacing)
        self.canvas.qpainter.drawText(
            QtCore.QRect(x, y, self.spacing, self.spacing),
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter,
            f"({i}, {j})"
        )
    
    def on_zoom(self, factor: float, e: QtGui.QWheelEvent):
        self.offset = e.pos() + (self.offset - e.pos()) * factor
        self.continuous_spacing = self.continuous_spacing * factor
        self.spacing = int(self.continuous_spacing)
        self.font_size = self.font_size * factor
        self.canvas.qpainter.setFont(QtGui.QFont('monospace', int(self.font_size)))
        self.draw_grid(fill=True)

    def on_canvas_resize(self, e: QtGui.QResizeEvent):
        self.draw_grid(fill=True)
    
    def on_canvas_move(self, offset: QtCore.QPoint):
        self.offset += offset
        self.draw_grid(fill=True)
