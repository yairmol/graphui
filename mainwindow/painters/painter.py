
from typing import Optional
from PyQt5.QtGui import QBrush, QPaintDevice, QPainter, QPen


class CustomPainter(QPainter):
    def __init__(self, pd: QPaintDevice):
        super().__init__(pd)
    
    def set(self, pen=None, brush=None):
        if pen:
            self.setPen(pen)
        if brush:
            self.setBrush(brush)
    
    def __call__(self, pen: Optional[QPen] = None, brush: Optional[QBrush] = None):
        self.set(pen, brush)
        return self
    
    def __enter__(self):
        pass

    def __exit__(self, *args, **kwargs) -> None:
        pass