# graph.py

import numpy as np
import simpleaudio as sa
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QPainterPath, QColor, QFont
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem

EPS = 1e-3


def _circle_circle_intersection(circle1: QGraphicsEllipseItem, circle2: QGraphicsEllipseItem) -> list:
    cx1, cy1, _, _ = circle1.rect().getCoords()
    cx2, cy2, _, _ = circle2.rect().getCoords()
    r1 = circle1.rect().width() / 2
    r2 = circle2.rect().width() / 2

    dx = cx2 - cx1
    dy = cy2 - cy1
    d = np.sqrt(dx * dx + dy * dy)

    if abs(d) < EPS:
        return []

    if d > r1 + r2:
        return []

    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = np.sqrt(r1 * r1 - a * a)
    x2 = cx1 + a * (dx) / d
    y2 = cy1 + a * (dy) / d

    rx = -dy * (h / d)
    ry = dx * (h / d)

    xi1 = x2 + rx
    xi2 = x2 - rx
    yi1 = y2 + ry
    yi2 = y2 - ry

    if abs(d - (r1 + r2)) < EPS:  # "d is almost exactly r1 + r2"
        return [QPointF(xi1, yi1)]
    else:
        return [QPointF(xi1, yi1), QPointF(xi2, yi2)]


def _circle_line_intersection(circle: QGraphicsEllipseItem, line: QGraphicsLineItem) -> list:
    cx, cy, _, _ = circle.rect().getCoords()
    x1, y1, x2, y2 = line.line().x1(), line.line().y1(), line.line().x2(), line.line().y2()
    r = circle.rect().width() / 2

    dx = x2 - x1
    dy = y2 - y1
    dr = np.sqrt(dx * dx + dy * dy)
    D = x1 * y2 - x2 * y1

    discriminant = r * r * dr * dr - D * D

    intersections = []
    if abs(discriminant) < EPS:  # discr is almost 0
        qx = (D * dy) / (dr * dr)
        qy = (-D * dx) / (dr * dr)
        intersections.append(QPointF(qx, qy))
    elif discriminant > 0:
        sign_dy = 1 if dy >= 0 else -1
        sqrt_discriminant = np.sqrt(discriminant)
        qx1 = (D * dy + sign_dy * dx * sqrt_discriminant) / (dr * dr)
        qx2 = (D * dy - sign_dy * dx * sqrt_discriminant) / (dr * dr)
        qy1 = (-D * dx + np.abs(dy) * sqrt_discriminant) / (dr * dr)
        qy2 = (-D * dx - np.abs(dy) * sqrt_discriminant) / (dr * dr)
        intersections.append(QPointF(qx1, qy1))
        intersections.append(QPointF(qx2, qy2))

    return intersections


def _line_line_intersection(line1: QGraphicsLineItem, line2: QGraphicsLineItem) -> list:
    x1, y1, x2, y2 = line1.line().x1(), line1.line().y1(), line1.line().x2(), line1.line().y2()
    x3, y3, x4, y4 = line2.line().x1(), line2.line().y1(), line2.line().x2(), line2.line().y2()

    det = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(det) < EPS:
        return []

    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / det
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / det

    if (min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2) and
            min(x3, x4) <= px <= max(x3, x4) and min(y3, y4) <= py <= max(y3, y4)):
        return [QPointF(px, py)]
    else:
        return []


def find_intersections(item1, item2):
    # returns a list of intersections of item1 and item2
    if isinstance(item1, QGraphicsEllipseItem) and isinstance(item2, QGraphicsEllipseItem):
        return _circle_circle_intersection(item1, item2)
    elif isinstance(item1, QGraphicsEllipseItem) and isinstance(item2, QGraphicsLineItem):
        return _circle_line_intersection(item1, item2)
    elif isinstance(item1, QGraphicsLineItem) and isinstance(item2, QGraphicsEllipseItem):
        return _circle_line_intersection(item2, item1)
    elif isinstance(item1, QGraphicsLineItem) and isinstance(item2, QGraphicsLineItem):
        return _line_line_intersection(item1, item2)
    return []


class FrequencyGraph(QGraphicsView):
    MIN_FREQ = 10
    MAX_FREQ = 10000

    SNAP_TOL = 20

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setRenderHint(QPainter.Antialiasing)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.current_mode = "Play mode"
        self.circle_radius = 50
        self.circle_item = None
        self.line_item = None
        self.start_line_point = None

        self.snap_points = []

        self.x_scale = [440 * (2 ** i) for i in range(-4, 5)]  # octaves of A
        self.y_scale = [440 * (2 ** i) for i in range(-4, 5)]  # octaves of A

        self.draw_graph()

    def draw_graph(self):
        pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)

        # Draw axis labels & horizontal/vertical grid lines
        font = QFont()
        font.setPointSize(10)
        for x_freq, y_freq in zip(self.x_scale, self.y_scale):
            x = self.map_frequency_to_x(x_freq)
            y = self.map_frequency_to_y(y_freq)

            # add to scene
            self.scene.addLine(x, 0, x, self.height(), pen)
            self.scene.addLine(0, y, self.width(), y, pen)

            text_item_x = self.scene.addText(str(x_freq), font)
            text_item_y = self.scene.addText(str(y_freq), font)
            text_item_x.setPos(x, self.height() - 20)
            text_item_y.setPos(0, y - 10)

        for x_freq in self.x_scale:
            for y_freq in self.y_scale:
                snap_point = QPointF(self.map_frequency_to_x(x_freq),
                                     self.map_frequency_to_y(y_freq))
                self.snap_points.append(snap_point)

        # Draw center point (440, 400)
        center_x, center_y = self.map_frequency_to_x(440), self.map_frequency_to_y(440)
        path = QPainterPath()
        path.addEllipse(center_x - 2.5, center_y - 2.5, 5, 5)
        self.scene.addPath(path, QPen(Qt.black, 1))

    def map_frequency_to_x(self, freq):
        log_min, log_max = np.log2(self.MIN_FREQ), np.log2(self.MAX_FREQ)
        return self.width() * (np.log2(freq) - log_min) / (log_max - log_min)

    def map_frequency_to_y(self, freq):
        log_min, log_max = np.log2(self.MIN_FREQ), np.log2(self.MAX_FREQ)
        return self.height() * (1 - (np.log2(freq) - log_min) / (log_max - log_min))

    def set_mode(self, mode):
        self.current_mode = mode

    def set_circle_radius(self, radius):
        self.circle_radius = radius

    def play_frequency(self, x, y):
        freq1 = self.map_x_to_frequency(x)
        freq2 = self.map_y_to_frequency(y)
        print(f"Playing frequencies {freq1}  +  {freq2}")
        duration = 0.5
        sample_rate = 44100

        t = np.linspace(0, duration, int(duration * sample_rate), False)
        audio_data = np.sin(freq1 * t * 2 * np.pi) + np.sin(freq2 * t * 2 * np.pi)
        audio_data = audio_data * (2 ** 15 - 1) / np.max(np.abs(audio_data))
        audio_data = audio_data.astype(np.int16)

        play_obj = sa.play_buffer(audio_data, 1, 2, sample_rate)
        play_obj.wait_done()

    def map_x_to_frequency(self, x):
        log_min, log_max = np.log2(self.MIN_FREQ), np.log2(self.MAX_FREQ)
        return 2 ** ((x * (log_max - log_min) / self.width()) + log_min)

    def map_y_to_frequency(self, y):
        log_min, log_max = np.log2(self.MIN_FREQ), np.log2(self.MAX_FREQ)
        return 2 ** (((1 - y / self.height()) * (log_max - log_min)) + log_min)

    def plot_snap_points(self):
        for point in self.snap_points:
            x, y = point.x(), point.y()
            snap_point = QGraphicsEllipseItem(x - 2, y - 2, 4, 4)
            snap_point.setBrush(Qt.red)
            snap_point.setPen(QPen(Qt.red, 1, Qt.SolidLine))
            self.scene.addItem(snap_point)

    def add_snap_points_from_item(self, item):
        # Iterate through existing items on the graph
        for existing_item in self.scene.items():
            intersections = find_intersections(item, existing_item)
            if intersections:
                print("added snap points")
                self.snap_points.extend(intersections)
        self.plot_snap_points()

    def add_circle(self, center_x, center_y, radius):
        circle = QGraphicsEllipseItem(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))
        circle.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        self.scene.addItem(circle)
        self.add_snap_points_from_item(circle)
        return circle

    def add_line(self, start_x, start_y, end_x, end_y):
        line = QGraphicsLineItem(start_x, start_y, end_x, end_y)
        line.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        self.scene.addItem(line)
        self.add_snap_points_from_item(line)
        return line

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()

            # "snap" x and y
            nearest_snap_point = None
            min_distance = float('inf')

            # Find the nearest snap point
            for snap_point in self.snap_points:
                distance = (x - snap_point.x()) ** 2 + (y - snap_point.y()) ** 2
                if distance < min_distance:
                    min_distance = distance
                    nearest_snap_point = snap_point

            # Snap to the nearest snap point if it's within a threshold
            snap_threshold = 20  # adjust
            if min_distance <= snap_threshold ** 2:
                print("snapped!")
                x, y = nearest_snap_point.x(), nearest_snap_point.y()

            if self.current_mode == "Play mode":
                self.play_frequency(x, y)
            elif self.current_mode == "Circle mode":
                self.circle_item = self.add_circle(x, y, self.circle_radius)
            elif self.current_mode == "Line mode":
                self.start_line_point = QPointF(x, y)
                self.line_item = self.add_line(x, y, x, y)

    def mouseMoveEvent(self, event):
        x, y = event.x(), event.y()

        if self.current_mode == "Circle mode" and self.circle_item is not None:
            # Calculate the new radius based on the mouse position and circle center
            center_x, center_y = self.circle_item.rect().center().x(), self.circle_item.rect().center().y()
            new_radius = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5

            # Update the circle's radius
            self.circle_item.setRect(center_x - new_radius, center_y - new_radius, new_radius * 2, new_radius * 2)

        elif self.current_mode == "Line mode" and self.line_item is not None:
            # Update the line's end point based on the mxouse position
            self.line_item.setLine(self.start_line_point.x(), self.start_line_point.y(), x, y)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.current_mode == "Circle mode":
                # here is where to update intersections
                self.circle_item = None
            elif self.current_mode == "Line mode":
                # here is where to update intersections
                # and also update the end of the line to snap

                self.line_item = None
                self.start_line_point = None
