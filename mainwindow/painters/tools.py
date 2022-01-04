from typing import Union
from PyQt5 import QtCore, QtGui

WHITE = QtGui.QColor('white')
WHITE_PEN = QtGui.QPen(WHITE)
WHITE_BRUSH = QtGui.QBrush(WHITE, QtCore.Qt.SolidPattern)

BLACK = QtGui.QColor('black')
BLACK_PEN = QtGui.QPen(BLACK)
BLACK_BRUSH = QtGui.QBrush(BLACK, QtCore.Qt.SolidPattern)

BLUE = QtGui.QColor(0x3895d3)
BLUE_PEN = QtGui.QPen(BLUE)
BLUE_BRUSH = QtGui.QBrush(BLUE, QtCore.Qt.SolidPattern)

GRAY = QtGui.QColor('gray')
GRAY_PEN = QtGui.QPen(GRAY)
GRAY_BRUSH = QtGui.QBrush(GRAY, QtCore.Qt.SolidPattern)

def make_pen_and_brush(color: Union[str, int]):
    qcolor = QtGui.QColor(color)
    return QtGui.QPen(qcolor), QtGui.QBrush(qcolor, QtCore.Qt.SolidPattern)