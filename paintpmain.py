import sys
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap, QKeySequence

"""This is a pixel art paint app."""

default_grid_size = int(32)
default_cell_size = int(10)
 
class Canvas(QtWidgets.QLabel):
    current_color = "#000000"
    current_eraser = Qt.transparent
    width = 0
    height = 0

    isDrawing = True
    isErasing = False
    isFilling = False
    MIN_ZOOM = 0.125
    MAX_ZOOM = 8.0

    cell_size = default_cell_size
    pen_size = 1
    current_opac = 255
    isDrawingLine = False
    start_point = None 
    end_point = None 

    def __init__(self, grid_size=default_grid_size, cell_size=default_cell_size):
        super().__init__()
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.zoom_level = 1
        self.border_buffer = 20
        self.undo_stack = []
        self.redo_stack = []
        self.setMouseTracking(True)
        self.hover_cell = None
        self.initCanvas()
       
    def initCanvas(self):
        self.width, self.height = self.grid_size * self.cell_size, self.grid_size * self.cell_size
        self.setFixedSize(self.width, self.height)
        self.image = QtGui.QPixmap(self.width, self.height)
        self.image.fill(Qt.transparent)
        self.setPixmap(self.image)
        self.pen_color = QtGui.QColor('#000000')
        self.setCustomCursor("icons/cursor.png")
        self.createCaroPattern()
        self.updateTransform()
        self.setStyleSheet("""
            QLabel {
                border: 0px solid gray;
                padding: 0px;  /* Ensure no padding */
                margin: 0px;   /* Ensure no margin */
            }
        """)

    def updateTransform(self):
        width = int(self.grid_size * self.cell_size * self.zoom_level)
        height = int(self.grid_size * self.cell_size * self.zoom_level)
        self.setFixedSize(width, height)

        # No scaling of QPixmap directly here, because the painter handles scaling
        self.update()  # Trigger repaint with new scaling
    
    def createCaroPattern(self):
        painter = QtGui.QPainter(self)
        painter.scale(self.zoom_level, self.zoom_level)

        color1 = QtGui.QColor('#e0e0e0')
        color2 = QtGui.QColor('#ffffff')

        for y in range(0, self.height, self.cell_size):
            for x in range(0, self.width, self.cell_size):
                color = color1 if (x // self.cell_size + y // self.cell_size) % 2 == 0 else color2
                painter.fillRect(x, y, self.cell_size, self.cell_size, color)

        painter.drawPixmap(0, 0, self.image)
        painter.end()

    def setPenColor(self, color):
        self.pen_color = QtGui.QColor(color)
        self.current_color = color
        self.changeOpac(self.current_opac)

    def clearCanvas(self, grid_size, cell_size):
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.width = grid_size * cell_size
        self.height = self.width
        self.image = QtGui.QPixmap(grid_size * cell_size, grid_size * cell_size)

        self.image.fill(Qt.transparent)
        self.setPixmap(self.image)
        self.createCaroPattern()
        self.updateTransform()

    def mousePressEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self.saveState()
            if self.isFilling:
                x = int((e.x() / self.zoom_level) // self.cell_size) * self.cell_size
                y = int((e.y() / self.zoom_level) // self.cell_size) * self.cell_size
                self.fillEvent(x, y)
            elif self.isDrawing:
                self.drawEvent(e)
            elif self.isErasing:
                self.eraseEvent(e)
            elif self.isDrawingLine:
                self.start_point = e.pos()

    def mouseMoveEvent(self, e):
        cell_size_zoomed = self.cell_size * self.zoom_level
        x = int(e.x() / cell_size_zoomed)
        y = int(e.y() / cell_size_zoomed)
        new_hover_cell = (x, y)
        if new_hover_cell != self.hover_cell:
            self.hover_cell = new_hover_cell
            self.update()

        if e.buttons() & Qt.LeftButton:
            if self.isDrawing:
                self.drawEvent(e)
            elif self.isErasing:
                self.eraseEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.isDrawingLine and self.start_point:
                    self.end_point = e.pos()
                    self.drawLine(self.start_point, self.end_point)
                    self.start_point = None 
                    self.end_point = None

    def paintEvent(self, e):
        super().paintEvent(e)
        self.createCaroPattern()

        painter = QtGui.QPainter(self) # hover highlighting
        painter.drawPixmap(0, 0, self.pixmap())
        if self.hover_cell:
            cell_size_zoomed = self.cell_size * self.zoom_level
            x, y = self.hover_cell
            hover_x = x * cell_size_zoomed
            hover_y = y * cell_size_zoomed

            painter.setBrush(QtGui.QColor(50, 25, 25, 100))
            painter.setPen(QtGui.QColor(50, 25, 25))
            painter.drawRect(int(hover_x), int(hover_y), int(cell_size_zoomed), int(cell_size_zoomed))

        painter.end()
    
    def drawEvent(self, e):
        x = int(e.x() / self.zoom_level // self.cell_size) * self.cell_size
        y = int(e.y() / self.zoom_level // self.cell_size) * self.cell_size

        painter = QtGui.QPainter(self.image)
        painter.fillRect(x, y, self.cell_size, self.cell_size, self.pen_color)
        painter.end()
        self.updateTransform()

    def eraseEvent(self, e):
        x = int((e.x() / self.zoom_level) // self.cell_size) * self.cell_size
        y = int((e.y() / self.zoom_level) // self.cell_size) * self.cell_size
        painter = QtGui.QPainter(self.image)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
        painter.fillRect(x, y, self.cell_size * 3, self.cell_size * 3, Qt.transparent)
        painter.end()
        self.updateTransform()

    def fillEvent(self, x, y):
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
                            (cx, cy + self.cell_size), (cx, cy - self.cell_size)])
        self.updateTransform()
    
    def drawLine(self, start_point, end_point):
        start_x = (start_point.x() // self.cell_size) * self.cell_size
        start_y = (start_point.y() // self.cell_size) * self.cell_size
        end_x = (end_point.x() // self.cell_size) * self.cell_size
        end_y = (end_point.y() // self.cell_size) * self.cell_size

        dx = abs(end_x - start_x)
        dy = abs(end_y - start_y)
        sx = self.cell_size if start_x < end_x else -self.cell_size
        sy = self.cell_size if start_y < end_y else -self.cell_size
        err = dx - dy

        painter = QtGui.QPainter(self.image)
        x, y = start_x, start_y

        while True:
            painter.fillRect(x, y, self.cell_size*self.pen_size, self.cell_size*self.pen_size, self.pen_color)

            if x == end_x and y == end_y:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

        painter.end()
        self.update()
    
    def resizeCanvas(self, grid_size_h=None, grid_size_w=None):
        if grid_size_h is None or grid_size_w is None:
            grid_size_w = grid_size_h
        return self.pixmap().scaled(grid_size_w, grid_size_h, QtCore.Qt.KeepAspectRatio)
    
    def changeToPen(self):
        self.setDrawingMode(1)
        self.setCustomCursor("icons/cursor.png")

    def changeToErase(self):
        self.setDrawingMode(2)
        self.setCustomCursor("icons/eraser.png")

    def changeToFill(self):
        self.setDrawingMode(3)
        self.setCustomCursor("icons/fill.png")

    def setDrawingMode(self, action):
        self.isDrawing = action == 1
        self.isErasing = action == 2
        self.isFilling = action == 3
        self.isLine = action == 4
        self.isRectangle = action == 5
        self.isCircle = action == 6

    def setCustomCursor(self, icon_path, size=32):
        cursor_pixmap = QtGui.QPixmap(icon_path).scaled(size, size, QtCore.Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setCursor(QtGui.QCursor(cursor_pixmap))

    def saveState(self):
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.undo_stack.append(self.image.copy())
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.image.copy())
            self.image = self.undo_stack.pop()
            self.setPixmap(self.image)
            self.updateTransform()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.image.copy())
            self.image = self.redo_stack.pop()
            self.setPixmap(self.image)
            self.updateTransform()

    def resizeCanvas(self, grid_size):
        return self.pixmap().scaled(grid_size, grid_size, QtCore.Qt.KeepAspectRatio)
    
    def zoom(self, zoom_factor):
        self.zoom_level *= zoom_factor
        self.zoom_level = max(self.MIN_ZOOM, min(self.zoom_level, self.MAX_ZOOM))
        self.updateTransform()

    def resetZoom(self):
        self.zoom_level = 1
        self.updateTransform()
    
    def changeOpac(self, value):
        color = self.pen_color
        color.setAlpha(value)
        self.current_opac = value
        self.pen_color = color
        self.setFocus()
    
    def toggle_line_mode(self):
        if not self.isDrawingLine:
            self.setDrawingMode(4)
        else:
            self.setDrawingMode(1)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Paint")
        self.canvas = Canvas()
        self.canvas.setParent(self) 
        self.setupUI()
        self.createMenus()
        self.createToolbar()
        self.adjustZoomToFitCanvas()
        self.showMaximized()
    
    def changePenSize(self, value):
        self.canvas.pen_size = value
        self.pen_size_value_label.setText(f"{value}")
        self.canvas.setFocus()

    def changeOpacity(self, value):
        self.opacity_value_label.setText(f"{value}")
        self.canvas.changeOpac(value)

    def setupUI(self):
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        color_picker_layout = QVBoxLayout()
        color_row_1 = QHBoxLayout()
        colors_row_1 = [
            '#000000', '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#00FFFF', 
            '#FF6347', '#FFD700', '#FF1493', '#A52A2A', '#8A2BE2', '#C71585'
        ]
        for color in colors_row_1:
            color_button = QPushButton(self)
            color_button.setStyleSheet(f"background-color: {color};")
            color_button.clicked.connect(lambda _, col=color: self.canvas.setPenColor(col))
            color_row_1.addWidget(color_button)

        color_row_2 = QHBoxLayout()
        colors_row_2 = [
            '#FFFFFF', '#C0C0C0', '#808080', '#800000', '#008000', '#A52A2A', 
            '#9ACD32', '#4B0082', '#D2691E', '#32CD32', '#7B68EE', '#FF8C00'
        ]
        for color in colors_row_2:
            color_button = QPushButton(self)
            color_button.setStyleSheet(f"background-color: {color};")
            color_button.clicked.connect(lambda _, col=color: self.canvas.setPenColor(col))
            color_row_2.addWidget(color_button)

        # Pen Size Slider
        pen_size_label = QLabel("Pen Size:", self)
        pen_size_slider = QSlider(Qt.Horizontal, self)
        pen_size_slider.setRange(1, 10) 
        pen_size_slider.setValue(self.canvas.pen_size) 
        pen_size_slider.valueChanged.connect(self.changePenSize)

        pen_size_value_label = QLabel(str(self.canvas.pen_size), self)

        # Opacity Slider
        opacity_label = QLabel("Opacity:", self)
        opacity_slider = QSlider(Qt.Horizontal, self)
        opacity_slider.setRange(0, 255)  
        opacity_slider.setValue(255) 
        opacity_slider.valueChanged.connect(self.changeOpacity)

        opacity_value_label = QLabel(f"{255}", self)

        # Add sliders to a layout
        sliders_layout = QVBoxLayout()
        sliders_layout.addWidget(pen_size_label)
        sliders_layout.addWidget(pen_size_slider)
        sliders_layout.addWidget(opacity_label)
        sliders_layout.addWidget(opacity_slider)

        # Add layouts to the top bar
        top_bar_layout.addLayout(color_picker_layout)
        top_bar_layout.addLayout(sliders_layout)

        color_picker_layout.addLayout(color_row_1)
        color_picker_layout.addLayout(color_row_2)

        custom_color_button = QPushButton("Custom Color", self)
        custom_color_button.clicked.connect(self.openColorDialog)
        custom_color_button.setFixedSize(100, 30) 
        custom_color_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        color_row_2.addWidget(custom_color_button, alignment=Qt.AlignRight)

        spacer = QSpacerItem(15, 15, QSizePolicy.Expanding, QSizePolicy.Minimum)

        top_bar_layout.addLayout(color_picker_layout)
        top_bar_layout.addItem(spacer)

        mode_layout = QVBoxLayout()

        penButton = QPushButton("Pen", self)
        penButton.clicked.connect(self.canvas.changeToPen)
        eraserButton = QPushButton("Eraser", self)
        eraserButton.clicked.connect(self.canvas.changeToErase)
        fillButton = QPushButton("Fill", self)
        fillButton.clicked.connect(self.canvas.changeToFill)
        zoomInButton = QPushButton("Zoom In", self)
        zoomInButton.clicked.connect(lambda: self.canvas.zoom(2))
        zoomOutButton = QPushButton("Zoom Out", self)
        zoomOutButton.clicked.connect(lambda: self.canvas.zoom(0.5))
        drawLineButton = QPushButton("Draw Line", self)
        drawLineButton.clicked.connect(lambda: self.canvas.setDrawingMode(4))

        mode_layout.addWidget(penButton)
        mode_layout.addWidget(eraserButton)
        mode_layout.addWidget(fillButton)
        mode_layout.addWidget(zoomInButton)
        mode_layout.addWidget(zoomOutButton)
        mode_layout.addWidget(drawLineButton)

        top_bar_layout.addLayout(mode_layout)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignCenter) 
        self
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        main_layout = QVBoxLayout()
        main_layout.addWidget(top_bar)  
        main_layout.addWidget(scroll_area)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def createMenus(self):
        menubar = self.menuBar()
        
        newGridAction = QAction('New', self)
        newGridAction.setShortcut("Ctrl+N")
        newGridAction.triggered.connect(self.newCanvas)
        menubar.addAction(newGridAction)

        saveAction = QAction('Save', self)
        saveAction.setShortcut("Ctrl+S")
        saveAction.triggered.connect(self.saveCanvas)
        menubar.addAction(saveAction)

        openAction = QAction('Open', self)
        openAction.setShortcut("Ctrl+O")
        openAction.triggered.connect(self.openImage)
        menubar.addAction(openAction)

        undoAction = QAction("Undo", self)
        undoAction.setShortcut("Ctrl+Z")
        undoAction.triggered.connect(self.canvas.undo)
        menubar.addAction(undoAction)

        redoAction = QAction("Redo", self)
        redoAction.setShortcut("Ctrl+Y")
        redoAction.triggered.connect(self.canvas.redo)
        menubar.addAction(redoAction)
    
    def createToolbar(self):
        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)

        penAction = QAction("Pen", self)
        penAction.triggered.connect(self.canvas.changeToPen)
        toolbar.addAction(penAction)

        eraserAction = QAction("Eraser", self)
        eraserAction.triggered.connect(self.canvas.changeToErase)
        toolbar.addAction(eraserAction)

        fillAction = QAction("Fill", self)
        fillAction.triggered.connect(self.canvas.changeToFill)
        toolbar.addAction(fillAction)

        colorAction = QAction("Open Color Dialog", self)
        colorAction.triggered.connect(self.openColorDialog)
        toolbar.addAction(colorAction)
        
        zoomInAction = QAction("Zoom In", self)
        zoomInAction.setShortcuts({QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")})
        zoomInAction.triggered.connect(lambda: self.canvas.zoom(2))
        toolbar.addAction(zoomInAction)
        
        zoomOutAction = QAction("Zoom Out", self)
        zoomOutAction.setShortcuts({QKeySequence("Ctrl+-"), QKeySequence("Ctrl+_")})
        zoomOutAction.triggered.connect(lambda: self.canvas.zoom(0.5))
        toolbar.addAction(zoomOutAction)
        
        resetZoomAction = QAction("Reset Zoom", self)
        resetZoomAction.setShortcut("Ctrl+0")
        resetZoomAction.triggered.connect(self.canvas.resetZoom)
        toolbar.addAction(resetZoomAction)

        lineAction = QAction("Line Tool", self)
        lineAction.triggered.connect(lambda: self.canvas.setDrawingMode(4))
        toolbar.addAction(lineAction)

        rectangleAction = QAction("Rectangle Tool", self)
        rectangleAction.triggered.connect(lambda: self.canvas.setDrawingMode(5))
        toolbar.addAction(rectangleAction)

        circleAction = QAction("Circle Tool", self)
        circleAction.triggered.connect(lambda: self.canvas.setDrawingMode(6))
        toolbar.addAction(circleAction)
    
    def adjustZoomToFitCanvas(self):
        central_widget = self.centralWidget()
        scroll_area = central_widget.findChild(QtWidgets.QScrollArea)
        if scroll_area:
            available_width = self.width() - scroll_area.verticalScrollBar().sizeHint().width()
            available_height = self.height() - scroll_area.horizontalScrollBar().sizeHint().height()
            canvas_width = self.canvas.grid_size * self.canvas.cell_size
            canvas_height = self.canvas.grid_size * self.canvas.cell_size

            width_ratio = available_width / canvas_width
            height_ratio = available_height / canvas_height
            zoom_factor = min(width_ratio, height_ratio)

            self.canvas.zoom_level = zoom_factor
            self.canvas.updateTransform()
        else:
            print("Scroll area not found in central widget")

        
    def newCanvas(self):
        grid_size, ok = QInputDialog.getInt(self, "New Canvas", "Grid size (e.g., 32):", 32, 8, 512, 8)
        if ok:
            self.canvas.clearCanvas(grid_size, default_cell_size)
            self.canvas.updateTransform()
            self.showMaximized()

    def openColorDialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas.setPenColor(color.name())
    
    def saveCanvas(self):
        try:
            filePath, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")
            if filePath:
                scaled_image = self.canvas.image.scaled(self.canvas.width // self.canvas.cell_size, 
                                                        self.canvas.height // self.canvas.cell_size, 
                                                        QtCore.Qt.IgnoreAspectRatio)
                scaled_image.save(filePath)
            else:
                raise Exception("Failed to save the file.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unable to save the image. Error: {e}")

    def openImage(self):
        try:
            imagePath, _ = QFileDialog.getOpenFileName()
            if imagePath:
                pixmap = QPixmap(imagePath)
                if pixmap.isNull():
                    raise Exception("Invalid image format.")
                if pixmap.width() != pixmap.height():
                    raise ValueError("The image must be square (width and height must be equal).")
                
                image_width = pixmap.width()
                image_height = pixmap.height()
                if image_width == image_height:
                    grid_size = image_width
                    self.canvas.clearCanvas(grid_size, self.canvas.cell_size)

                    self.canvas.image = pixmap.scaled(self.canvas.size(), QtCore.Qt.IgnoreAspectRatio)
                    self.canvas.setPixmap(self.canvas.image)

                    self.showMaximized()
                else:
                    QMessageBox.warning(self, "Error", "The image must be square (width and height must be equal).")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open the image. Error: {e}")

app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()