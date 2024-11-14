    def openImage(self):
        imagePath, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        
        if imagePath:
            pixmap = QPixmap(imagePath)
            
            # Check if the image is square (grid)
            image_width = pixmap.width()
            image_height = pixmap.height()
            
            if image_width == image_height:  # Only square images are allowed
                # Update grid size and canvas
                grid_size = image_width
                self.canvas.clear_canvas(grid_size, self.canvas.cell_size)
                
                # Scale the image based on current zoom level
                scaled_pixmap = pixmap.scaled(self.canvas.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.canvas.setPixmap(scaled_pixmap)
                
                # Adjust window size based on image size and current zoom level
                new_window_width = grid_size * self.canvas.cell_size * self.canvas.zoom_level + self.canvas.frameWidth() * 2
                new_window_height = grid_size * self.canvas.cell_size * self.canvas.zoom_level + self.menuBar().height() + self.canvas.frameWidth() * 2
                self.resize(new_window_width, new_window_height)
            else:
                # Handle non-square images
                QMessageBox.warning(self, "Error", "The image must be square (width and height must be equal).")