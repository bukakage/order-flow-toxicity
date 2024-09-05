from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QSize, QByteArray, QBuffer, QIODevice
from PIL import Image
import io

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Setup the main widget
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        layout = QVBoxLayout()
        self.main_widget.setLayout(layout)

        # Create a button to take a screenshot
        self.screenshot_button = QPushButton('Take Screenshot')
        layout.addWidget(self.screenshot_button)
        self.screenshot_button.clicked.connect(self.take_screenshot)

        # Set up the window
        self.setWindowTitle('PyQt5 Screenshot Example')
        self.resize(800, 600)

    def take_screenshot(self):
        # Capture the widget as a QPixmap
        pixmap = QPixmap(self.size())
        self.render(pixmap)

        # Convert QPixmap to QImage
        qimage = pixmap.toImage()

        # Convert QImage to QByteArray
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        qimage.save(buffer, 'PNG')
        buffer.close()

        # Convert QByteArray to BytesIO
        byte_array_data = byte_array.data()
        byte_stream = io.BytesIO(byte_array_data)

        # Convert BytesIO to Pillow Image
        pil_image = Image.open(byte_stream)

        # Save the image
        pil_image.save('screenshot.png')

if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
