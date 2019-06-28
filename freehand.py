import logging as log
import sys
from copy import copy
import os
import pathlib

import matplotlib.pyplot as plt
import numpy as np
import skimage.draw as Draw
import skimage.io
import skimage.transform
import torch
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from skimage.transform import resize

from freehandTool.freehand import FreehandTool
# from freehandTool.ghostLine import PointerTrackGhost
from freehandTool.freehandHead import PointerTrackGhost
from freehandTool.pointerEvent import PointerEvent
from freehandTool.segmentString.segmentString import SegmentString
from Utils import toQImage
from PyQt5.QtWidgets import QColorDialog
width, height = 500, 500


class FreeHandSlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.scene = DiagramScene(0, 0, width, height, self)
        self.view = FreeHandView(self.scene)
        self.view.setFixedSize(width, height)
        self.view.setSceneRect(-width, -height, width, height)
        # self.view.fitInView(-width, -height, width, height, Qt.KeepAspectRatio)
        layout.addWidget(self.view)
        self.picker_radius = 20
        self.picker = self.scene.addEllipse(QRectF(0, 0, self.picker_radius, self.picker_radius), QPen(Qt.red), QBrush(Qt.green))
        self.picker.setEnabled(False)
        self.view.global_image_update_signal.connect(self.hide_picker)
        self.view.hide_picker_signal.connect(self.hide_picker)


    def show_picker(self, y, x):
        self.picker.setEnabled(True)
        self.picker.setRect(QRectF(x, y, self.picker_radius, self.picker_radius))

    def hide_picker(self):
        self.picker.setEnabled(False)

    

class DiagramScene(QGraphicsScene):
    def __init__(self, *args):
        QGraphicsScene.__init__(self, *args)

        # self.addItem(QGraphicsTextItem("Freehand drawing with pointer"))


class FreeHandView(QGraphicsView):
    '''
    Slot that contains the actual image
    '''
    global_image_update_signal = pyqtSignal(int, int)
    hide_picker_signal = pyqtSignal()
    mode_signal = pyqtSignal(str, str)
    reset_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = 'paint'
        self.paint_related_operations = ['paint', 'eraser', 'keep']
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_size = width
        # self.mask = torch.zeros(1024, self.image.shape[1])
        # self.set_image(np.ones([width, height,3],dtype=np.uint8) * 255)

        # self.baseImageChangedCallbacks = []
        # self.base_image = None
        self.mask = None
        self.image = None
        assert self.dragMode() == QGraphicsView.NoDrag
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        """Stores all points currently drawing"""
        self.isMousePressed = False
        self.draw_color = np.array([255,255,255], dtype=np.uint8)
        self.isLocalEditted = False
        self.brushSize = 20


    def reset(self):
        self.mask = torch.zeros(self.image.shape[0], self.image.shape[1])
        self.refresh()
        self.isLocalEditted = False
        self.reset_signal.emit()
        log.debug('Reset FHS')

    def set_mode(self, mode):
        log.info(f'Selecting Mode : {mode}')
        self.mode_signal.emit(self.mode, mode)
        if mode != 'pick':
            self.hide_picker_signal.emit()
        self.mode = mode
        self.refresh()

    def save_image(self, path):
        log.info(f'Saving current img @ {path}')
        skimage.io.imsave(path, self.image.astype(np.uint8))

    def mouseMoveEvent(self, event):
        if self.isMousePressed is True:
            x, y = event.x(), event.y()
            if self.isLocalEditted:
                rr, cc = Draw.circle(
                    y * self.image.shape[0] // self.image_size, x * self.image.shape[1] // self.image_size, self.brushSize, self.mask.shape)
                if self.mask is None:
                    return
                    # self.mask = torch.zeros(*self.image.shape[:2])
                # rr[rr>self.image.shape[0]-1] = self.image.shape[0]-1
                # cc[cc>self.image.shape[0]-1] = self.image.shape[0]-1
                if self.mode == 'paint':
                    self.mask[rr,cc] = 1
                    self.image[rr,cc,:] = self.draw_color
                elif self.mode == 'eraser':
                    self.mask[rr,cc] = -1    
                    self.image[rr,cc,:] = np.array([255, 255, 255])
                elif self.mode == 'keep':
                    self.mask[rr,cc] = 2
                    self.image[rr,cc,0] = 255
                self.refresh()
            elif self.mode == 'pick':
                self.global_image_update_signal.emit(y, x)



    def mousePressEvent(self, event):
        '''
        On mouse button down, create a new (infinitesmal) SegmentString and PointerTrackGhost.
        freehandTool remembers and updates SegmentString.
        '''
        if event.button() == Qt.LeftButton:
            self.isMousePressed = True
            x, y = event.x(), event.y()
            if self.mode in self.paint_related_operations:
                if self.mask is None: 
                    self.mask = torch.zeros(*self.image.shape[:2])
                rr, cc = Draw.circle(
                    y * self.image.shape[0] // self.image_size, x * self.image.shape[1] // self.image_size, self.brushSize, self.mask.shape)
                # rr[rr>self.image.shape[0]-1] = self.image.shape[0]-1
                # cc[cc>self.image.shape[0]-1] = self.image.shape[0]-1
                if self.mode == 'paint':
                    self.mask[rr,cc] = 1
                    self.image[rr,cc,:] = self.draw_color
                elif self.mode == 'eraser':
                    self.mask[rr,cc] = -1
                    self.image[rr,cc,:] = np.array([255, 255, 255])
                elif self.mode == 'keep':
                    self.mask[rr,cc] = 2
                    self.image[rr,cc,0] = 255                        
                self.isLocalEditted = True
            elif self.mode == 'pick':
                self.reset()
                self.isLocalEditted = False
                self.global_image_update_signal.emit(y, x)


        elif event.button() == 4:
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            folder = self.parent().parent().parent().iter_folder
            fileName, _ = QFileDialog.getSaveFileName(self,"Save Current Image",f"{str(folder)}","All Files (*);;Image Files (*.jpg)", options=options)
            if not fileName.endswith('.jpg'):
                fileName += '.jpg'
            self.save_image(fileName)


    def set_paint_color(self):
        color = QColorDialog.getColor()
        rgb = color.getRgb()
        self.draw_color = np.array(rgb[:-1])
        log.info(f'Set New color {self.draw_color}')

    def keyPressEvent(self, event):
        key = event.key()
        if key == 87:#'w'
            self.set_mode('paint')
        elif key == 69: #'e'
            self.set_paint_color()
        elif key == 83: #'s'
            folder = self.parent().parent().parent().iter_folder
            i = 0
            while folder.joinpath(f'I_{i}.jpg').exists():
                i += 1
            path_string = str(folder.joinpath(f'I_{i}.jpg'))
            self.save_image(path_string)
            log.info(f"Saved Image @ {path_string}")

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.isMousePressed = False

        self.refresh()

    def refresh(self):
        self.set_image(self.image)
        self.repaint()

    def set_image(self, img):
        # if self.mask is not None:
        #     img = self.image * (1 - self.mask).unsqueeze(-1) + \
        #         img * self.mask.unsqueeze(-1)
        #     img = img.numpy()

        self.image = img.copy()
        if self.mask is None:
            self.mask = torch.zeros(self.image.shape[0], self.image.shape[1])
        oImage = toQImage(self.image)
        sImage = oImage.scaled(QSize(self.image_size, self.image_size))
        self.pixmap_image = QPixmap.fromImage(sImage)
        # self.setPixmap(self.pixmap_image)
        if not hasattr(self, 'item'):
            self.item = QGraphicsPixmapItem(self.pixmap_image)
            self.item.setOffset(-self.image_size, -self.image_size)
            self.item.setPos(0, 0)
            self.scene().addItem(self.item)
            self.repaint()
        else:
            self.item.setPixmap(self.pixmap_image)


    # def baseImageChanged(self, image):
    #     for callback in self.baseImageChangedCallbacks:
    #         callback(image)
