import sys
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap

title = "Paint"

gridsize = int(32)
defaultCellSize = int(10)
 
class Canvas(QtWidgets.QLabel):
    current_color = '#000000'
    current_eraser = Qt.transparent
    width = 0
    height = 0
    isDrawing = True
    isErasing = False
    isFilling = False
    MIN_ZOOM = 0.125
    MAX_ZOOM = 8.0
    cell_size = defaultCellSize
    pen_size=1
    current_opac = 255
    isDrawingLine = False
    start_point = None 
    end_point = None 

    def __init__(self, grid_size=32, cell_size=defaultCellSize):
        super().__init__()
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.zoom_level = 1
        self.border_buffer = 20  
        self.undo_stack = []
        self.redo_stack = []
        self.init_canvas()

    def caroPattern(self):
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

    def paintEvent(self, event):
        self.caroPattern()
        
    def init_canvas(self):
        self.width, self.height = self.grid_size * self.cell_size, self.grid_size * self.cell_size
        self.setFixedSize(self.width, self.height)
        self.image = QtGui.QPixmap(self.width, self.height)
        self.image.fill(Qt.transparent)
        self.setPixmap(self.image)
        self.pen_color = QtGui.QColor('#000000')
        self.set_custom_cursor("icons/cursor.png")
        self.caroPattern()  # Redraw the checkerboard pattern
        self.updateTransform()

    # Use padding/margin to enhance the border appearance
        self.setStyleSheet("""
        QLabel {
            border: 0px solid gray;
            padding: 0px;  /* Ensure no padding */
            margin: 0px;   /* Ensure no margin */
        }
    """)

    def updateTransform(self):
        # Recalculate the size based on the new zoom level
        scaled_width = int(self.grid_size * self.cell_size * self.zoom_level)
        scaled_height = int(self.grid_size * self.cell_size * self.zoom_level)

        # Ensure the QLabel size matches the new dimensions
        self.setFixedSize(scaled_width, scaled_height)

        # No scaling of QPixmap directly here, because the painter handles scaling
        self.update()  # Trigger repaint with new scaling

    def set_pen_color(self, color):
        self.pen_color = QtGui.QColor(color)
        self.current_color = color
        self.change_opac(self.current_opac)

    def clear_canvas(self, grid_size, cell_size):
        self.grid_size = grid_size
        self.cell_size = cell_size
        self.width = grid_size*cell_size
        self.height = self.width
        self.image = QtGui.QPixmap(grid_size * cell_size, grid_size * cell_size)
        self.image.fill(Qt.transparent)
        self.setPixmap(self.image)
        self.caroPattern()  
        self.updateTransform()

    def mouseMoveEvent(self, e):
        self.save_state()
        if self.isDrawing:
            self.DrawEvent(e)
        elif self.isErasing:
            self.EraserEvent(e)

    def mousePressEvent(self, e):
        self.save_state()
        if self.isFilling:
            x = int((e.x() / self.zoom_level) // self.cell_size) * self.cell_size
            y = int((e.y() / self.zoom_level) // self.cell_size) * self.cell_size
            self.fill_canvas_part(x, y)
        elif self.isDrawing:
            self.DrawEvent(e)
        elif self.isErasing:
            self.EraserEvent(e)
        elif self.isDrawingLine:
            self.start_point = e.pos()

    def mouseReleaseEvent(self, event):
        if self.isDrawingLine and self.start_point:
            self.end_point = event.pos()
            self.draw_line(self.start_point, self.end_point)
            self.start_point = None 
            self.end_point = None
    
    def DrawEvent(self, e):
        x = int(e.x() / self.zoom_level // self.cell_size) * self.cell_size
        y = int(e.y() / self.zoom_level // self.cell_size) * self.cell_size
        painter = QtGui.QPainter(self.image)
        painter.fillRect(x, y, self.cell_size*self.pen_size, self.cell_size*self.pen_size, self.pen_color)
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

    def fill_canvas_part(self, x, y):
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
                painter = QtGui.QPainter(self.image)
                painter.fillRect(cx, cy, self.cell_size, self.cell_size, self.pen_color)
                painter.end()
                visited.add((cx, cy))
                stack.extend([(cx + self.cell_size, cy), (cx - self.cell_size, cy), 
                            (cx, cy + self.cell_size), (cx, cy - self.cell_size)])

        self.updateTransform()
    
    def draw_line(self, start_point, end_point):
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
        self.set_custom_cursor("icons/cursor.png")

    def changeToErase(self):
        self.setDrawingMode(2)
        self.set_custom_cursor("icons/eraser.png")

    def changeToFill(self):
        self.setDrawingMode(3)
        self.set_custom_cursor("icons/fill.png")

    def set_mode(self, mode):
        self.mode = mode
        if mode == "pen":
            self.changeToPen()
        elif mode == "eraser":
            self.changeToErase()
        elif mode == "fill":
            self.changeToFill()
        elif mode == "zoom_in":
            self.zoom_in()
        elif mode == "zoom_out":
            self.zoom_out()

    def setDrawingMode(self, action):
        if action == 1: # Pen
            self.isDrawing = True
            self.isErasing = False
            self.isFilling = False
            self.isDrawingLine = False
        elif action == 2: # Eraser
            self.isDrawing = False
            self.isErasing = True
            self.isFilling = False
            self.isDrawingLine = False
        elif action == 3: # FIll
            self.isDrawing = False
            self.isErasing = False
            self.isFilling = True
            self.isDrawingLine = False
        elif action == 4:
            self.isDrawing = False
            self.isErasing = False
            self.isFilling = False
            self.isDrawingLine = True

    def set_custom_cursor(self, icon_path, size=32):
        cursor_pixmap = QtGui.QPixmap(icon_path).scaled(size, size, QtCore.Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setCursor(QtGui.QCursor(cursor_pixmap))

    def save_state(self):
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

    def fill_canvas(self):
        painter = QtGui.QPainter(self.pixmap())
        painter.fillRect(0, 0, self.width, self.height, self.pen_color)
        painter.end()
        self.update()

    def resizeCanvas (self, grid_size):
        return self.pixmap().scaled(grid_size, grid_size, QtCore.Qt.KeepAspectRatio)
    def zoom(self, zoom_factor):
        self.zoom_level *= zoom_factor
        self.zoom_level = max(self.MIN_ZOOM, min(self.zoom_level, self.MAX_ZOOM))
        self.updateTransform()

    def reset_zoom(self):
        self.zoom_level = 1
        self.updateTransform()
    
    def change_opac(self, value):
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
        self.setup_ui()
        self.create_menus()
        self.adjust_window_size_to_canvas()
        self.show()

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+="), self).activated.connect(lambda: self.canvas.zoom(2))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl++"), self).activated.connect(lambda: self.canvas.zoom(2))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+="), self).activated.connect(lambda: self.canvas.zoom(2))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+-"), self).activated.connect(lambda: self.canvas.zoom(0.5))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+0"), self).activated.connect(self.canvas.reset_zoom)
    
    def change_pen_size(self, value):
        """Update the pen size in the canvas."""
        self.canvas.pen_size = value
        self.pen_size_value_label.setText(f"{value}")
        self.canvas.setFocus()

    def change_opacity(self, value):
        self.opacity_value_label.setText(f"{value}")
        self.canvas.change_opac(value)

    def setup_ui(self):
        self.top_bar = QWidget(self)
        self.top_bar_layout = QHBoxLayout(self.top_bar)
        self.color_picker_layout = QVBoxLayout()
        self.color_row_1 = QHBoxLayout()
        colors_row_1 = [
            '#000000', '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#00FFFF', 
            '#FF6347', '#FFD700', '#FF1493', '#A52A2A', '#8A2BE2', '#C71585'
        ]
        for color in colors_row_1:
            color_button = QPushButton(self)
            color_button.setStyleSheet(f"background-color: {color};")
            color_button.clicked.connect(lambda _, col=color: self.canvas.set_pen_color(col))
            self.color_row_1.addWidget(color_button)

        self.color_row_2 = QHBoxLayout()
        colors_row_2 = [
            '#FFFFFF', '#C0C0C0', '#808080', '#800000', '#008000', '#A52A2A', 
            '#9ACD32', '#4B0082', '#D2691E', '#32CD32', '#7B68EE', '#FF8C00'
        ]
        for color in colors_row_2:
            color_button = QPushButton(self)
            color_button.setStyleSheet(f"background-color: {color};")
            color_button.clicked.connect(lambda _, col=color: self.canvas.set_pen_color(col))
            self.color_row_2.addWidget(color_button)

        # Pen Size Slider
        self.pen_size_label = QLabel("Pen Size:", self)
        self.pen_size_slider = QSlider(Qt.Horizontal, self)
        self.pen_size_slider.setRange(1, 10) 
        self.pen_size_slider.setValue(self.canvas.pen_size) 
        self.pen_size_slider.valueChanged.connect(self.change_pen_size)\

        self.pen_size_value_label = QLabel(str(self.canvas.pen_size), self)

        # Opacity Slider
        self.opacity_label = QLabel("Opacity:", self)
        self.opacity_slider = QSlider(Qt.Horizontal, self)
        self.opacity_slider.setRange(0, 255)  
        self.opacity_slider.setValue(255) 
        self.opacity_slider.valueChanged.connect(self.change_opacity)

        self.opacity_value_label = QLabel(f"{255}", self)

        # Add sliders to a layout
        self.sliders_layout = QVBoxLayout()
        self.sliders_layout.addWidget(self.pen_size_label)
        self.sliders_layout.addWidget(self.pen_size_slider)
        self.sliders_layout.addWidget(self.opacity_label)
        self.sliders_layout.addWidget(self.opacity_slider)

        # Add layouts to the top bar
        self.top_bar_layout.addLayout(self.color_picker_layout)
        self.top_bar_layout.addLayout(self.sliders_layout)

        self.color_picker_layout.addLayout(self.color_row_1)
        self.color_picker_layout.addLayout(self.color_row_2)

        self.custom_color_button = QPushButton("Custom Color", self)
        self.custom_color_button.clicked.connect(self.open_color_dialog)
        self.custom_color_button.setFixedSize(100, 30) 
        self.custom_color_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.color_row_2.addWidget(self.custom_color_button, alignment=Qt.AlignRight)

        self.spacer = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.top_bar_layout.addLayout(self.color_picker_layout)
        self.top_bar_layout.addItem(self.spacer)

        self.mode_layout = QVBoxLayout()

        self.pen_button = QPushButton("Pen", self)
        self.pen_button.clicked.connect(lambda: self.canvas.set_mode("pen"))
        self.eraser_button = QPushButton("Eraser", self)
        self.eraser_button.clicked.connect(lambda: self.canvas.set_mode("eraser"))
        self.fill_button = QPushButton("Fill", self)
        self.fill_button.clicked.connect(lambda: self.canvas.set_mode("fill"))
        self.zoom_in_button = QPushButton("Zoom In", self)
        self.zoom_in_button.clicked.connect(lambda: self.canvas.zoom(2))
        self.zoom_out_button = QPushButton("Zoom Out", self)
        self.zoom_out_button.clicked.connect(lambda: self.canvas.zoom(0.5))
        self.zoom_out_button = QPushButton("Draw line", self)
        self.zoom_out_button.clicked.connect(lambda: self.canvas.setDrawingMode(4))


        self.mode_layout.addWidget(self.pen_button)
        self.mode_layout.addWidget(self.eraser_button)
        self.mode_layout.addWidget(self.fill_button)
        self.mode_layout.addWidget(self.zoom_in_button)
        self.mode_layout.addWidget(self.zoom_out_button)

        self.top_bar_layout.addLayout(self.mode_layout)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter) 
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame) 

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.top_bar)  
        main_layout.addWidget(self.scroll_area) 
        central_widget = QWidget(self)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    

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
        canvas_width = self.canvas.width
        canvas_height = self.canvas.height

        frame_width = self.scroll_area.frameWidth() * 2
        menu_bar_height = self.menuBar().height()

        total_width = canvas_width + frame_width
        total_height = canvas_height + menu_bar_height + frame_width

        self.setGeometry(
            QStyle.alignedRect(
                Qt.LeftToRight,
                Qt.AlignCenter,
                QSize(total_width, total_height),
                QtWidgets.QApplication.primaryScreen().availableGeometry()
            )
        )
        
    def new_grid_dialog(self):
        gs, ok = QInputDialog.getInt(
            self, "New Grid", "Enter grid size (e.g., 32 for 32x32)", 32, 8, 512, 8
        )
        if ok:
            gridsize = gs
            max_grid_size = 128
            if gridsize > max_grid_size:
                gridsize = max_grid_size # limit size
                QMessageBox.warning(self, "Warning", f"Grid size is too large. Limiting to {max_grid_size}.")

            self.canvas.clear_canvas(gridsize, defaultCellSize)

            # prevent the new window from expanding past the screen
            new_width = gridsize * self.canvas.cell_size + self.canvas.frameWidth() * 2
            new_height = gridsize * self.canvas.cell_size + self.menuBar().height() + self.canvas.frameWidth() * 2
            screen_geometry = QApplication.primaryScreen().geometry()
            max_width = screen_geometry.width() - 50  # 50px margin to avoid overflow
            max_height = screen_geometry.height() - 50 
            new_width = min(new_width, max_width)
            new_height = min(new_height, max_height)
            self.resize(new_width, new_height)

    def open_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.canvas.set_pen_color(color.name())
            self.canvas.setFocus()
    
    def canvas_save(self):
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")
        if filePath:
            scaled_image = self.canvas.image.scaled(self.canvas.width // self.canvas.cell_size, 
                                                    self.canvas.height // self.canvas.cell_size, 
                                                    QtCore.Qt.IgnoreAspectRatio)
            scaled_image.save(filePath)

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