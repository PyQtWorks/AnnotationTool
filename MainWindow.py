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
        self.fs.eraseButton.clicked.connect(lambda: self.fs.MainView.view.set_mode('eraser'))
        self.fs.paintButton.clicked.connect(lambda: self.fs.MainView.view.set_mode('paint'))
        self.fs.erasep.clicked.connect(lambda: self.fs.MainView.view.change_brush_size('erase', 10))
        self.fs.erasem.clicked.connect(lambda: self.fs.MainView.view.change_brush_size('erase', -10))
        self.fs.paintp.clicked.connect(lambda: self.fs.MainView.view.change_brush_size('paint', 10))
        self.fs.paintm.clicked.connect(lambda: self.fs.MainView.view.change_brush_size('paint', -10))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = MainWindow()
    img = cv2.imread('data/img.jpg')[..., ::-1]
    height, width, _ = img.shape
    size = min(height, width)
    img = img[:size, :size]
    from skimage.transform import resize
    size = mw.fs.MainView.view.image_size
    img = resize(img, (size, size), preserve_range=True)
    mw.fs.MainView.view.set_image(img)

    mw.show()
    sys.exit(app.exec_())

    pass

