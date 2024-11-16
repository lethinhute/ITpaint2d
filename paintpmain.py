import sys
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap

title = "Paint" # what is this for?

gridsize = int(32)
 
class Canvas(QtWidgets.QLabel):
    def __init__(self, grid_size=32, cell_size=20):
        super().__init__()
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.zoom_level = 1.0
        self.init_canvas()

    def init_canvas(self):
        width, height = self.grid_size * self.cell_size, self.grid_size * self.cell_size
        self.setFixedSize(width, height)
        self.image = QtGui.QPixmap(width, height)
        self.image.fill(Qt.transparent)
        self.setPixmap(self.image)
        self.pen_color = QtGui.QColor('#000000')
        self.updateTransform()

    def updateTransform(self):
        transform = QtGui.QTransform()
        transform.scale(self.zoom_level, self.zoom_level)
        self.setPixmap(self.image.transformed(transform, Qt.SmoothTransformation))
        self.update()

    def set_pen_color(self, color):
        self.pen_color = color

    def clear_canvas(self, grid_size, cell_size):
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.image = QtGui.QPixmap(self.grid_size * self.cell_size, self.grid_size * self.cell_size)
        self.image.fill(Qt.transparent)
        self.setPixmap(self.image)
        self.updateTransform()

    def mouseMoveEvent(self, e):
        x = int((e.x() / self.zoom_level) // self.cell_size) * self.cell_size
        y = int((e.y() / self.zoom_level) // self.cell_size) * self.cell_size
        painter = QtGui.QPainter(self.image)
        painter.fillRect(x, y, self.cell_size, self.cell_size, self.pen_color)
        painter.end()
        self.updateTransform()

    def resizeCanvas (self, grid_size):
        return self.pixmap().scaled(grid_size, grid_size, QtCore.Qt.KeepAspectRatio)

    def zoom(self, zoom_factor):
        self.zoom_level *= zoom_factor
        self.updateTransform()

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.updateTransform()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.canvas = Canvas()
        self.setup_ui()
        self.create_menus()

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl++"), self).activated.connect(lambda: self.canvas.zoom(2))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+="), self).activated.connect(lambda: self.canvas.zoom(2))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+-"), self).activated.connect(lambda: self.canvas.zoom(0.5))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+0"), self).activated.connect(self.canvas.reset_zoom)

    def setup_ui(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout()
        l.addWidget(self.canvas, alignment=Qt.AlignTop)
        w.setLayout(l)
        self.setCentralWidget(w)
            
    def create_menus(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        
        newGridAction = QAction('New Grid', self)
        newGridAction.triggered.connect(self.new_grid_dialog)
        fileMenu.addAction(newGridAction)

        saveAction = QAction('Save', self)
        saveAction.triggered.connect(self.canvas_save)
        fileMenu.addAction(saveAction)

        openAction = QAction('Open', self)
        openAction.triggered.connect(self.openImage)
        fileMenu.addAction(openAction)

        colorMenu = menubar.addMenu('Color')
        colorAction = QAction('Open Color Dialog', self)
        colorAction.triggered.connect(self.open_color_dialog)
        colorMenu.addAction(colorAction)

        viewMenu = menubar.addMenu("View")
        
        zoomInAction = QAction("Zoom In", self)
        zoomInAction.triggered.connect(lambda: self.canvas.zoom(2))
        viewMenu.addAction(zoomInAction)
        
        zoomOutAction = QAction("Zoom Out", self)
        zoomOutAction.triggered.connect(lambda: self.canvas.zoom(0.5))
        viewMenu.addAction(zoomOutAction)
        
        resetZoomAction = QAction("Reset Zoom", self)
        resetZoomAction.triggered.connect(self.canvas.reset_zoom)
        viewMenu.addAction(resetZoomAction)

    def new_grid_dialog(self):
        grid_size, ok = QInputDialog.getInt(
            self, "New Grid", "Enter grid size (e.g., 32 for 32x32)", 32, 8, 512, 8
        )
        if ok:
                global gridsize
                gridsize = grid_size
                self.canvas.clear_canvas(grid_size, 16)

                # resize window
                new_width = grid_size * self.canvas.cell_size + self.canvas.frameWidth() * 2
                new_height = grid_size * self.canvas.cell_size + self.menuBar().height() + self.canvas.frameWidth() * 2
                self.setFixedSize(new_width, new_height)

    def open_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas.set_pen_color(color)
    
    def canvas_save(self):
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")

        if filePath:
            self.canvas.resizeCanvas(gridsize).save(filePath)

    def openImage(self):
        imagePath, _ = QFileDialog.getOpenFileName()
        if imagePath:
            pixmap = QPixmap(imagePath)
            image_width = pixmap.width()
            image_height = pixmap.height()

            if image_width == image_height:
                grid_size = image_width
                self.canvas.clear_canvas(grid_size, self.canvas.cell_size)

                self.canvas.image = pixmap.scaled(self.canvas.size(), QtCore.Qt.IgnoreAspectRatio)
                self.canvas.setPixmap(self.canvas.image)

                new_window_width = grid_size * self.canvas.cell_size + self.canvas.frameWidth() * 2
                new_window_height = grid_size * self.canvas.cell_size + self.menuBar().height() + self.canvas.frameWidth() * 2
                self.resize(new_window_width, new_window_height)
            else:
                QMessageBox.warning(self, "Error", "The image must be square (width and height must be equal).")

app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()