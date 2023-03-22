# gui.py (updated)

from PyQt5.QtWidgets import QMainWindow, QGridLayout, QWidget, QComboBox, QSpinBox, QLabel, QSlider
from PyQt5.QtCore import Qt
from graph import FrequencyGraph

class FrequencyGraphWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Frequency Graph")

        central_widget = QWidget(self)
        layout = QGridLayout(central_widget)

        self.mode_selector = QComboBox()
        self.mode_selector.addItem("Play mode")
        self.mode_selector.addItem("Circle mode")
        self.mode_selector.addItem("Line mode")
        self.mode_selector.currentIndexChanged.connect(self.change_mode)
        layout.addWidget(self.mode_selector, 0, 0)

        self.radius_label = QLabel("Radius:")
        self.radius_label.setHidden(True)
        layout.addWidget(self.radius_label, 0, 1)

        self.radius_slider = QSlider(Qt.Horizontal)
        self.radius_slider.setMinimum(10)
        self.radius_slider.setMaximum(200)
        self.radius_slider.setValue(50)
        layout.addWidget(self.radius_slider, 0, 1)

        # Connect the mode_selector and radius_slider signals to the corresponding slots
        self.mode_selector.currentIndexChanged.connect(self.change_mode)
        self.radius_slider.valueChanged.connect(self.update_circle_radius)

        self.graph = FrequencyGraph()  # Instantiate the FrequencyGraph class
        layout.addWidget(self.graph, 1, 0, 4, 4)

        self.setCentralWidget(central_widget)

    def change_mode(self, index):
        mode = self.mode_selector.itemText(index)
        self.graph.set_mode(mode)

    def update_circle_radius(self, value):
        self.graph.set_circle_radius(value)

