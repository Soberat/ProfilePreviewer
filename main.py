import re
import sys
import os
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QModelIndex
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication, QHBoxLayout, QGroupBox, \
    QFormLayout, QPushButton, QTabWidget, QDoubleSpinBox, QMainWindow, QToolBar, QLineEdit, QFileDialog, QListWidget, \
    QListView, QCheckBox, QErrorMessage
from pyqtgraph import ImageView
from pyqtgraph import opengl as gl
import numpy as np
from Sensor import Sensor, ColormapWorker
from watchdog.observers import Observer
from watchdog.events import RegexMatchingEventHandler


class MainWindow(QMainWindow):

    ready = pyqtSignal(str, str)
    pattern = re.compile('[0-9_]+\\.png')

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ProfilePreviewer")

        self.pathEdit = QLineEdit()
        self.pathEdit.setMinimumWidth(400)
        self.pathEdit.setMaximumWidth(600)
        self.pathEdit.setReadOnly(True)
        self.pathEdit.setText(os.path.dirname(__file__))

        self.pathButton = QPushButton("Wybierz folder")
        self.pathButton.clicked.connect(self.choose_folder)

        self.mainWidget = MainWidget()
        self.mainWidget.fileList.itemSelectionChanged.connect(self.selection_changed)
        self.mainWidget.refreshRequired.connect(self.update_file_list)

        self.observer = Observer()
        self.observer.start()
        self.eventHandler = RegexMatchingEventHandler([".+Sensor[12][0-9_]+\\.png$"], None, True, False)
        self.eventHandler.on_created = self.on_created

        self.setCentralWidget(self.mainWidget)
        self.ready.connect(self.mainWidget.update_image_view)

        self.autoSwitchCheckbox = QCheckBox("Automatycznie wyświetlaj nowe obrazy")

        tb = QToolBar()
        tb.layout().setSpacing(10)
        tb.addWidget(self.pathEdit)
        tb.addWidget(self.pathButton)
        tb.addWidget(self.autoSwitchCheckbox)
        self.addToolBar(tb)
        self.showMaximized()

        self.update_file_list()

        if self.mainWidget.fileList.item(0).text().endswith(".png"):
            self.mainWidget.fileList.setCurrentRow(0)
            self.mainWidget.update_image_view(f"{self.pathEdit.text()}\\Sensor2{self.mainWidget.fileList.item(0).text()}", f"{self.pathEdit.text()}\\Sensor1{self.mainWidget.fileList.item(0).text()}")

    def choose_folder(self):
        folderPath = str(QFileDialog.getExistingDirectory(self, "Wybierz folder do obserwowania", directory=self.pathEdit.text()))
        if len(folderPath) != 0:
            if os.access(folderPath, os.R_OK):
                self.observer.unschedule_all()
                self.pathEdit.setText(folderPath)
                self.observer.schedule(self.eventHandler, folderPath, recursive=False)
                self.update_file_list()
            else:
                self.pathEdit.setText("Brak uprawnień do folderu")

    def on_created(self, event):
        suffix = self.pattern.search(event.src_path)[0]
        fileList = os.listdir(self.pathEdit.text())

        if suffix.startswith('1'):
            firstFileName = "Sensor" + suffix
            secondFileName = "Sensor2" + suffix[1:len(suffix)]
        else:
            firstFileName = "Sensor1" + suffix[1:len(suffix)]
            secondFileName = "Sensor" + suffix

        if firstFileName in fileList and secondFileName in fileList:
            if self.mainWidget.fileList.item(0).text().startswith("Brak"):
                self.mainWidget.fileList.clear()
            self.mainWidget.fileList.addItem(firstFileName.replace("Sensor1", ""))
            if self.autoSwitchCheckbox.isChecked():
                self.mainWidget.fileList.setCurrentRow(self.mainWidget.fileList.count()-1)
                self.ready.emit(self.pathEdit.text() + f"/{secondFileName}", self.pathEdit.text() + f"/{firstFileName}")

    def update_file_list(self):
        # Clear the list of old items
        self.mainWidget.fileList.itemSelectionChanged.disconnect()
        self.mainWidget.fileList.clear()

        # List files in path and those that begin with Sensor1
        files = [file for file in os.listdir(self.pathEdit.text()) if re.match(r"^Sensor[12][_0-9]+.png$", file)]
        onlyS1 = [file for file in files if re.match(r"^Sensor1[_0-9]+.png$", file)]

        for file in onlyS1:
            secondFileName = file.replace("Sensor1", "Sensor2")
            # If a proper pair exists, add only the suffix to the list
            if secondFileName in files:
                self.mainWidget.fileList.addItem(file.replace("Sensor1", ""))

        # If there are no proper pairs of images in the folder, add single item informing the user of that
        if self.mainWidget.fileList.count() == 0:
            self.mainWidget.fileList.addItem("Brak plików w folderze!")
        self.mainWidget.fileList.itemSelectionChanged.connect(self.selection_changed)

    def selection_changed(self):
        if self.mainWidget.fileList.currentItem().text().endswith(".png"):
            self.mainWidget.update_image_view(f"{self.pathEdit.text()}/Sensor2{self.mainWidget.fileList.currentItem().text()}",
                                              f"{self.pathEdit.text()}/Sensor1{self.mainWidget.fileList.currentItem().text()}")


class MainWidget(QWidget):
    SCALE = 0.5
    POINT_SIZE = 0.1
    Y_STEP = 1

    refreshRequired = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.sensor1XOffsetSpinbox = QDoubleSpinBox()
        self.sensor1XOffsetSpinbox.setRange(-1000, 1000)
        self.sensor1XOffsetSpinbox.setSuffix(" mm")
        self.sensor1XOffsetSpinbox.valueChanged.connect(self.update_sensor1_values)

        self.sensor1YOffsetSpinbox = QDoubleSpinBox()
        self.sensor1YOffsetSpinbox.setRange(-1000, 1000)
        self.sensor1YOffsetSpinbox.setSuffix(" mm")
        self.sensor1YOffsetSpinbox.valueChanged.connect(self.update_sensor1_values)

        self.sensor1ZOffsetSpinbox = QDoubleSpinBox()
        self.sensor1ZOffsetSpinbox.setRange(-1000, 1000)
        self.sensor1ZOffsetSpinbox.setSuffix(" mm")
        self.sensor1ZOffsetSpinbox.valueChanged.connect(self.update_sensor1_values)

        self.sensor1XAngleSpinbox = QDoubleSpinBox()
        self.sensor1XAngleSpinbox.setRange(-180, 180)
        self.sensor1XAngleSpinbox.setSuffix(" °")
        self.sensor1XAngleSpinbox.valueChanged.connect(self.update_sensor1_values)

        self.sensor1YAngleSpinbox = QDoubleSpinBox()
        self.sensor1YAngleSpinbox.setRange(-180, 180)
        self.sensor1YAngleSpinbox.setSuffix(" °")
        self.sensor1YAngleSpinbox.valueChanged.connect(self.update_sensor1_values)

        self.sensor1ZAngleSpinbox = QDoubleSpinBox()
        self.sensor1ZAngleSpinbox.setRange(-180, 180)
        self.sensor1ZAngleSpinbox.setSuffix(" °")
        self.sensor1ZAngleSpinbox.valueChanged.connect(self.update_sensor1_values)

        self.sensor1ResetButton = QPushButton("Reset")
        self.sensor1ResetButton.clicked.connect(self.reset_sensor1_values)
        self.sensor1ApplyButton = QPushButton("Zastosuj")
        self.sensor1ApplyButton.clicked.connect(self.apply_sensor1_values)
        self.sensor1ApplyButton.setEnabled(False)

        self.sensor2XOffsetSpinbox = QDoubleSpinBox()
        self.sensor2XOffsetSpinbox.setRange(-1000, 1000)
        self.sensor2XOffsetSpinbox.setSuffix(" mm")
        self.sensor2XOffsetSpinbox.valueChanged.connect(self.update_sensor2_values)

        self.sensor2YOffsetSpinbox = QDoubleSpinBox()
        self.sensor2YOffsetSpinbox.setRange(-1000, 1000)
        self.sensor2YOffsetSpinbox.setSuffix(" mm")
        self.sensor2YOffsetSpinbox.valueChanged.connect(self.update_sensor2_values)

        self.sensor2ZOffsetSpinbox = QDoubleSpinBox()
        self.sensor2ZOffsetSpinbox.setRange(-1000, 1000)
        self.sensor2ZOffsetSpinbox.setSuffix(" mm")
        self.sensor2ZOffsetSpinbox.valueChanged.connect(self.update_sensor2_values)

        self.sensor2XAngleSpinbox = QDoubleSpinBox()
        self.sensor2XAngleSpinbox.setRange(-180, 180)
        self.sensor2XAngleSpinbox.setSuffix(" °")
        self.sensor2XAngleSpinbox.valueChanged.connect(self.update_sensor2_values)

        self.sensor2YAngleSpinbox = QDoubleSpinBox()
        self.sensor2YAngleSpinbox.setRange(-180, 180)
        self.sensor2YAngleSpinbox.setSuffix(" °")
        self.sensor2YAngleSpinbox.valueChanged.connect(self.update_sensor2_values)

        self.sensor2ZAngleSpinbox = QDoubleSpinBox()
        self.sensor2ZAngleSpinbox.setRange(-180, 180)
        self.sensor2ZAngleSpinbox.setSuffix(" °")
        self.sensor2ZAngleSpinbox.valueChanged.connect(self.update_sensor2_values)

        self.sensor2ResetButton = QPushButton("Reset")
        self.sensor2ResetButton.clicked.connect(self.reset_sensor2_values)
        self.sensor2ApplyButton = QPushButton("Zastosuj")
        self.sensor2ApplyButton.clicked.connect(self.apply_sensor2_values)
        self.sensor2ApplyButton.setEnabled(False)

        self.fileList = QListWidget()

        self.tabs = QTabWidget()

        self.imageView = ImageView()
        self.imageView.setPredefinedGradient('viridis')
        self.hostView = gl.GLViewWidget()
        self.view1 = gl.GLScatterPlotItem(size=self.POINT_SIZE, pxMode=False)
        self.view2 = gl.GLScatterPlotItem(size=self.POINT_SIZE, pxMode=False)

        self.s1 = Sensor("Sensor1", isOffset=True)
        self.s2 = Sensor("Sensor2")

        masterLayout = QHBoxLayout()
        masterLayout.addLayout(self.create_left_column())
        masterLayout.addWidget(self.create_image_view())
        self.setLayout(masterLayout)

    def create_left_column(self):
        COLUMN_WIDTH = 250

        masterLayout = QVBoxLayout()
        groupR = QGroupBox("Sensor 1 (Lewy)")

        layout = QFormLayout()
        layout.addRow(QLabel("X"), self.sensor1XOffsetSpinbox)
        layout.addRow(QLabel("Y"), self.sensor1YOffsetSpinbox)
        layout.addRow(QLabel("Z"), self.sensor1ZOffsetSpinbox)

        layout.addRow(QLabel("Kąt X"), self.sensor1XAngleSpinbox)
        layout.addRow(QLabel("Kąt Y"), self.sensor1YAngleSpinbox)
        layout.addRow(QLabel("Kąt Z"), self.sensor1ZAngleSpinbox)
        layout.addRow(self.sensor1ResetButton, self.sensor1ApplyButton)

        groupR.setLayout(layout)
        groupR.setMaximumSize(COLUMN_WIDTH, 300)
        masterLayout.addWidget(groupR, alignment=Qt.AlignTop)

        groupL = QGroupBox("Sensor 2 (Prawy)")

        layout = QFormLayout()
        layout.addRow(QLabel("X"), self.sensor2XOffsetSpinbox)
        layout.addRow(QLabel("Y"), self.sensor2YOffsetSpinbox)
        layout.addRow(QLabel("Z"), self.sensor2ZOffsetSpinbox)

        layout.addRow(QLabel("Kąt X"), self.sensor2XAngleSpinbox)
        layout.addRow(QLabel("Kąt Y"), self.sensor2YAngleSpinbox)
        layout.addRow(QLabel("Kąt Z"), self.sensor2ZAngleSpinbox)
        layout.addRow(self.sensor2ResetButton, self.sensor2ApplyButton)

        groupL.setLayout(layout)
        groupL.setMaximumSize(COLUMN_WIDTH, 300)
        masterLayout.addWidget(groupL, alignment=Qt.AlignTop)

        groupCam = QGroupBox("Sterowanie widokiem 3D")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b> Lewy p/m</b> - obrót"))
        layout.addWidget(QLabel("<b> Środkowy p/m</b> - przesunięcie X/Y"))
        layout.addWidget(QLabel("<b> Ctrl + Lewy p/m</b> - przesunięcie Z"))
        layout.addWidget(QLabel("<b> Rolka</b> - zoom"))
        layout.addWidget(QLabel("<b> Ctrl + Rolka</b> - zmiana pola widzenia"))

        groupCam.setLayout(layout)
        groupCam.setMaximumWidth(COLUMN_WIDTH)
        masterLayout.addWidget(groupCam, alignment=Qt.AlignTop)

        groupList = QGroupBox("Pary plików w folderze")
        layout = QVBoxLayout()
        self.fileList.setMinimumHeight(250)
        self.fileList.setSelectionMode(QListView.SingleSelection)
        self.fileList.setResizeMode(QListView.Adjust)
        self.fileList.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.fileList)
        groupList.setLayout(layout)
        groupList.setMaximumWidth(COLUMN_WIDTH)
        masterLayout.addWidget(groupList, alignment=Qt.AlignTop)

        masterLayout.setStretch(3, 100)

        return masterLayout

    def create_image_view(self):
        layout = QVBoxLayout()
        layout.addWidget(self.imageView)

        self.tabs.addTab(self.imageView, "Widok 2D")

        # 3D Tab
        layout = QVBoxLayout()

        self.view1.setGLOptions('opaque')
        self.view1.scale(self.SCALE, self.SCALE, self.SCALE)
        self.hostView.addItem(self.view1)

        self.view2.setGLOptions('opaque')
        self.view2.scale(self.SCALE, self.SCALE, self.SCALE)
        self.hostView.addItem(self.view2)

        self.hostView.pan(dx=0, dy=100 * self.Y_STEP * self.SCALE, dz=0)
        self.hostView.orbit(225, 180)

        layout.addWidget(self.hostView)
        self.tabs.addTab(self.hostView, "Widok 3D")

        self.tabs.currentChanged.connect(self.tab_change_handler)

        return self.tabs

    def tab_change_handler(self):
        if self.tabs.currentIndex() == 0:
            self.sensor1ApplyButton.setEnabled(False)
            self.sensor2ApplyButton.setEnabled(False)

        if self.tabs.currentIndex() == 1:
            self.sensor1ApplyButton.setEnabled(True)
            self.sensor2ApplyButton.setEnabled(True)
            if not self.s1.processed3d or not self.s2.processed3d:
                self.s1.process_image3d()
                self.s2.process_image3d()
                self.apply_sensor1_values()
                self.apply_sensor2_values()

    def update_image_view(self, im1: str, im2: str):
        try:
            self.s1.open_image(im1)
            self.s2.open_image(im2)
        except FileNotFoundError as fnfe:
            dialog = QErrorMessage()
            dialog.showMessage(str(fnfe))
            dialog.exec_()
            self.refreshRequired.emit()

        maxVal = np.max((np.max(self.s1.imageArray), np.max(self.s2.imageArray)))
        self.s1.maxVal = maxVal
        self.s2.maxVal = maxVal

        self.s1.process_image2d()
        self.s2.process_image2d()

        if self.tabs.currentIndex() == 1:
            self.s1.process_image3d()
            self.s2.process_image3d()

        self.imageView.setImage(np.concatenate((self.s1.imageArray, self.s2.imageArray)))

        # Delete previous 3D data
        self.view1.setData(pos=None, color=None)
        self.view2.setData(pos=None, color=None)

        if self.tabs.currentIndex() == 1:
            self.apply_sensor1_values()
            self.apply_sensor2_values()

    def update_sensor1_values(self):
        self.s1.xOffset = self.sensor1XOffsetSpinbox.value()
        self.s1.yOffset = self.sensor1YOffsetSpinbox.value()
        self.s1.zOffset = self.sensor1ZOffsetSpinbox.value()

        self.s1.xAngle = self.sensor1XAngleSpinbox.value()
        self.s1.yAngle = self.sensor1YAngleSpinbox.value()
        self.s1.zAngle = self.sensor1ZAngleSpinbox.value()

    def update_sensor2_values(self):
        self.s2.xOffset = self.sensor2XOffsetSpinbox.value()
        self.s2.yOffset = self.sensor2YOffsetSpinbox.value()
        self.s2.zOffset = self.sensor2ZOffsetSpinbox.value()

        self.s2.xAngle = self.sensor2XAngleSpinbox.value()
        self.s2.yAngle = self.sensor2YAngleSpinbox.value()
        self.s2.zAngle = self.sensor2ZAngleSpinbox.value()

    def reset_sensor1_values(self):
        self.s1.xOffset = 0.0
        self.s1.yOffset = 0.0
        self.s1.zOffset = 0.0
        self.s1.xAngle = 0.0
        self.s1.yAngle = 0.0
        self.s1.zAngle = 0.0

        self.sensor1XOffsetSpinbox.setValue(0.0)
        self.sensor1YOffsetSpinbox.setValue(0.0)
        self.sensor1ZOffsetSpinbox.setValue(0.0)
        self.sensor1XAngleSpinbox.setValue(0.0)
        self.sensor1YAngleSpinbox.setValue(0.0)
        self.sensor1ZAngleSpinbox.setValue(0.0)

    def reset_sensor2_values(self):
        self.s2.xOffset = 0.0
        self.s2.yOffset = 0.0
        self.s2.zOffset = 0.0
        self.s2.xAngle = 0.0
        self.s2.yAngle = 0.0
        self.s2.zAngle = 0.0

        self.sensor2XOffsetSpinbox.setValue(0.0)
        self.sensor2YOffsetSpinbox.setValue(0.0)
        self.sensor2ZOffsetSpinbox.setValue(0.0)
        self.sensor2XAngleSpinbox.setValue(0.0)
        self.sensor2YAngleSpinbox.setValue(0.0)
        self.sensor2ZAngleSpinbox.setValue(0.0)

    def save_colormap1(self, colormap):
        self.s1.colormap = colormap

    def save_colormap2(self, colormap):
        self.s2.colormap = colormap

    def apply_sensor1_values(self):
        self.s1.transform()
        self.thread1 = QThread()
        self.worker1 = ColormapWorker(self.s1.pointsArray)
        self.worker1.moveToThread(self.thread1)
        self.thread1.started.connect(self.worker1.generate_colormap)
        self.worker1.finished.connect(self.save_colormap1)
        self.worker1.finished.connect(lambda: self.view1.setData(pos=self.s1.pointsArray, color=self.s1.colormap))
        self.worker1.finished.connect(self.thread1.quit)
        self.worker1.finished.connect(self.worker1.deleteLater)
        self.thread1.finished.connect(self.thread1.deleteLater)
        self.thread1.start()

    def apply_sensor2_values(self):
        self.s2.transform()
        self.thread2 = QThread()
        self.worker2 = ColormapWorker(self.s2.pointsArray)
        self.worker2.moveToThread(self.thread2)
        self.thread2.started.connect(self.worker2.generate_colormap)
        self.worker2.finished.connect(self.save_colormap2)
        self.worker2.finished.connect(lambda: self.view2.setData(pos=self.s2.pointsArray, color=self.s2.colormap))
        self.worker2.finished.connect(self.thread2.quit)
        self.worker2.finished.connect(self.worker2.deleteLater)
        self.thread2.finished.connect(self.thread2.deleteLater)
        self.thread2.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
