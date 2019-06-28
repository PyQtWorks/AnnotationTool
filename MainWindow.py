from UI import Ui_Dialog
from PyQt5.QtCore import QPoint, QRect, QSize, Qt
from PyQt5.QtGui import (QBrush, QColor, QIcon, QImage, QPainter, QPalette,
                         QPen, QPixmap)
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import (QApplication, QCheckBox, QGridLayout, QGroupBox,
                             QLabel, QMenu, QPushButton, QRadioButton,
                             QRubberBand, QSlider, QTabWidget, QVBoxLayout,
                             QWidget)
import sys

class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        fs = Ui_Dialog()
        fs.setupUi(self)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())

    pass

