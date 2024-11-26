import sys
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap

gridsize = int(32)
 
class Canvas(QtWidgets.QLabel):
    current_color = '#000000'
    current_eraser = Qt.transparent
    isDrawing = True
    isErasing = False
    isFilling = False
    MIN_ZOOM = 0.125
    MAX_ZOOM = 8.0

    def __init__(self, grid_size=32, cell_size=20):
        super().__init__()
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.zoom_level = 1.0
        self.undo_stack = []
        self.redo_stack = []
        self.init_canvas()

    def init_canvas(self):
        width, height = self.grid_size * self.cell_size, self.grid_size * self.cell_size
        self.setFixedSize(width, height)
        self.image = QtGui.QPixmap(width, height)
        self.image.fill(Qt.transparent)
        self.setPixmap(self.image)
        self.pen_color = QtGui.QColor('#000000')
        self.set_custom_cursor("icons/pen.png")
        self.updateTransform()
        self.setStyleSheet("border: 3px solid gray")

    def updateTransform(self):
        width = int(self.grid_size * self.cell_size * self.zoom_level)
        height = int(self.grid_size * self.cell_size * self.zoom_level)
        self.setFixedSize(width, height)

        # Update the pixmap to match the scaled size
        scaled_image = self.image.scaled(width, height, QtCore.Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled_image)

    def set_pen_color(self, color):
        self.pen_color = QtGui.QColor(color)
        self.current_color = color

    def clear_canvas(self, grid_size, cell_size):
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.image = QtGui.QPixmap(self.grid_size * self.cell_size, self.grid_size * self.cell_size)
        self.image.fill(Qt.transparent)
        self.setPixmap(self.image)
        self.updateTransform()

    def mouseMoveEvent(self, e):
        if self.isDrawing:
            self.DrawEvent(e)
        elif self.isErasing:
            self.EraserEvent(e)

    def mousePressEvent(self, e):
        self.save_state()
        if self.isFilling:
            x = int((e.x() / self.zoom_level) // self.cell_size) * self.cell_size
            y = int((e.y() / self.zoom_level) // self.cell_size) * self.cell_size
            self.fill_canvas(x, y)
        elif self.isDrawing:
            self.DrawEvent(e)
        elif self.isErasing:
            self.EraserEvent(e)

    # def mouseReleaseEvent(self, e):
    
    def DrawEvent(self, e):
        x = int((e.x() / self.zoom_level) // self.cell_size) * self.cell_size
        y = int((e.y() / self.zoom_level) // self.cell_size) * self.cell_size
        painter = QtGui.QPainter(self.image)
        painter.fillRect(x, y, self.cell_size, self.cell_size, self.pen_color)
        painter.end()
        self.updateTransform()

    def EraserEvent(self, e):
        x = int((e.x() / self.zoom_level) // self.cell_size) * self.cell_size
        y = int((e.y() / self.zoom_level) // self.cell_size) * self.cell_size
        painter = QtGui.QPainter(self.image)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
        painter.fillRect(x, y, self.cell_size*3, self.cell_size*3, Qt.transparent)
        painter.end()
        self.updateTransform()

    def fill_canvas(self, x, y):
        img = self.image.toImage()
        target_color = img.pixelColor(x, y)
        if target_color == self.pen_color:
            return # avoid inf recursion
        stack = [(x, y)]
        visited = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue # skip already visited
            if not (0 <= cx < self.image.width() and 0 <= cy < self.image.height()):
                continue # check within bounds
            current_color = img.pixelColor(cx, cy)
            if current_color == target_color:
                painter = QtGui.QPainter(self.image)
                painter.fillRect(cx, cy, self.cell_size, self.cell_size, self.pen_color)
                painter.end()
                visited.add((cx, cy))
                stack.extend([(cx + self.cell_size, cy), (cx - self.cell_size, cy), 
                            (cx, cy + self.cell_size), (cx, cy - self.cell_size)]) # add neighbors

        self.updateTransform()
    
    def resizeCanvas(self, grid_size_h=None, grid_size_w=None): # optional square or rectangle
        if grid_size_h is None or grid_size_w is None:
            grid_size_w = grid_size_h
        return self.pixmap().scaled(grid_size_w, grid_size_h, QtCore.Qt.KeepAspectRatio)
    
    def changeToPen(self):
        self.setDrawingMode(1)
        self.set_custom_cursor("icons/pen.png")

    def changeToErase(self):
        self.setDrawingMode(2)
        self.set_custom_cursor("icons/eraser.png")

    def changeToFill(self):
        self.setDrawingMode(3)
        self.set_custom_cursor("icons/fill.png")

    def setDrawingMode(self, action):
        if action == 1: # Pen
            self.isDrawing = True
            self.isErasing = False
            self.isFilling = False
        elif action == 2: # Eraser
            self.isDrawing = False
            self.isErasing = True
            self.isFilling = False
        elif action == 3: # FIll
            self.isDrawing = False
            self.isErasing = False
            self.isFilling = True

    def zoom(self, zoom_factor):
        self.zoom_level *= zoom_factor
        self.zoom_level = max(self.MIN_ZOOM, min(self.zoom_level, self.MAX_ZOOM))
        self.updateTransform()

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.updateTransform()

    def set_custom_cursor(self, icon_path, size=32):
        cursor_pixmap = QtGui.QPixmap(icon_path).scaled(size, size, QtCore.Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setCursor(QtGui.QCursor(cursor_pixmap))

    def save_state(self):
        if len(self.undo_stack) > 50:  # Optional: Limit the stack size to prevent excessive memory usage
            self.undo_stack.pop(0)
        self.undo_stack.append(self.image.copy())  # Save a copy of the current state
        self.redo_stack.clear()  # Clear redo stack on new action

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.image.copy())  # Save the current state to the redo stack
            self.image = self.undo_stack.pop()  # Restore the previous state
            self.setPixmap(self.image)  # Update the canvas display
            self.updateTransform()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.image.copy())  # Save the current state to the undo stack
            self.image = self.redo_stack.pop()  # Restore the next state
            self.setPixmap(self.image)  # Update the canvas display
            self.updateTransform()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Paint")
        self.canvas = Canvas()
        self.setup_ui()
        self.create_menus()
        self.adjust_window_size_to_canvas()

    def setup_ui(self):
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.setCentralWidget(scroll_area)
            
    def create_menus(self):
        menubar = self.menuBar()

        fileMenu = menubar.addMenu('File')

        newGridAction = QAction('New Grid', self)
        newGridAction.setShortcut("Ctrl+N")
        newGridAction.triggered.connect(self.new_grid_dialog)
        fileMenu.addAction(newGridAction)

        saveAction = QAction('Save', self)
        saveAction.setShortcut("Ctrl+S")
        saveAction.triggered.connect(self.canvas_save)
        fileMenu.addAction(saveAction)

        openAction = QAction('Open', self)
        openAction.setShortcut("Ctrl+O")
        openAction.triggered.connect(self.openImage)
        fileMenu.addAction(openAction)

        editMenu = self.menuBar().addMenu("Edit")

        undoAction = QAction("Undo", self)
        undoAction.setShortcut("Ctrl+Z")
        undoAction.triggered.connect(self.canvas.undo)
        editMenu.addAction(undoAction)

        redoAction = QAction("Redo", self)
        redoAction.setShortcut("Ctrl+Y")
        redoAction.triggered.connect(self.canvas.redo)
        editMenu.addAction(redoAction)

        toolMenu = menubar.addMenu('Tools')

        penAction = QAction('Pen', self)
        penAction.triggered.connect(self.canvas.changeToPen)
        toolMenu.addAction(penAction)

        eraserAction = QAction('Eraser', self)
        eraserAction.triggered.connect(self.canvas.changeToErase)
        toolMenu.addAction(eraserAction)

        fillAction = QAction('Fill Canvas', self)
        fillAction.triggered.connect(self.canvas.changeToFill)
        toolMenu.addAction(fillAction)

        colorMenu = menubar.addMenu('Color')

        colorAction = QAction('Open Color Dialog', self)
        colorAction.triggered.connect(self.open_color_dialog)
        colorMenu.addAction(colorAction)

        viewMenu = menubar.addMenu("View")
        
        zoomInAction = QAction("Zoom In", self)
        zoomInAction.setShortcut("Ctrl+=")
        zoomInAction.setShortcut("Ctrl++")
        zoomInAction.triggered.connect(lambda: self.canvas.zoom(2))
        viewMenu.addAction(zoomInAction)
        
        zoomOutAction = QAction("Zoom Out", self)
        zoomOutAction.setShortcut("Ctrl+-")
        zoomOutAction.triggered.connect(lambda: self.canvas.zoom(0.5))
        viewMenu.addAction(zoomOutAction)
        
        resetZoomAction = QAction("Reset Zoom", self)
        resetZoomAction.setShortcut("Ctrl+0")
        resetZoomAction.triggered.connect(self.canvas.reset_zoom)
        viewMenu.addAction(resetZoomAction)
    
    def adjust_window_size_to_canvas(self):
        canvas_width = self.canvas.grid_size * self.canvas.cell_size
        canvas_height = self.canvas.grid_size * self.canvas.cell_size

        scroll_area_frame_width = self.centralWidget().frameWidth()
        menu_bar_height = self.menuBar().height()

        total_width = canvas_width + 2 * scroll_area_frame_width
        total_height = canvas_height + menu_bar_height + 2 * scroll_area_frame_width

        self.resize(total_width + 50, total_height + 50)

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
            self.canvas.setFocus()
    
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