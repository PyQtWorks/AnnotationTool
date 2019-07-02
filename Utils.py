import numpy as np
import skimage.io
import sys
import torch
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtWidgets import (QApplication, QCheckBox, QGridLayout, QGroupBox,
                             QMenu, QPushButton, QRadioButton, QVBoxLayout, QWidget, QSlider, QLabel, QRubberBand)
from PyQt5.QtGui import QIcon, QPixmap

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QImage, QPalette, QBrush, QPainter, QColor, QPen
from PyQt5.QtWidgets import *
import skimage.transform

def toQImage(im, copy=False):
    if im is None:
        return QImage()

    im = np.ascontiguousarray(im, dtype=np.uint8)
    # assert im.shape[2] <= 4, 'Weird image shape detected : {}'.format(im.shape)
    
    if len(im.shape) == 2:
        qim = QImage(im.data, im.shape[1], im.shape[0],
                     im.strides[0], QImage.Format_Indexed8)
        qim.setColorTable(gray_color_table)
        return qim.copy() if copy else qim
    elif len(im.shape) == 3:
        if im.shape[2] == 3:
            qim = QImage(
                im.data, im.shape[1], im.shape[0], im.strides[0], QImage.Format_RGB888)
            return qim.copy() if copy else qim
        elif im.shape[2] == 4:
            qim = QImage(
                im.data, im.shape[1], im.shape[0], im.strides[0], QImage.Format_ARGB32)
            return qim.copy() if copy else qim


def rect_info(rect:QRect, scale=1):
    return rect.x() * scale, rect.y()* scale, rect.width() * scale, rect.height() * scale