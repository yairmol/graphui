import numpy as np
import itertools
from typing import Optional, Union
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint, QRect, QSize
from PyQt5.QtGui import QBrush, QColor, QFont, QPen, QPixmap
from PyQt5.QtWidgets import QLabel

from mainwindow.painters import tools
from mainwindow.painters.painter import CustomPainter


canvas_id_gen = itertools.count(0)



class Canvas(QLabel):
    def __init__(self, win_id: int, w: int = 600, h: int = 800, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._win_id = win_id
        self.canvas_id = next(canvas_id_gen)

        canvas = QPixmap(w, h)
        self.setPixmap(canvas)
        self.setMouseTracking(True)
        self.setMinimumSize(1, 1)

        self.painter = CustomPainter(self.pixmap())
        self.state = AnnotateCanvasState(self)# GridCanvasState(self, 5, 5)
    
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        self.state.on_mouse_press(e)
    
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if e.buttons() == QtCore.Qt.NoButton:
            self.state.on_mouse_hover(e)
        elif e.buttons() == QtCore.Qt.LeftButton:
            self.state.on_mouse_left_click_drag(e)
        elif e.buttons() == QtCore.Qt.RightButton:
            self.state.on_mouse_right_click_drag(e)
    
    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        return self.state.on_mouse_release(e)
    
    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self.scale(e.size())
        self.state.on_resize(e)
    
    def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
        # steps = e.angleDelta().y() // 120
        self.state.on_wheel_move(e)
    
    def set_state(self, state: Union[str, 'BaseCanvasState']):
        self.state.transition_to(state)
        state.transition_from(self.state)
        self.state = state
    
    def scale(self, size: QSize):
        self.painter.end()
        self.setPixmap(self.pixmap().scaled(size))
        self.painter = CustomPainter(self.pixmap())


class BaseCanvasState:
    def __init__(self, canvas: Canvas):
        self.canvas = canvas

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
    
    def on_resize(self, e: QtGui.QResizeEvent):
        pass

    def on_wheel_move(self, e: QtGui.QWheelEvent):
        pass

    def transition_to(self, other: 'BaseCanvasState'):
        pass

    def transition_from(self, other: 'BaseCanvasState'):
        pass


class AnnotateCanvasState(BaseCanvasState):
    def __init__(self, canvas: Canvas) -> None:
        super().__init__(canvas)
        self.segments = set()
        self.last_point: Optional[QPoint] = None
        self.pen, self.brush = QPen(QColor('white')), QBrush(QColor('white'))
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        self.last_point = e.pos()
    
    def on_mouse_left_click_drag(self, e: QtGui.QMouseEvent):
        new_point = e.pos()
        with self.canvas.painter(self.pen, self.brush):
            self.canvas.painter.drawLine(self.last_point, new_point)
        self.last_point = new_point
        self.canvas.update()


class GridCanvasState(BaseCanvasState):
    def __init__(self, canvas: Canvas, rows: int, columns: int, spacing=50):
        super().__init__(canvas)
        self.offset_x = 0
        self.offset_y = 0
        self.rows = rows
        self.columns = columns
        self.spacing = spacing
        self.continuos_spacing = self.spacing
        self.matrix = np.zeros((rows, columns))
        self.current_hover = None
        self.base_zoom_factor = 1.1
        self.last_point = None
        self.font_size = 8
        self.canvas.painter.setFont(QFont('monospace', self.font_size))
        self.draw_grid()
        print("font size", self.canvas.painter.font().family())
    
    def draw_grid(self, fill=False):
        row_width = self.columns * self.spacing
        column_width = self.rows * self.spacing
        with self.canvas.painter(tools.WHITE_PEN, tools.WHITE_BRUSH):
            for i in range(self.rows + 1):
                self.canvas.painter.drawLine(self.offset_x, self.offset_y + self.spacing * i, self.offset_x + row_width, self.offset_y + i * self.spacing)
            for i in range(self.columns + 1):
                self.canvas.painter.drawLine(self.offset_x + self.spacing * i, self.offset_y + 0, self.offset_x + i * self.spacing, self.offset_y + column_width)
        self.canvas.update()
        if fill:
            for i, j in itertools.product(range(self.rows), range(self.columns)):
                if self.matrix[i][j] == 2:
                    self.mark_rect(i, j, tools.GRAY_BRUSH)
                elif self.matrix[i][j]:
                    self.mark_rect(i, j, tools.WHITE_BRUSH)
                else:
                    x, y = self.get_location(i, j)
                    self.canvas.painter.drawText(QRect(x, y, self.spacing, self.spacing), QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter, f"({i}, {j})")
                # self.canvas.painter.setFont(QFont(''))
    
    def get_indices(self, p: QPoint):
        return (p.y() - self.offset_y) // self.spacing, (p.x() - self.offset_x) // self.spacing
    
    def get_location(self, i, j):
        return self.offset_x + j * self.spacing, self.offset_y + i * self.spacing
    
    def on_mouse_hover(self, e: QtGui.QMouseEvent):
        i, j = self.get_indices(e.pos())
        if self.current_hover and self.current_hover != (i, j):
            last_i, last_j = self.current_hover
            if self.matrix[last_i][last_j] == 2:
                self.mark_rect(last_i, last_j, tools.BLACK_BRUSH)
                self.matrix[last_i][last_j] = 0
        if not 0 <= i < self.rows or not 0 <= j < self.columns:
            return
        if self.matrix[i][j] == 0:
            self.mark_rect(i, j, tools.GRAY_BRUSH)
            self.matrix[i][j] = 2
        self.current_hover = i, j
    
    def mark_rect(self, i, j, brush):
        with self.canvas.painter(tools.WHITE_PEN, brush):
            x, y = self.get_location(i, j)
            self.canvas.painter.drawRect(x, y, self.spacing, self.spacing)
            self.canvas.painter.drawText(QRect(x, y, self.spacing, self.spacing), QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter, f"({i}, {j})")
        self.canvas.update()
    
    def on_mouse_press(self, e: QtGui.QMouseEvent):
        if e.buttons() == QtCore.Qt.RightButton:
            self.last_point = e.pos()
            return
        i, j = self.get_indices(e.pos())
        if not 0 <= i < self.rows or not 0 <= j < self.columns:
            return
        if self.matrix[i][j] == 1:
            self.mark_rect(i, j, tools.BLACK_BRUSH)
            self.matrix[i][j] = 0
        else:
            self.mark_rect(i, j, tools.WHITE_BRUSH)
            self.matrix[i][j] = 1
    
    def on_wheel_move(self, e: QtGui.QWheelEvent):
        steps = e.angleDelta().y() // 120
        factor = self.base_zoom_factor ** abs(steps)
        factor = factor if steps > 0 else 1 / factor
        self.offset_x = int(e.x() + (self.offset_x - e.x()) * factor)
        self.offset_y = int(e.y() + (self.offset_y - e.y()) * factor)
        self.continuos_spacing = self.continuos_spacing * factor
        self.spacing = int(self.continuos_spacing)
        self.font_size = self.font_size * factor
        self.canvas.painter.setFont(QFont('monospace', int(self.font_size)))
        self.clear_canvas()
        self.draw_grid(fill=True)
    
    def clear_canvas(self):
        with self.canvas.painter(tools.BLACK_PEN, tools.BLACK_BRUSH):
            self.canvas.painter.drawRect(0, 0, self.canvas.width(), self.canvas.height())

    def on_resize(self, e: QtGui.QResizeEvent):
        self.clear_canvas()
        self.draw_grid(fill=True)
    
    def on_mouse_right_click_drag(self, e: QtGui.QMouseEvent):
        self.clear_canvas()
        self.offset_x += e.x() - self.last_point.x()
        self.offset_y += e.y() - self.last_point.y()
        self.last_point = e.pos()
        self.draw_grid(fill=True)