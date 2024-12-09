import sys
import PyQt5 # unused
from PyQt5 import QtCore, QtGui, QtWidgets # unused
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from functools import partial

"""This is a pixel art paint app."""

default_grid_size = int(64)
default_cell_size = int(10)
 
class Canvas(QLabel):
    isDrawing = True
    isErasing = False
    isFilling = False
    isLine = False
    isRectangle = False
    isEllipse = False
    MIN_ZOOM = 0.125
    MAX_ZOOM = 8.0
    zoomChanged = pyqtSignal(float)
    pen_size = 1
    current_opac = 255

    def __init__(self, grid_size=default_grid_size, cell_size=default_cell_size):
        super().__init__()
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.zoom_level = 1
        self.undo_stack = []
        self.redo_stack = []
        self.setMouseTracking(True)
        self.hover_cell = None
        self.initCanvas()
       
    def initCanvas(self):
        self.width, self.height = self.grid_size * self.cell_size, self.grid_size * self.cell_size
        self.setFixedSize(self.width, self.height)
        self.image = QPixmap(self.width, self.height)
        self.image.fill(Qt.transparent)
        self.setPixmap(self.image)
        self.pen_color = QColor("#000000")
        self.setCustomCursor("icons/cursor.png")
        self.createCaroPattern()
        self.updateTransform()

    def updateTransform(self): # note: no scaling of QPixmap happens here directly because painter/paintEvent handles scaling
        width = int(self.grid_size * self.cell_size * self.zoom_level)
        height = int(self.grid_size * self.cell_size * self.zoom_level)
        self.setFixedSize(width, height)

        self.update()  # trigger repaint with new scaling
    
    def createCaroPattern(self):
        painter = QPainter(self)
        painter.scale(self.zoom_level, self.zoom_level)

        color1 = QColor("#E0E0E0")
        color2 = QColor("#FFFFFF")

        for y in range(0, self.height, self.cell_size):
            for x in range(0, self.width, self.cell_size):
                color = color1 if (x // self.cell_size + y // self.cell_size) % 2 == 0 else color2
                painter.fillRect(x, y, self.cell_size, self.cell_size, color)

        painter.drawPixmap(0, 0, self.image)
        painter.end()

    def setPenColor(self, color):
        self.pen_color = QColor(color)
        self.current_color = color
        self.changeOpac(self.current_opac)

    def clearCanvas(self, grid_size, cell_size):
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.width = grid_size * cell_size
        self.height = self.width
        self.image = QPixmap(grid_size * cell_size, grid_size * cell_size)

        self.image.fill(Qt.transparent)
        self.setPixmap(self.image)
        self.createCaroPattern()
        self.updateTransform()

    def mousePressEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self.saveState()
            self.start_pos = self.snapToGrid(e.pos())
            if self.isDrawing:
                self.drawEvent(e)
            elif self.isErasing:
                self.eraseEvent(e)
            elif self.isFilling:
                x = int((e.x() / self.zoom_level) // self.cell_size) * self.cell_size
                y = int((e.y() / self.zoom_level) // self.cell_size) * self.cell_size
                self.fillEvent(x, y)
            elif self.isLine or self.isRectangle or self.isEllipse:
                self.temp_image = self.image.copy()

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
            elif self.isLine or self.isRectangle or self.isEllipse:
                self.end_pos = self.snapToGrid(e.pos())
                self.image = self.temp_image.copy()
                self.drawShapePreview()
                self.updateTransform()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.isLine or self.isRectangle or self.isEllipse:
                self.end_pos = self.snapToGrid(e.pos())
                self.drawShapeFinal()
                self.updateTransform()
            self.last_pos = None

    def paintEvent(self, e):
        super().paintEvent(e)
        self.createCaroPattern()
        painter = QPainter(self)

        painter.fillRect(self.rect(), Qt.transparent) # proper reset when updating
        painter.scale(self.zoom_level, self.zoom_level)
        painter.drawPixmap(0, 0, self.pixmap())

        if self.hover_cell: # hover
            cell_size_zoomed = self.cell_size
            x, y = self.hover_cell
            painter.setBrush(QColor(50, 25, 25, 100))
            painter.setPen(QColor(50, 25, 25))
            painter.drawRect(x * cell_size_zoomed, y * cell_size_zoomed, cell_size_zoomed, cell_size_zoomed)

        painter.end()

    def drawOrEraseLine(self, start_pos, end_pos, painter, erase=False):
        x1, y1 = start_pos.x(), start_pos.y()
        x2, y2 = end_pos.x(), end_pos.y()
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = self.cell_size if x1 < x2 else -self.cell_size
        sy = self.cell_size if y1 < y2 else -self.cell_size
        err = dx - dy

        while True:
            size = self.cell_size * self.pen_size
            if erase:
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.fillRect(x1, y1, size, size, Qt.transparent)
            else:
                painter.fillRect(x1, y1, size, size, self.pen_color)

            if x1 == x2 and y1 == y2:
                break
            e2 = err * 2
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def drawEvent(self, e):
        current_x = int(e.x() / self.zoom_level // self.cell_size) * self.cell_size
        current_y = int(e.y() / self.zoom_level // self.cell_size) * self.cell_size
        current_pos = QPoint(current_x, current_y)

        if not hasattr(self, "last_pos") or self.last_pos is None:
            self.last_pos = current_pos

        painter = QPainter(self.image)
        self.drawOrEraseLine(self.last_pos, current_pos, painter, erase=False)
        painter.end()

        self.last_pos = current_pos
        self.updateTransform()

    def eraseEvent(self, e):
        current_x = int((e.x() / self.zoom_level) // self.cell_size) * self.cell_size
        current_y = int((e.y() / self.zoom_level) // self.cell_size) * self.cell_size
        current_pos = QPoint(current_x, current_y)

        if not hasattr(self, "last_pos") or self.last_pos is None:
            self.last_pos = current_pos

        painter = QPainter(self.image)
        self.drawOrEraseLine(self.last_pos, current_pos, painter, erase=True)
        painter.end()

        self.last_pos = current_pos
        self.updateTransform()

    def fillEvent(self, x, y):
        img = self.image.toImage()
        target_color = img.pixelColor(x, y)
        if target_color == self.pen_color:
            return 
        stack = [(x, y)]
        visited = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            if not (0 <= cx < self.image.width() and 0 <= cy < self.image.height()):
                continue 
            current_color = img.pixelColor(cx, cy)
            if current_color == target_color:
                painter = QPainter(self.image)
                painter.fillRect(cx, cy, self.cell_size, self.cell_size, self.pen_color)
                painter.end()
                visited.add((cx, cy))
                stack.extend([(cx + self.cell_size, cy), (cx - self.cell_size, cy), 
                            (cx, cy + self.cell_size), (cx, cy - self.cell_size)])
        self.updateTransform()

    def snapToGrid(self, pos):
        x = int((pos.x() / self.zoom_level) // self.cell_size) * self.cell_size
        y = int((pos.y() / self.zoom_level) // self.cell_size) * self.cell_size
        return QPoint(x, y)
    
    def drawShapePreview(self):
        painter = QPainter(self.image)
        painter.setPen(QPen(self.pen_color, 1))
        if self.isLine:
            self.drawLine(painter, self.start_pos, self.end_pos)
        elif self.isRectangle:
            self.drawRectangle(painter, self.start_pos, self.end_pos)
        elif self.isEllipse:
            self.drawEllipse(painter, self.start_pos, self.end_pos)
        painter.end()
        
    def drawShapeFinal(self):
        painter = QPainter(self.image)
        painter.setPen(QPen(self.pen_color, 1))
        painter.setBrush(self.pen_color)
        if self.isLine:
            self.drawLine(painter, self.start_pos, self.end_pos, finalize=True)
        elif self.isRectangle:
            self.drawRectangle(painter, self.start_pos, self.end_pos)
        elif self.isEllipse:
            self.drawEllipse(painter, self.start_pos, self.end_pos)
        painter.end()

    def drawLine(self, painter, start, end, finalize=False): # Bresenham's algorithm
        x1, y1 = start.x() // self.cell_size, start.y() // self.cell_size
        x2, y2 = end.x() // self.cell_size, end.y() // self.cell_size
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            cell_x = x1 * self.cell_size
            cell_y = y1 * self.cell_size
            painter.fillRect(cell_x, cell_y, self.cell_size, self.cell_size, self.pen_color)
            if x1 == x2 and y1 == y2:
                break
            e2 = err * 2
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def drawRectangle(self, painter, start, end):
        x1, y1 = start.x(), start.y()
        x2, y2 = end.x(), end.y()
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)

        for x in range(x1, x2 + self.cell_size, self.cell_size):
            painter.fillRect(x, y1, self.cell_size, self.cell_size, self.pen_color)
            painter.fillRect(x, y2, self.cell_size, self.cell_size, self.pen_color)
        
        for y in range(y1 + self.cell_size, y2, self.cell_size):
            painter.fillRect(x1, y, self.cell_size, self.cell_size, self.pen_color)
            painter.fillRect(x2, y, self.cell_size, self.cell_size, self.pen_color)

    def drawEllipse(self, painter, start, end): # midpoint algorithm
        x1, y1 = start.x(), start.y()
        x2, y2 = end.x(), end.y()
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)

        rx = (x2 - x1) // 2
        ry = (y2 - y1) // 2
        cx = x1 + rx
        cy = y1 + ry

        x, y = 0, ry
        dx, dy = 0, 2 * rx * rx * y
        p1 = ry * ry - (rx * rx * ry) + (0.25 * rx * rx)
        while dx < dy:
            self.fillEllipseCells(painter, cx, cy, x, y)
            x += self.cell_size
            dx += 2 * ry * ry
            if p1 < 0:
                p1 += dx + ry * ry
            else:
                y -= self.cell_size
                dy -= 2 * rx * rx
                p1 += dx - dy + ry * ry

        p2 = (ry * ry) * (x + 0.5) ** 2 + (rx * rx) * (y - 1) ** 2 - (rx * rx * ry * ry)
        while y >= 0:
            self.fillEllipseCells(painter, cx, cy, x, y)
            y -= self.cell_size
            dy -= 2 * rx * rx
            if p2 > 0:
                p2 += rx * rx - dy
            else:
                x += self.cell_size
                dx += 2 * ry * ry
                p2 += dx - dy + rx * rx

    def fillEllipseCells(self, painter, cx, cy, x, y):
        painter.fillRect(cx + x, cy + y, self.cell_size, self.cell_size, self.pen_color)
        painter.fillRect(cx - x, cy + y, self.cell_size, self.cell_size, self.pen_color)
        painter.fillRect(cx + x, cy - y, self.cell_size, self.cell_size, self.pen_color)
        painter.fillRect(cx - x, cy - y, self.cell_size, self.cell_size, self.pen_color)
    
    def changeToPen(self):
        self.setDrawingMode(1)
        self.setCustomCursor("icons/cursor.png")

    def changeToErase(self):
        self.setDrawingMode(2)
        self.setCustomCursor("icons/eraser.png")

    def changeToFill(self):
        self.setDrawingMode(3)
        self.setCustomCursor("icons/fill.png")

    def changeToLine(self):
        self.setDrawingMode(4)
        self.setCustomCursor("icons/cursor_shape.png")

    def changeToRectangle(self):
        self.setDrawingMode(5)
        self.setCustomCursor("icons/cursor_shape.png")
    
    def changeToEllipse(self):
        self.setDrawingMode(6)
        self.setCustomCursor("icons/cursor_shape.png")

    def setDrawingMode(self, action):
        self.isDrawing = action == 1
        self.isErasing = action == 2
        self.isFilling = action == 3
        self.isLine = action == 4
        self.isRectangle = action == 5
        self.isEllipse = action == 6

    def setCustomCursor(self, icon_path, size=32):
        cursor_pixmap = QPixmap(icon_path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setCursor(QCursor(cursor_pixmap))

    def saveState(self):
        if self.undo_stack and self.image.toImage() == self.undo_stack[-1].toImage(): # avoid duplicates
            return
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.undo_stack.append(self.image.copy())
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            if hasattr(self, "last_pos") and self.last_pos:
                self.saveState() # handles active drawing
            self.redo_stack.append(self.image.copy())
            self.image = self.undo_stack.pop()
            self.update()

    def redo(self):
        if self.redo_stack:
            if hasattr(self, "last_pos") and self.last_pos:  # handles active drawing
                self.saveState()
            self.undo_stack.append(self.image.copy())
            self.image = self.redo_stack.pop()
            self.update()
    
    def resizeCanvas(self, grid_size):
        return self.pixmap().scaled(grid_size, grid_size, Qt.KeepAspectRatio)
    
    def zoom(self, zoom_factor):
        self.zoom_level *= zoom_factor
        self.zoom_level = max(self.MIN_ZOOM, min(self.zoom_level, self.MAX_ZOOM))
        self.updateTransform()
        self.zoomChanged.emit(self.zoom_level)

    def resetZoom(self):
        self.zoom_level = 1
        self.updateTransform()
        self.zoomChanged.emit(self.zoom_level)
    
    def changeOpac(self, value):
        color = self.pen_color
        color.setAlpha(value)
        self.current_opac = value
        self.pen_color = color
        self.setFocus()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Paint")
        self.canvas = Canvas()
        self.canvas.setParent(self) 
        self.setupUI()
        self.createMenus()
        self.showMaximized()
        self.selected_tool_button = None
        self.selected_color_button = None

    def setupUI(self):
        main_layout = QHBoxLayout()
        
        left_bar = QVBoxLayout()
        left_bar_widget = QWidget()
        left_bar_widget.setLayout(left_bar)
        left_bar_widget.setStyleSheet("background-color: #B0C4DE; border: 2px solid black;")

        self.zoom_level_label = QLabel("Zoom:\n100%", self)
        self.zoom_level_label.setAlignment(Qt.AlignCenter)
        self.zoom_level_label.setStyleSheet("color: black; font-weight: bold; border: none;")
        left_bar.addWidget(self.zoom_level_label)
        self.canvas.zoomChanged.connect(self.updateZoomLabel)

        tools = [
            ("icons/pen.png", self.canvas.changeToPen),
            ("icons/eraser.png", self.canvas.changeToErase),
            ("icons/fill.png", self.canvas.changeToFill),
            ("icons/line.png", self.canvas.changeToLine),
            ("icons/rectangle.png", self.canvas.changeToRectangle),
            ("icons/ellipse.png", self.canvas.changeToEllipse),
            ("icons/zoom_in.png", partial(self.canvas.zoom, 2)),
            ("icons/zoom_out.png", partial(self.canvas.zoom, 0.5)),
            ("icons/zoom_reset.png", self.canvas.resetZoom),
        ]

        for icon_path, action in tools:
            button = QPushButton(QIcon(icon_path), "", self)
            button.setFixedSize(85, 85)
            button.setIconSize(QSize(60, 60))
            button.setStyleSheet("background-color: white;")
            button.clicked.connect(lambda checked, btn=button, act=action: self.selectTool(btn, act))
            left_bar.addWidget(button)
        
        left_bar.addStretch()  # add stretch to push buttons to the top

        zoom_in_shortcut_1 = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in_shortcut_2 = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in_shortcut_1.activated.connect(lambda: self.canvas.zoom(2))
        zoom_in_shortcut_2.activated.connect(lambda: self.canvas.zoom(2))

        zoom_out_shortcut_1 = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out_shortcut_2 = QShortcut(QKeySequence("Ctrl+_"), self)
        zoom_out_shortcut_1.activated.connect(lambda: self.canvas.zoom(0.5))
        zoom_out_shortcut_2.activated.connect(lambda: self.canvas.zoom(0.5))

        reset_zoom_shortcut_1 = QShortcut(QKeySequence("Ctrl+0"), self)
        reset_zoom_shortcut_2 = QShortcut(QKeySequence("Ctrl+)"), self)
        reset_zoom_shortcut_1.activated.connect(self.canvas.resetZoom)
        reset_zoom_shortcut_2.activated.connect(self.canvas.resetZoom)

        scroll_area = QScrollArea() # canvas / middle area
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignCenter)

        right_bar = QVBoxLayout()
        right_bar_widget = QWidget()
        right_bar_widget.setLayout(right_bar)
        right_bar_widget.setStyleSheet("background-color: #B0C4DE; border: 2px solid black;")

        pen_size_label = QLabel("Pen Size:", self)
        pen_size_label.setAlignment(Qt.AlignCenter)
        pen_size_label.setStyleSheet("color: black; border: none; font-weight: bold;")
        self.pen_size_slider = QSlider(Qt.Horizontal, self)
        self.pen_size_slider.setRange(1, 10)
        self.pen_size_slider.setValue(self.canvas.pen_size)
        self.pen_size_slider.valueChanged.connect(self.changePenSize)
        self.pen_size_slider.setStyleSheet("border: none;")
        self.pen_size_value_label = QLabel(str(self.canvas.pen_size))
        self.pen_size_value_label.setStyleSheet("color: black; border: none; font-weight: bold;")
        self.pen_size_value_label.setAlignment(Qt.AlignCenter)

        opacity_label = QLabel("Opacity:", self)
        opacity_label.setAlignment(Qt.AlignCenter)
        opacity_label.setStyleSheet("color: black; border: none; font-weight: bold;")
        self.opacity_slider = QSlider(Qt.Horizontal, self)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setValue(255)
        self.opacity_slider.valueChanged.connect(self.changeOpacity)
        self.opacity_slider.setStyleSheet("border: none;")
        self.opacity_value_label = QLabel(f"{255}", self)
        self.opacity_value_label.setStyleSheet("color: black; border: none; font-weight: bold;")
        self.opacity_value_label.setAlignment(Qt.AlignCenter)
        
        colors = [ # base colors
            "#000000", "#ffffff", 
            "#808080", "#C0C0C0", 
            "#800000", "#804000",
            "#ff0000", "#ffB6C1", 
            "#ffA500", "#ffB347", 
            "#ffff00", "#EEE8AA",
            "#00ff00", "#ADff2f", 
            "#0080ff", "#00ffff", 
            "#0000ff", "#8080ff",
            "#800080", "#ff00ff"
        ]
        
        self.color_buttons = [] # custom colors storage
        color_grid = QGridLayout()
        for i, color in enumerate(colors + [""] * 10):
            color_button = QPushButton(self)
            color_button.setFixedSize(40, 40)
            color_button.color = color
            if color: 
                color_button.setStyleSheet(f"background-color: {color}; border: 2px solid darkslategray;")
                #color_button.clicked.connect(lambda _, btn=color_button, col=color: self.selectColor(btn, col)) #add loop
                color_button.clicked.connect(partial(self.selectColor, color_button, color))
            else:
                color_button.setStyleSheet(f"background-color: white; border: 2px solid darkslategray;")
                color_button.setEnabled(False)
            self.color_buttons.append(color_button)
            color_grid.addWidget(color_button, i // 2, i % 2)

        right_bar.addWidget(pen_size_label)
        right_bar.addWidget(self.pen_size_slider)
        right_bar.addWidget(self.pen_size_value_label)
        right_bar.addWidget(opacity_label)
        right_bar.addWidget(self.opacity_slider)
        right_bar.addWidget(self.opacity_value_label)

        right_bar.addLayout(color_grid)

        custom_color_button = QPushButton("Add Custom Color", self)
        custom_color_button.clicked.connect(self.addCustomColor)
        custom_color_button.setFixedSize(200, 30)
        custom_color_button.setStyleSheet("background-color: silver; font-weight: bold;")
        right_bar.addWidget(custom_color_button, alignment=Qt.AlignCenter)
        right_bar.addStretch()

        main_layout.addWidget(left_bar_widget)
        main_layout.addWidget(scroll_area, stretch=1)  # give the canvas majority space
        main_layout.addWidget(right_bar_widget)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        central_widget.setStyleSheet("background-color: dimgrey; border: none;")
        self.setCentralWidget(central_widget)

    def createMenus(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("background-color: silver; color: black; font-weight: bold;")
        
        newGridAction = QAction("New", self)
        newGridAction.setShortcut("Ctrl+N")
        newGridAction.triggered.connect(self.newCanvas)
        menubar.addAction(newGridAction)

        saveAction = QAction("Save", self)
        saveAction.setShortcut("Ctrl+S")
        saveAction.triggered.connect(self.saveCanvas)
        menubar.addAction(saveAction)

        openAction = QAction("Open", self)
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

    def newCanvas(self):
        grid_size, ok = QInputDialog.getInt(self, "New Canvas", "Enter the new canvas' size (default 64x64, min 8x8, max 256x256):", 64, 8, 256, 8)
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
                                                        Qt.IgnoreAspectRatio)
                scaled_image.save(filePath)
            else:
                raise Exception("Failed to save the file.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unable to save the image. Error: {e}")

    def openImage(self):
        try:
            imagePath, _ = QFileDialog.getOpenFileName(self, "Save Image", "", "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")
            if imagePath:
                pixmap = QPixmap(imagePath)
                if pixmap.isNull():
                    raise Exception("Invalid image format.")
                if pixmap.width() != pixmap.height():
                    raise ValueError("The image must be square (width and height must be equal).")
                    
                grid_size = pixmap.width()
                cell_size = self.canvas.cell_size
                self.canvas.clearCanvas(grid_size, cell_size)
                self.canvas.image = pixmap.scaled(grid_size * cell_size, grid_size * cell_size)

                self.showMaximized()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open the image. Error: {e}")

    
    def changePenSize(self, value):
        self.canvas.pen_size = value
        self.pen_size_value_label.setText(f"{value}")
        self.canvas.setFocus()

    def changeOpacity(self, value):
        self.opacity_value_label.setText(f"{value}")
        self.canvas.changeOpac(value)

    def addCustomColor(self):
        color = QColorDialog.getColor()
        if color.isValid():
            for button in self.color_buttons:
                if not button.isEnabled():
                    button.color = color.name()
                    button.setStyleSheet(f"background-color: {color.name()}; border: 2px solid darkslategray;")
                    button.clicked.connect(partial(self.selectColor, button, color.name()))
                    button.setEnabled(True)
                    break
    
    def selectTool(self, button, action):
        if self.selected_tool_button: # reset highlight
            self.selected_tool_button.setStyleSheet("background-color: white;")
        button.setStyleSheet("background-color: lightblue; border: 2px solid darkblue;") # new highlight
        self.selected_tool_button = button
        action()

    def selectColor(self, button, color):
        if self.selected_color_button: # reset highlight
            self.selected_color_button.setStyleSheet(f"background-color: {self.selected_color_button.color}; border: 2px solid darkslategray;") 
        button.setStyleSheet(f"background-color: {color}; border: 7px solid darkblue;") # new highlight
        self.selected_color_button = button
        self.canvas.setPenColor(color)

    def updateZoomLabel(self, zoom_level):
        self.zoom_level_label.setText(f"Zoom:\n{int(zoom_level * 100)}%")

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()