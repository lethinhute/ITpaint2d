import sys
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

title = "Paint"
 
class Canvas(QtWidgets.QLabel):
    current_color = '#000000'

    def __init__(self, grid_size=32, cell_size=20):
        super().__init__()
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.init_canvas()
    
    def init_canvas(self):
        width, height = self.grid_size * self.cell_size, self.grid_size * self.cell_size
        self.image = QtGui.QPixmap(width, height)
        self.image.fill(Qt.white)
        self.setPixmap(self.image)

        self.pen_color = QtGui.QColor('#000000')
        self.setFixedSize(width, height)

    def set_pen_color(self, color):
        self.pen_color = color

    def clear_canvas(self, grid_size, cell_size):
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.init_canvas()
        self.update()

    def mouseMoveEvent(self, e):
        x = (e.x() // self.cell_size) * self.cell_size
        y = (e.y() // self.cell_size) * self.cell_size

        painter = QtGui.QPainter(self.pixmap())
        painter.fillRect(x, y, self.cell_size, self.cell_size, self.pen_color)
        painter.end()
        self.update()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.canvas = Canvas()
        self.setup_ui()
        self.create_menus()

    def setup_ui(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout()
        l.addWidget(self.canvas, alignment=Qt.AlignCenter)
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

        colorMenu = menubar.addMenu('Color')

        colorAction = QAction('Open Color Dialog', self)
        colorAction.triggered.connect(self.open_color_dialog)
        colorMenu.addAction(colorAction)

    def new_grid_dialog(self):
        grid_size, ok = QInputDialog.getInt(
            self, "New Grid", "Enter grid size (e.g., 32 for 32x32)", 32, 8, 512, 8
        )
        if ok:
            cell_size, ok = QInputDialog.getInt(
                self, "Cell Size", "Enter cell size (32 for 32x32, etc):", 
            )
            if ok:
                self.canvas.clear_canvas(grid_size, cell_size)

    def open_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas.set_pen_color(color)
    
    def canvas_save(self):
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")

        if filePath:
            self.canvas.pixmap().save(filePath)

app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()