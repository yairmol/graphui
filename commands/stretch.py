from commandbar.api import cmdutils
from mainwindow import MainWindow

@cmdutils.register(name='calc-stretch', instance='main-window', scope='window', maxsplit=0)
def calculate_stretch(self: MainWindow):
    if len(self.graph_views) <= 1:
        print("unable to calculate")

class StretchCalcution:

    @cmdutils.register(instance='stretch-calculator', name='next-pair', scope='window')
    def next_pair(self):
        pass