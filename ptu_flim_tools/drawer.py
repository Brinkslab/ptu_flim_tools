import math
import pathlib

from PyQt6 import QtWidgets, QtCore, QtGui
import numpy as np
import tifffile


SCROLLHANDDRAG = QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
NODRAG = QtWidgets.QGraphicsView.DragMode.NoDrag
save = {"pen_width": 10}


def excluding_multiconnect(connections):
    """connect all the pyqt signals in the dict connections

    will specifically disconnect and reconnect them when they trigger in order
    to stop them from triggering each other

    connections: dict of {signal: function}
    """

    def wrapper(func):
        def wrap(*args, **kwargs):
            for othersig, otherfunc in connected.items():
                othersig.disconnect(otherfunc)

            func(*args, **kwargs)
            for othersig, otherfunc in connected.items():
                othersig.connect(otherfunc)

        return wrap

    connected = {}
    for sig, func in connections.items():
        wrapped = wrapper(func)
        sig.connect(wrapped)
        connected[sig] = wrapped


class Drawer(QtWidgets.QWidget):
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent=parent)
        self.setWindowTitle("mask drawing tool")
        self.scene = QtWidgets.QGraphicsScene(parent=self)
        self.scene.setSceneRect(-512, -512, 2048, 2048)
        self.view = GraphicsViewZoom(self.scene, parent=self)

        self.scalebar = QtWidgets.QSlider(
            QtCore.Qt.Orientation.Horizontal, parent=self
        )
        self.scalebar.setRange(-GraphicsViewZoom.MAX, GraphicsViewZoom.MAX)
        self.scalebar.setPageStep(1)
        self.scalebar.setTickPosition(
            QtWidgets.QSlider.TickPosition.TicksAbove
        )

        self.set_button = QtWidgets.QPushButton("set image", parent=self)
        self.opacity_bar = QtWidgets.QSlider(
            QtCore.Qt.Orientation.Horizontal, parent=self
        )
        self.opacity_bar.setRange(0, 100)
        self.opacity_bar.setValue(100)
        self.opacity_bar.setTickPosition(
            QtWidgets.QSlider.TickPosition.TicksAbove
        )

        self.pan_button = QtWidgets.QPushButton(parent=self)
        self.erase_button = QtWidgets.QPushButton(parent=self)
        self.erasing = True

        self.width_spinbox = QtWidgets.QDoubleSpinBox(parent=self)
        self.width_bar = QtWidgets.QSlider(
            QtCore.Qt.Orientation.Horizontal, parent=self
        )
        max_width = 256
        self.width_spinbox.setRange(1, max_width)
        width_bar_steepness = 0.3
        self.width_bar.setRange(
            100, int(max_width**width_bar_steepness * 100) + 1
        )

        self.export_button = QtWidgets.QPushButton("export", parent=self)
        self.import_button = QtWidgets.QPushButton("import", parent=self)

        self.buttons = QtWidgets.QWidget(self)
        self.buttons_layout = QtWidgets.QGridLayout(self.buttons)
        self.buttons_layout.addWidget(self.set_button, 0, 0)
        self.buttons_layout.addWidget(self.pan_button, 0, 1)
        self.buttons_layout.addWidget(self.scalebar, 0, 2)
        self.buttons_layout.addWidget(self.erase_button, 0, 3)
        self.buttons_layout.addWidget(self.width_spinbox, 0, 4)
        self.buttons_layout.addWidget(self.width_bar, 0, 5)
        self.buttons_layout.addWidget(self.opacity_bar, 0, 6)
        self.buttons_layout.addWidget(self.export_button, 0, 7)
        self.buttons_layout.addWidget(self.import_button, 0, 8)

        self.layout = QtWidgets.QGridLayout(self)
        self.layout.addWidget(self.buttons, 0, 0)
        self.layout.addWidget(self.view, 1, 0)

        self.scene.setBackgroundBrush(QtGui.QColor("black"))
        self.bg = QtWidgets.QGraphicsRectItem(0, 0, 1024, 1024)
        self.bg.setBrush(QtGui.QColor("yellow"))
        self.canvas = Canvas(1024, 1024)
        self.scene.addItem(self.bg)
        self.scene.addItem(self.canvas)
        self.canvas.show()
        self.view.centerOn(self.canvas)

        self.set_button.clicked.connect(self.set_background)
        self.import_button.clicked.connect(self.import_mask)
        self.opacity_bar.valueChanged.connect(
            lambda value: self.canvas.setOpacity(value / 100)
        )
        excluding_multiconnect(
            {
                self.scalebar.valueChanged: self.view.set_zoom,
                self.view.zoomChanged: self.scalebar.setValue,
            }
        )
        excluding_multiconnect(
            {
                self.width_spinbox.valueChanged: (
                    lambda value: self.width_bar.setValue(
                        int(value**width_bar_steepness * 100)
                    )
                ),
                self.width_bar.valueChanged: (
                    lambda value: self.width_spinbox.setValue(
                        (value / 100) ** (1 / width_bar_steepness)
                    )
                ),
            }
        )
        self.width_spinbox.valueChanged.connect(
            self.canvas.default_pen.setWidthF
        )
        self.pan_button.clicked.connect(self.invert_drag)
        self.erase_button.clicked.connect(self.toggle_erase)
        self.export_button.clicked.connect(self.export_mask)

        self.width_spinbox.setValue(save["pen_width"])

        self.invert_drag()
        self.toggle_erase()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(lambda: self.view.centerOn(self.canvas))
        self.timer.setSingleShot(True)
        self.timer.start(100)

    @QtCore.pyqtSlot()
    def set_background(self):
        path, ok = QtWidgets.QFileDialog.getOpenFileName(
            self, "select file", ".", "Tiff (*.tif *.tiff)"
        )
        if not ok or not path:
            return

        pathpath = pathlib.Path(path)
        if not pathpath.exists():
            raise RuntimeError(f"{path} does not exist")

        bgimg = QtGui.QImage(path)
        self.bg.setBrush(QtGui.QBrush(bgimg))
        self.setWindowTitle(f"mask drawing tool, masking {pathpath.name}")

    @QtCore.pyqtSlot()
    def toggle_erase(self):
        if self.erasing:
            self.erasing = False
            self.erase_button.setText("start erasing")
        else:
            self.erasing = True
            self.erase_button.setText("stop erasing")

        self.canvas.erasing = self.erasing

    @QtCore.pyqtSlot()
    def invert_drag(self):
        if self.view.dragMode() is SCROLLHANDDRAG:
            self.pan_button.setText("enable panning")
            self.view.setDragMode(NODRAG)
            self.canvas.enabled = True
        else:
            self.pan_button.setText("disable panning")
            self.view.setDragMode(SCROLLHANDDRAG)
            self.canvas.enabled = False

    @QtCore.pyqtSlot()
    def export_mask(self):
        path, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, "select save location", ".", "Tiff (*.tif *.tiff)"
        )
        if not ok or not path:
            return

        if not (path.endswith(".tif") or path.endswith(".tiff")):
            path += ".tif"

        mask = self.canvas.export_image()
        tifffile.imwrite(path, mask)

    @QtCore.pyqtSlot()
    def import_mask(self):
        path, ok = QtWidgets.QFileDialog.getOpenFileName(
            self, "select file", ".", "Tiff (*.tif *.tiff)"
        )
        if not ok or not path:
            return

        if not pathlib.Path(path).exists():
            raise RuntimeError(f"{path} does not exist")

        with tifffile.TiffFile(path) as tif:
            self.canvas.import_image(tif.asarray())


class GraphicsViewZoom(QtWidgets.QGraphicsView):
    zoomChanged = QtCore.pyqtSignal(int)
    MAX = 4  # creates 9 possible values
    DIV = 2  # use twice as small steps
    # zoom steps follow a nice natural log2 curve
    # highest value = 2 ** (MAX / DIV)

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        self.setTransformationAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )

    def set_zoom(self, index):
        index = min(self.MAX, max(-self.MAX, round(index)))  # truncate
        factor = 2 ** (index / self.DIV)
        transform = QtGui.QTransform(factor, 0, 0, factor, 0, 0)
        self.setTransform(transform)
        self.zoomChanged.emit(index)

    def wheelEvent(self, event):  # override
        delta = event.angleDelta().y()
        if not delta:
            return

        factor = self.transform().m11()  # m22 will have the same value
        index = math.log2(factor) * self.DIV
        index += delta / 120
        self.set_zoom(index)


class Canvas(QtWidgets.QGraphicsRectItem):
    def __init__(self, width, height):
        self._super = super()
        self._super.__init__(0, 0, width, height)
        self.drawing = False
        self.has_drawn = False
        self.enabled = False
        self.erasing = False
        self.image = QtGui.QImage(
            width, height, QtGui.QImage.Format.Format_ARGB32
        )
        self.image.fill(QtGui.qRgba(255, 0, 0, 0))
        self.painter = QtGui.QPainter()
        self.default_pen = QtGui.QPen()
        self.default_pen.setStyle(QtCore.Qt.PenStyle.SolidLine)
        self.default_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        self.default_pen.setColor(QtGui.QColor("green"))
        self.refresh_image()

    def export_image(self):
        shape = self.image.height(), self.image.width()
        cvt = self.image.convertedTo(QtGui.QImage.Format.Format_Alpha8)
        size = cvt.sizeInBytes()
        array = np.fromiter(
            cvt.constBits().asarray(size),
            dtype=bool,  # bool is actually stored as bytes, but shown as bool
        )
        return array.reshape(shape)

    def import_image(self, image):
        height, width = image.shape
        copy = image.astype(np.uint8) * 0xFF
        self.image = QtGui.QImage(
            copy.data,
            width,
            height,
            QtGui.QImage.Format.Format_Alpha8,
        )
        self.image.convertTo(QtGui.QImage.Format.Format_ARGB32)
        self.refresh_image()

    def refresh_image(self):
        brush = QtGui.QBrush(self.image)
        self.setBrush(brush)

    def mousePressEvent(self, event):  # override
        if self.enabled:
            self.drawing = True
            self.has_drawn = False
            self.pos = event.pos()
        else:
            self._super.mousePressEvent(event)

    def mouseReleaseEvent(self, event):  # override
        if self.drawing:
            self.drawing = False
            if not self.has_drawn:
                self.draw(event.pos())
        else:
            self._super.mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):  # override
        if self.drawing:
            self.draw(event.pos())
        else:
            self._super.mouseMoveEvent(event)

    def draw(self, pos):
        self.has_drawn = True
        if self.erasing:
            self.image.invertPixels(QtGui.QImage.InvertMode.InvertRgba)

        self.painter.begin(self.image)
        self.painter.setPen(self.default_pen)
        if self.pos == pos:
            self.painter.drawPoint(pos)
        else:
            self.painter.drawLine(self.pos, pos)

        self.painter.end()
        self.pos = pos
        if self.erasing:
            self.image.invertPixels(QtGui.QImage.InvertMode.InvertRgba)

        self.refresh_image()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    drawer = Drawer(None)
    drawer.show()
    app.exec()
