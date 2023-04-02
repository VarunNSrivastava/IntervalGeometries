# graph.py

import numpy as np
import simpleaudio as sa
from PyQt5.QtCore import Qt, QPointF, QRectF, QLineF
from PyQt5.QtGui import QPainter, QPen, QPainterPath, QColor, QFont, QPolygonF
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem

EPS = 1e-3


def _circle_circle_intersection(circle1: QGraphicsEllipseItem, circle2: QGraphicsEllipseItem) -> list:
    path1 = circle1.shape()
    path2 = circle2.shape()

    if circle1.collidesWithPath(path2):
        intersections = find_path_intersections(path1, path2)
        return intersections
    else:
        return []


def _line_line_intersection(line1: QGraphicsLineItem, line2: QGraphicsLineItem) -> list:
    # QLineF
    lf1 = line1.line()
    lf2 = line2.line()
    intersection_point = QPointF()
    if lf1.intersect(lf2, intersection_point) == 1:
        return [intersection_point]
    else:
        return []

def _circle_line_intersection(circle: QGraphicsEllipseItem, line: QGraphicsLineItem) -> list:
    polys = circle.shape().toSubpathPolygons()
    # print(f"there are {len(polys)} polygons")
    path1 = circle.shape()
    path2 = line.shape()
    if circle.collidesWithPath(path2):
        intersections = find_path_intersections(path1, path2)
        return intersections
    else:
        return []

def remove_duplicates(intersections, epsilon=5):
    unique_intersections = []
    for point in intersections:
        if not any((abs(point.x() - p.x()) < epsilon and abs(point.y() - p.y()) < epsilon) for p in unique_intersections):
            unique_intersections.append(point)
    return unique_intersections

def find_path_intersections(path1: QPainterPath, path2: QPainterPath) -> list:

    intersections = []

    for i, subpath1 in enumerate(path1.toSubpathPolygons()):
        for j, subpath2 in enumerate(path2.toSubpathPolygons()):
            polygon1 = QPolygonF(subpath1)
            polygon2 = QPolygonF(subpath2)

            # Find intersections between two polygons
            intersections += find_polygon_intersections(polygon1, polygon2)

    # Remove duplicate intersection points
    intersections = remove_duplicates(intersections)

    # print(len(intersections))
    return intersections


def find_polygon_intersections(polygon1, polygon2):
    intersections = []

    for i in range(polygon1.size()):
        line1 = QLineF(polygon1[i - 1], polygon1[i])

        for j in range(polygon2.size()):
            line2 = QLineF(polygon2[j - 1], polygon2[j])

            intersection_point = QPointF()
            result = line1.intersect(line2, intersection_point)

            if result == QLineF.IntersectType.BoundedIntersection:
                intersections.append(intersection_point)

    return intersections


def find_intersections(item1, item2):
    if item1 == item2:
        return []
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

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setRenderHint(QPainter.Antialiasing)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.current_mode = "Play mode"
        self.duration = 0.5

        self.circle_radius = 50
        self.circle_item = None
        self.line_item = None
        self.start_line_point = None

        self.primitives = []
        self.snap_points = []

        self._width = 800
        self._height = 800
        self.setFixedSize(self._width, self._height)

        # tonal center
        self.x_center = 440
        self.y_center = 440 *8

        # number of octaves
        self.x_range = 15
        self.y_range = 15

        # octaves
        self.x_scale = [self.x_center * (2 ** i) for i in range(-int(self.x_range / 2), 1 + int(self.x_range / 2))]
        self.y_scale = [self.y_center * (2 ** i) for i in range(-int(self.y_range / 2), 1 + int(self.y_range / 2))]

        self.play_obj = None
        self.playing_audio = False

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

        self.plot_snap_points()

    def map_frequency_to_x(self, freq):
        return self.width() * (0.5 + np.log2(freq / self.x_center) / self.x_range)

    def map_frequency_to_y(self, freq):
        return -self.height() * (-0.5 + np.log2(freq / self.y_center) / self.y_range)

    def map_x_to_frequency(self, x):
        # print(self.width(), self.x_center, self.x_range)
        return self.x_center * (2 ** (self.x_range * ((x / self.width()) - 0.5)))

    def map_y_to_frequency(self, y):
        return self.y_center * (2 ** (self.y_range * (-(y / self.height()) + 0.5)))

    def set_mode(self, mode):
        self.current_mode = mode
        if self.playing_audio:
            self.stop_audio()

    def stop_audio(self):
        if self.play_obj is not None:
            self.play_obj.stop()
            self.play_obj = None
        self.playing_audio = False

    def set_circle_radius(self, radius):
        self.circle_radius = radius

    def play_frequency(self, x, y, duration=None):
        if self.playing_audio:
            self.stop_playing_audio()

        freq1 = 0 #self.map_x_to_frequency(x)
        freq2 = self.map_y_to_frequency(y)
        sample_rate = 44100
        fade_duration = 0.01  # Fade duration in seconds

        if duration is None:
            t = np.linspace(0, 1, sample_rate, False)
        else:
            t = np.linspace(0, duration, int(duration * sample_rate), False)

        audio_data = np.sin(freq1 * t * 2 * np.pi) + np.sin(freq2 * t * 2 * np.pi)

        # Apply fade in and fade out effect
        fade_samples = int(fade_duration * sample_rate)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)

        audio_data[:fade_samples] *= fade_in
        audio_data[-fade_samples:] *= fade_out

        # Normalize the audio data and convert to int16
        audio_data = audio_data * (2 ** 15 - 1) / np.max(np.abs(audio_data))
        audio_data = audio_data.astype(np.int16)

        play_obj = sa.play_buffer(audio_data, 1, 2, sample_rate)
        self.play_obj = play_obj
        self.playing_audio = True

    def stop_playing_audio(self):
        if self.playing_audio:
            self.play_obj.stop()
            self.playing_audio = False

    def plot_snap_points(self):
        for point in self.snap_points:
            x, y = point.x(), point.y()
            snap_point = QGraphicsEllipseItem(x - 2, y - 2, 4, 4)
            snap_point.setBrush(Qt.red)
            snap_point.setPen(QPen(Qt.red, 1, Qt.SolidLine))
            # causing interferences, we dont
            # want these
            # intersections to count "double count"

            # so the idea shold be
            # instead of checking scene.items
            # we loop through this "primitives" list

            #

            self.scene.addItem(snap_point)

    def add_snap_points_from_item(self, item):
        # Iterate through existing items on the graph
        for existing_item in self.scene.items():
            # for tm in self.scene.collidingItems(existing_item, 1):
            #
            #
            # self.scene.collidingItems()
            # existing_item.

            intersections = find_intersections(item, existing_item)
            # todo: filter out existing "snap points"

            if intersections:
                self.snap_points.extend(intersections)

        self.plot_snap_points()

    def add_circle(self, center_x, center_y, radius):
        circle = QGraphicsEllipseItem(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))
        circle.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        self.scene.addItem(circle)
        return circle

    def add_line(self, start_x, start_y, end_x, end_y):
        line = QGraphicsLineItem(start_x, start_y, end_x, end_y)
        line.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        self.scene.addItem(line)
        return line

    def snapped(self, x, y):
        # returns snapped version of x and y
        nearest_snap_point = None
        min_distance = float('inf')

        # Find the nearest snap point
        for snap_point in self.snap_points:
            distance = (x - snap_point.x()) ** 2 + (y - snap_point.y()) ** 2
            if distance < min_distance:
                min_distance = distance
                nearest_snap_point = snap_point

        snap_threshold = 10  # adjust
        if min_distance <= snap_threshold ** 2:
            #print([(self.map_x_to_frequency(point.x()), self.map_y_to_frequency(point.y())) for point in self.snap_points])
            x, y = nearest_snap_point.x(), nearest_snap_point.y()
            # print(f"snapped to {self.map_x_to_frequency(x)}, {self.map_y_to_frequency(y)}")

        return x, y

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x, y = self.snapped(event.x(), event.y())
            if self.current_mode == "Play mode":
                self.play_frequency(x, y, duration=self.duration)
            elif self.current_mode == "Circle mode":
                self.circle_item = self.add_circle(x, y, self.circle_radius)
            elif self.current_mode == "Line mode":
                self.start_line_point = QPointF(x, y)
                self.line_item = self.add_line(x, y, x, y)
            elif self.current_mode == "Drag mode":
                self.play_frequency(x, y)

    def mouseMoveEvent(self, event):
        x, y = event.x(), event.y()

        if self.current_mode == "Circle mode" and self.circle_item is not None:
            # TODO: add a dotted line from origin to destination
            # Calculate the new radius based on the mouse position and circle center
            center_x, center_y = self.circle_item.rect().center().x(), self.circle_item.rect().center().y()
            new_radius = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5

            # Update the circle's radius
            self.circle_item.setRect(center_x - new_radius, center_y - new_radius, new_radius * 2, new_radius * 2)

        elif self.current_mode == "Line mode" and self.line_item is not None:
            # Update the line's end point based on the mouse position
            self.line_item.setLine(self.start_line_point.x(), self.start_line_point.y(), x, y)
        elif self.current_mode == "Drag mode" and self.playing_audio:
            x, y = self.snapped(x, y)
            self.play_frequency(x, y)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # print(event.x(), event.y())
            x, y = self.snapped(event.x(), event.y())

            if self.current_mode == "Circle mode":
                self.add_snap_points_from_item(self.circle_item)
                self.circle_item = None
            elif self.current_mode == "Line mode":
                # if line is degenerate, just remove / dont place, whatever
                # here is where to update intersections
                # and also update the end of the line to snap
                if self.start_line_point != QPointF(x, y):
                    # line isnt degenerate
                    self.line_item.setLine(self.start_line_point.x(), self.start_line_point.y(), x, y)
                    self.add_snap_points_from_item(self.line_item)

                self.line_item = None
                self.start_line_point = None
            elif self.current_mode == "Drag mode":
                self.stop_audio()

    # also need a resize / rescale event
    # because _width and _height should be changable, but we should know when that happens
