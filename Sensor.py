import time

import PIL.Image
import numpy as np
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot
from scipy.ndimage import median_filter
from scipy.spatial.transform import Rotation


class ColormapWorker(QObject):

    finished = pyqtSignal(np.ndarray)

    def __init__(self, pointsArray):
        super().__init__()
        self.pointsArray = pointsArray

    @pyqtSlot()
    def generate_colormap(self):
        colors = np.empty((np.shape(self.pointsArray)[0], 4))
        maxZ = np.max(self.pointsArray[:, 2])
        maxY = np.max(self.pointsArray[:, 1])
        norm = np.exp(0.04 * (self.pointsArray[:, 2] - maxZ))
        normY = self.pointsArray[:, 1] / maxY
        for i in range(np.shape(colors)[0]):
            val = norm[i]
            colors[i] = (1 - val, val, normY[i], 0.5)

        self.finished.emit(colors)


class Sensor:
    xStep = 0.219
    yStep = 1
    zStep = 0.006

    def __init__(self, prefix, isOffset=False):
        super().__init__()
        self.prefix: str = prefix
        self.maxVal: float = 0.0
        self.xOffset: float = 0.0
        self.yOffset: float = 0.0
        self.zOffset: float = 0.0
        self.xAngle: float = 0.0
        self.yAngle: float = 0.0
        self.zAngle: float = 0.0
        self.imageArray = None
        self.unprocessedPointsArray = None
        self.pointsArray = None
        self.colormap = None
        self.isOffset = isOffset
        self.processed3d = False

    def open_image(self, path: str):
        self.processed3d = False
        self.imageArray = np.asarray(PIL.Image.open(path).transpose(PIL.Image.ROTATE_270))

    def process_image2d(self):
        self.imageArray[self.imageArray == 0] = self.maxVal
        self.imageArray = self.imageArray * -self.zStep
        self.imageArray = median_filter(self.imageArray, size=5)

    def process_image3d(self):
        shape = np.shape(self.imageArray)
        x = np.linspace(0, shape[0], shape[0]) * self.xStep
        y = np.linspace(0, shape[1], shape[1]) * self.yStep

        self.pointsArray = np.zeros((shape[0] * shape[1], 3))
        self.pointsArray[:, 0] = np.repeat(x, shape[1])
        self.pointsArray[:, 1] = np.tile(y, shape[0])
        self.pointsArray[:, 2] = np.reshape(self.imageArray, (shape[0]*shape[1]))

        yOffset = np.max(self.pointsArray[:, 1])
        zOffset = np.mean(self.pointsArray[np.where((self.pointsArray[:, 1] == np.max(self.pointsArray[:, 1]))), 2])
        self.pointsArray[:, 1] = -(self.pointsArray[:, 1] - yOffset)
        self.pointsArray[:, 2] = self.pointsArray[:, 2] - zOffset

        if self.isOffset:
            self.pointsArray[:, 0] -= np.max(self.pointsArray[:, 0])

        self.unprocessedPointsArray = self.pointsArray.copy()

        self.transform()
        self.processed3d = True

    def transform(self):
        self.pointsArray = self.unprocessedPointsArray.copy()
        if self.xAngle != 0.0:
            rx = Rotation.from_euler('x', self.xAngle, degrees=True)
            self.pointsArray = rx.apply(self.pointsArray)

        if self.yAngle != 0.0 or self.zAngle != 0.0:
            ryz = Rotation.from_euler('yz', [self.yAngle, self.zAngle], degrees=True)
            meanX = np.mean(self.pointsArray[:, 0])
            self.pointsArray[:, 0] = self.pointsArray[:, 0] - meanX
            self.pointsArray = ryz.apply(self.pointsArray)
            self.pointsArray[:, 0] = self.pointsArray[:, 0] + meanX

        self.pointsArray[:, 0] += self.xOffset
        self.pointsArray[:, 1] += self.yOffset
        self.pointsArray[:, 2] += self.zOffset

