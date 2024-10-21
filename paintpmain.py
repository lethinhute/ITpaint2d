import sys
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

title = "Paint"
 
class Canvas(QtWidgets.QLabel):

    current_color = '#000000'

    def __init__(self):
        super().__init__()
        self.image = QtGui.QPixmap(1200, 600)
        self.image.fill(Qt.white)
        self.setPixmap(self.image)

        self.last_x, self.last_y = None, None
        self.pen_color = QtGui.QColor('#000000')

        button = QPushButton('Open color dialog', self)
        button.setToolTip('Opens color dialog')
        button.move(10,10)
        button.clicked.connect(self.on_click)

        buttonSave = QPushButton('save', self)
        buttonSave.setToolTip('save')
        buttonSave.move(120,10)
        buttonSave.clicked.connect(self.save)

        self.show()
    
    def on_click(self):
        self.openColorDialog()

    def openColorDialog(self):
        color = QColorDialog.getColor()

        if color.isValid():
            self.set_pen_color(color)
            return

    def set_pen_color(self, c):
        self.pen_color = QtGui.QColor(c)
        current_color = c

    def mouseMoveEvent(self, e):
        if self.last_x is None: # First event.
            self.last_x = e.x()
            self.last_y = e.y()
            return # Ignore the first time.

        painter = QtGui.QPainter(self.pixmap())
        p = painter.pen()
        p.setWidth(4)
        p.setColor(self.pen_color)
        painter.setPen(p)
        painter.drawLine(self.last_x, self.last_y, e.x(), e.y())
        painter.end()
        self.update()

        # Update the origin for next time.
        self.last_x = e.x()
        self.last_y = e.y()

    def mouseReleaseEvent(self, e):
        self.last_x = None
        self.last_y = None

    def save(self):
         
        # selecting file path
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Image", "",
                         "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")
 
        # if file path is blank return back
        if filePath == "":
            return
         
        # saving canvas at desired path
        self.image = self.pixmap()
        self.image.save(filePath)

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        self.canvas = Canvas()

        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout()
        w.setLayout(l)
        l.addWidget(self.canvas)

        self.setCentralWidget(w)

        

    
    
app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()