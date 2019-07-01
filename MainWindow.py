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
import cv2

class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fs = Ui_Dialog()
        self.fs.setupUi(self)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.fs.MainView.view.set_image(cv2.imread('data/img.jpg')[..., ::-1])

    mw.show()
    sys.exit(app.exec_())

    pass

