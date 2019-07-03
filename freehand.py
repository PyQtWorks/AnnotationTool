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
import cv2

width, height = 500, 500


class FreeHandSlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.scene = DiagramScene(0, 0, width, height, self)
        self.view = FreeHandView(self, self.scene)
        self.view.setFixedSize(width, height)
        self.view.setSceneRect(-width, -height, width, height)
        # self.view.fitInView(-width, -height, width, height, Qt.KeepAspectRatio)
        layout.addWidget(self.view)
        self.picker_radius = 20
        self.picker = self.scene.addEllipse(QRectF(0, 0, self.picker_radius, self.picker_radius), QPen(Qt.red), QBrush(Qt.green))
        self.picker.setEnabled(False)
        self.update_cursor()

    def update_cursor(self):
        size = self.view.brushSize
        rr, cc = Draw.circle(
            size, size, size, [size*2, size*2])
        cursor_img = np.ones([size*2, size*2, 3],dtype=np.uint8) * 200
        if self.view.mode == 'paint':
            cursor_img[..., 1:] = 0
        cursor_mask = np.ones([size*2, size*2], np.uint8) * 255
        cursor_mask[rr, cc] = 0
        qi = toQImage(cursor_img)
        Qp = QPixmap.fromImage(qi)
        qimage_mask = QImage(cursor_mask, size*2, size*2, QImage.Format_Grayscale8)
        qb = QBitmap(qimage_mask)
        Qp.setMask(qb)
        self.view.setCursor(QCursor(Qp))

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
    gw = None
    _center = None
    def __init__(self, slot, parent=None):
        super().__init__(parent)
        self.mode = 'paint'
        self.slot = slot
        self.paint_related_operations = ['paint', 'eraser']
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_size = width
        self.mask = None
        self.image = None
        assert self.dragMode() == QGraphicsView.NoDrag
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        """Stores all points currently drawing"""
        self.isMousePressed = False
        self.draw_color = np.array([255,255,255], dtype=np.uint8)
        self.isLocalEditted = False
        self.paint_bs = 20
        self.erase_bs = 20
        self.scale = 1.0
        self.speed = np.array([0, 0, 0, 0], dtype=np.uint8)
    
    def zoom(self, scale_delta):
        self.scale += scale_delta
        self.scale = min(max(self.scale, 1), 2)
        self.set_image()
        self.slot.update_cursor()

    @property
    def brushSize(self):
        if self.mode == 'paint':
            return self.paint_bs
        return self.erase_bs
        
    def change_brush_size(self, name, value):
        bs = getattr(self, f'{name}_bs')
        setattr(self, f'{name}_bs', bs + value)
        self.slot.update_cursor()

    def reset(self):
        self.mask = np.zeros(self.image.shape[0], self.image.shape[1])
        self.refresh()
        self.isLocalEditted = False
        self.reset_signal.emit()
        log.debug('Reset FHS')

    def set_mode(self, mode):
        log.info(f'Selecting Mode : {mode}')
        # self.mode_signal.emit(self.mode, mode)
        self.mode = mode
        self.slot.update_cursor()
        self.refresh()

    def save_image(self, path):
        log.info(f'Saving current img @ {path}')
        skimage.io.imsave(path, self.image.astype(np.uint8))

    def mouseMoveEvent(self, event):
        should_refresh = False
        x, y = event.x(), event.y()

        if y < 0.1:
            should_refresh = True
            self.speed[0] = 5
        elif y > 0.9:
            should_refresh = True
            self.speed[2] = 5
        elif x < 0.1:
            should_refresh = True
            self.speed[1] = 5
        elif x > 0.9:
            should_refresh = True
            self.speed[3] = 5
        else:
            self.speed[:] = 0

        if self.isMousePressed is True:
            should_refresh = True
            brushSize = self.brushSize / self.scale
            rr, cc = Draw.circle(
                y * self.side // self.image_size + self.y0, x * self.side // self.image_size + self.x0, brushSize, self.mask.shape)
            if self.mask is None:
                print('Moving but mask is None')
                return
            if self.mode == 'paint':
                self.mask[rr,cc] = 0.5
            elif self.mode == 'eraser':
                self.mask[rr,cc] = 0
            
        if should_refresh:
            self.refresh()

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
                    self.mask = np.zeros(*self.image.shape[:2])
                brushSize = self.brushSize / self.scale
                rr, cc = Draw.circle(
                    y * self.side // self.image_size + self.y0, x * self.side // self.image_size + self.x0, brushSize, self.mask.shape)
                if self.mode == 'paint':
                    self.mask[rr,cc] = 0.5
                elif self.mode == 'eraser':
                    self.mask[rr,cc] = 0
                self.refresh()

        elif event.button() == 4:
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            folder = self.parent().parent().parent().iter_folder
            fileName, _ = QFileDialog.getSaveFileName(self,"Save Current Image",f"{str(folder)}","All Files (*);;Image Files (*.jpg)", options=options)
            if not fileName.endswith('.jpg'):
                fileName += '.jpg'
            self.save_image(fileName)

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
        self._center[0] += self.speed[0] - self.speed[2] 
        self._center[1] += self.speed[1] - self.speed[3] 
        self.set_image()
        self.repaint()
    
    @property
    def bound(self):
        return int(self.image_size / self.scale / 2)

    @property
    def side(self):
        return self.bound*2

    @property
    def center(self):
        self._center[0] = max(min(self._center[0], self.image_size - self.bound), self.bound)
        self._center[1] = max(min(self._center[1], self.image_size - self.bound), self.bound)
        return self._center
    
    @property
    def y0(self):
        return self.center[0] - self.bound

    @property
    def x0(self):
        return self.center[1] - self.bound

    @property
    def y1(self):
        return self.y0 + self.side

    @property
    def x1(self):
        return self.x0 + self.side


    def set_image(self, img=None): 
        if img is not None:
            self.image = img.copy()
            self._center = np.array([img.shape[0]/2, img.shape[1]/2], np.uint8)
        color = np.zeros_like(self.image)
        color[..., 0] = 255
        if self.mask is None:
            self.mask = np.zeros((self.image.shape[0], self.image.shape[1]))[..., None]
    
        _img = self.image * (1-self.mask) + color * self.mask
        if self.gw is not None:
            size = 300
            gw_img = _img.copy()
            cv2.rectangle(gw_img, (self.x0, self.y0), (self.x1, self.y1), [255, 0, 255], 5)
            oImage = toQImage(gw_img)
            self.gw.pixmap_image = QPixmap.fromImage(oImage.scaled(QSize(size, size)))
            self.gw.setPixmap(self.gw.pixmap_image)

        _img = _img[self.y0: self.y1, self.x0: self.x1]
        oImage = toQImage(_img)
        sImage = oImage.scaled(QSize(self.image_size, self.image_size))
        self.pixmap_image = QPixmap.fromImage(sImage)
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
