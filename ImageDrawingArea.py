from PyQt6.QtWidgets import QGraphicsView, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsPolygonItem
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QTransform, QPolygonF
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, QLineF
from PyQt6 import sip
from math import sqrt
from uuid import uuid4 as uuid

PEN_LINE_SIZE = 4

def getVectorMagnitude(vector):
    return sqrt( vector.x()**2 +  vector.y()**2 )

class AnimatedDottedLine(QGraphicsLineItem):
    def __init__(self, start, end):
        super().__init__()
        self.start = start
        self.end = end
        self.setLine(start.x(), start.y(), end.x(), end.y())

        # Create a custom pen with a dash pattern
        global PEN_LINE_SIZE
        self.pen = QPen(QColor(252, 232, 3), PEN_LINE_SIZE)  # Line color and thickness
        self.pen.setDashPattern([4, 4])  # Dash pattern: 4 pixels on, 4 pixels off
        self.setPen(self.pen)

        # Dash offset for animation
        self.dash_offset = 0

    def advance(self):
        if sip.isdeleted(self): # the item was already deleted
            print('item was deleted, do nothing')
            return
        
        # Update the dash offset to create the animation effect
        self.dash_offset += 1  # Adjust speed here
        if self.dash_offset >= 8:  # Reset offset to loop the animation
            self.dash_offset = 0
        self.pen.setDashOffset(self.dash_offset)
        self.setPen(self.pen)


HOTSPOT_NONE = -1
HOTSPOT_END = 0
HOTSPOT_START = 1
HOTSPOT_TOP_RIGHT = 2
HOTSPOT_BOTTOM_LEFT = 3

MIN_AREA_RECT = 50

def arePointsEqual(a,b):
    return (int(a.x()) == int(b.x()) and
            int(a.y()) == int(b.y()))

class Arrow():
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.scene = None
        self.arrow_line_item = None
        self.arrow_point_item = None

    
    def clearFromScene(self):
        if not self.arrow_line_item or sip.isdeleted(self.arrow_line_item):
            return
        self.scene.removeItem(self.arrow_line_item)
        self.scene.removeItem(self.arrow_point_item)

    def render(self):
        self.clearFromScene()
        point_a = self.start
        point_b = self.end
        polygon_line = QPolygonF([
            QPointF(0, -5),
            QPointF(0, 5),
            QPointF(10, 5),
            QPointF(10, -5),
        ])

        polygon_arrow_point = QPolygonF([
            QPointF(-5, -5),
            QPointF(-5, 5),
            QPointF(2, 0),
        ])

        # Create a QGraphicsPolygonItem
        brush = QBrush(QColor(255,0,255))
        pen = QPen(Qt.PenStyle.NoPen)
        poly_item_a = QGraphicsPolygonItem(polygon_line)
        poly_item_a.setBrush(brush)
        poly_item_a.setPen(pen)

        poly_item_b = QGraphicsPolygonItem(polygon_arrow_point)
        poly_item_b.setBrush(brush)
        poly_item_b.setPen(pen)

        # Calculate the scaling factor and rotation angle
        line = QLineF(point_a, point_b)
        scale_x = line.length() / 10  # Scale to fit the length between points
        scale_y = 1.0  # Maintain aspect ratio (or adjust as needed)
        angle = -line.angle()  # Rotation angle (negative because Qt's y-axis is inverted)

        # Apply scaling and rotation using QTransform
        transform_a = QTransform()
        transform_a.translate(point_a.x(), point_a.y())  # Move to the starting point
        transform_a.rotate(angle)  # Rotate
        transform_a.scale(scale_x, scale_y)  # Scale

        poly_item_a.setTransform(transform_a)

        scale_arrow = max(5, min(8, scale_x))
        # Apply scaling and rotation using QTransform
        transform_b = QTransform()
        transform_b.translate(point_b.x(), point_b.y())  # Move to the starting point
        transform_b.scale(scale_arrow,scale_arrow)
        transform_b.rotate(angle)

        poly_item_b.setTransform(transform_b)


        # Add the pixmap item to the scene
        self.scene.addItem(poly_item_a)
        self.arrow_line_item = poly_item_a
        self.scene.addItem(poly_item_b)
        self.arrow_point_item = poly_item_b

class ImageRect():
    def __init__(self, initial_pos, end_pos=None, id=None, detected=None, machine_translation=None):
        self.item_reference = None
        self._origin = initial_pos
        self._end = ( initial_pos + QPointF(1,1) )if not end_pos else end_pos

        self._top_right = QPointF( self._end.x(), self._origin.y() )
        self._bottom_left = QPointF( self._origin.x(), self._end.y() )

        self.color_normal = QColor('black')
        self.color_focus = QColor('orange')
        self.use_color = self.color_normal

        self._is_mouse_hovering = False

        # Create an animated dotted line
        self.animated_lines = []
        self.animated_lines_references = []


        # Set up a timer for animation
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateLineAnim)
        self.timer.start(100)

        self.scene = None
        self.image = None

        # other used data.
        self.id = id if id != None else uuid()
        self.detected_characters = detected
        self.machine_translation = machine_translation
    
    # Calculate the origin point so the area of the rect
    # can never go bellow MIN_AREA_RECT
    def calcOrigin(self, value):
        return QPointF(
            min( self.end.x()-MIN_AREA_RECT, value.x() ),
            min( self.end.y()-MIN_AREA_RECT, value.y() ) )
    
    # Calculate the end point so the area of the rect
    # can never go bellow MIN_AREA_RECT
    def calcEnd(self, value):
        return QPointF(
            max( self._origin.x()+MIN_AREA_RECT, value.x() ),
            max( self._origin.y()+MIN_AREA_RECT, value.y() ) )
    
    @property
    def start(self):
        return self._origin
    
    @start.setter
    def start(self, value):
        if arePointsEqual(self._origin, value):
            return # is equal the new value, do noting
         # never allow the end point to form someting of less than 50 squared units.
        self._origin = self.calcOrigin(value)
        self.recalculateBorders()
        self.render()

    @property
    def end(self):
        return self._end
    
    @end.setter
    def end(self, value):
        if arePointsEqual(self._origin, value):
            return # is equal the new value, do noting
        # never allow the end point to form someting of less than MIN_AREA_RECT squared units.
        self._end = self.calcEnd(value)
        self.recalculateBorders()
        self.render()

    @property
    def bottom(self):
        return self._bottom_left
    
    @bottom.setter
    def bottom(self, point):
        y = self._origin.y()
        x = self._end.x()
        self._origin = self.calcOrigin( QPointF( point.x(), y ) ) 
        self._end = self.calcEnd( QPointF( x, point.y() ) )
        self.recalculateBorders()
        self.render()

    @property
    def top(self):
        return self._top_right
    
    @top.setter
    def top(self, point):
        y = self._end.y()
        x = self._origin.x()
        self._end = self.calcEnd( QPointF( point.x(), y ) ) 
        self._origin = self.calcOrigin( QPointF( x, point.y() ) )
        self.recalculateBorders()
        self.render()
    
    @property
    def is_mouse_hovering(self):
        return self._is_mouse_hovering

    @is_mouse_hovering.setter
    def is_mouse_hovering(self, value):
        old_val = self._is_mouse_hovering
        self._is_mouse_hovering = value
        if old_val != value:
            self.use_color = self.color_normal if not self._is_mouse_hovering else self.color_focus
            self.render()

    # retuns a tuple of this rect in the form x,y,w,h
    def getDefinition(self):
        x = int(self._origin.x())
        y = int(self._origin.y())
        return (x, y, int(self._end.x() - x), int(self._end.y()-y) )
    
    def getCenter(self):
        (x,y,w,h) = self.getDefinition()
        return QPointF( x+(w/2), y+(h/2) )

    def updateLineAnim(self):
        for line in self.animated_lines:
            line.advance()
    
    def createLines(self):
        self.animated_lines = [
            AnimatedDottedLine(self._origin, self._top_right),
            AnimatedDottedLine(self._top_right, self._end),
            AnimatedDottedLine(self._end, self._bottom_left),
            AnimatedDottedLine(self._bottom_left, self._origin),
        ]
    
    def recalculateBorders(self):
        self._top_right = QPointF( self._end.x(), self._origin.y() )
        self._bottom_left = QPointF( self._origin.x(), self._end.y() )
    
    def translate(self, delta):
        self._origin = self._origin + delta
        self._end = self._end + delta
        self.recalculateBorders()
        self.render()
    
    def getNearestHotspot(self, pos):
        spots = [
            # end takes priority to check, to not at a extra check that ask "is this a new rect"
            self._end,
            self._origin,
            self._top_right,
            self._bottom_left,
        ]
        for index, spot in enumerate(spots):
            magnitude = getVectorMagnitude( pos - spot) 
            if magnitude < 50:
                return index
        return -1

    def clearFromScene(self):
        if self.item_reference:
            self.scene.removeItem(self.item_reference)
        for line in self.animated_lines:
            self.scene.removeItem(line)
        self.animated_lines = []
    
    def render(self):
        self.clearFromScene()
        global PEN_LINE_SIZE
        self.createLines()

        self.drawable_rect = QRectF()
        self.drawable_rect.setX(self._origin.x())
        self.drawable_rect.setY(self._origin.y())
        self.drawable_rect.setBottomRight(self._end)

        pen = QPen(self.use_color, PEN_LINE_SIZE, Qt.PenStyle.SolidLine)
        if self._is_mouse_hovering:
            brush = QBrush(QColor(252, 232, 3, 30))
            self.item_reference = self.scene.addRect(self.drawable_rect, pen, brush)
        else:
            self.item_reference = self.scene.addRect(self.drawable_rect, pen)

        for line in self.animated_lines:
            self.scene.addItem(line)
    
    def hasPointInside(self, point):
        horizontal = point.x() > self._origin.x() and point.x() < self._end.x()
        vertical = point.y() > self._origin.y() and point.y() < self._end.y()
        return  horizontal and vertical


class ImageDrawingArea(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setMouseTracking(True)  # Enable mouse tracking
        
        # Selection attributes
        self.selecting = False
        self.active_rect = None
        self.current_hover_rect = None
        self.current_pixmap = None
        self.selected_hotspot_at_click = HOTSPOT_NONE
        self.selection_original_pos = None
        self.selection_item = None
        self.min_zoom = 0.8
        self.ctrl_pressed =  False
        
        self.is_active = False
        
        # Set up the view
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.cursor_in_image_point = None

        self.pressed_keys = set()

        self.list_of_draw_rects = []

        self.is_showing_orden_arrows = False
        self.list_of_arrows = []
        self.highlight_current_rect_arrow = None

        self.parent = None

    def clearArrows(self):
        for arrow in self.list_of_arrows:
            arrow.clearFromScene()
        
        self.list_of_arrows = []

    def updateOrderRects(self, new_order):
        new_list = []
        for uuid in new_order:
            new_list.append( *(rect for rect in self.list_of_draw_rects if rect.id == uuid) )
        self.list_of_draw_rects = new_list
        self.updateArrorws()

    def showHithlightArrow(self, uuid):
        self.removeHighlightArrow()
        list =  [rect for rect in self.list_of_draw_rects if rect.id == uuid]
        if len(list) == 0:
            return
        rect = list[0]
        (x,y,w,h) = rect.getDefinition()
        center = rect.getCenter()
        self.current_hover_rect = rect
        rect.is_mouse_hovering = True

        end =  QPointF( center.x(), center.y()+(h/2)+5 )
        start = QPointF( center.x(), center.y()+(h/2)+20 )
        self.highlight_current_rect_arrow = Arrow(start, end)
        self.highlight_current_rect_arrow.scene = self.scene()
        self.highlight_current_rect_arrow.render()


    def removeHighlightArrow(self):
        if self.highlight_current_rect_arrow:
            self.highlight_current_rect_arrow.clearFromScene()
            self.highlight_current_rect_arrow = None
            if self.current_hover_rect:
                self.current_hover_rect.is_mouse_hovering = False
            self.current_hover_rect = None


    def updateArrorws(self):
        self.clearArrows()
        if not self.is_showing_orden_arrows:
            return
        number_rects = len(self.list_of_draw_rects)
        if number_rects < 2:
            return

        start_index = 0
        final_index = 1
        while final_index < number_rects:
            start_point = self.list_of_draw_rects[start_index].getCenter()
            end_point = self.list_of_draw_rects[final_index].getCenter()
            start_index = final_index
            final_index+=1
            arrow = Arrow(start_point, end_point)
            arrow.scene = self.scene()
            arrow.render()
            self.list_of_arrows.append(arrow)        

    def addTextSelections(self, list_text):
        for rect_data in list_text:
            initial = rect_data["initial_pos"]
            end = rect_data["end_pos"]
            id = rect_data["id"]
            detected = rect_data["raw_text"]
            machine_translation = rect_data["machine_translation"]
            gui_rect = ImageRect(initial, end, id, detected, machine_translation)
            gui_rect.scene = self.scene()
            gui_rect.render()
            rect_definition = gui_rect.getDefinition()
            gui_rect.image = self.current_pixmap.copy(*rect_definition)
            self.list_of_draw_rects.append(gui_rect)
        self.informRectsUpdated()

    def getTextSelections(self):
        list_selections = []
        for rect in self.list_of_draw_rects:
            list_selections.append( {
                'initial_pos': rect.start,
                'end_pos':rect.end,
                'id':rect.id,
                'raw_text':rect.detected_characters,
                'machine_translation':rect.machine_translation
            } )
        return list_selections
    
    def clearActiveRect(self):
        if self.active_rect:
            self.active_rect.clearFromScene()
            self.active_rect = None
    
    def updateRectUnderMouse(self, pos):
        self.current_hover_rect = None
        for rect in self.list_of_draw_rects:
            # is better to run it over all the rects
            # to only trigger the redraw call at the change of state.
            rect.is_mouse_hovering = rect.hasPointInside(pos) 
            if rect.is_mouse_hovering:
                self.current_hover_rect = rect
    
    def clear(self):
        self.list_of_draw_rects = []
        self.clearActiveRect()
        self.is_active = False

    def setPixmap(self, pixmap):
        self.current_pixmap = pixmap
        self.is_active = True
        image_size = pixmap.size()
        view_size = self.size()

        # Calculate the scaling factors for width and height
        width_scale = view_size.width() / image_size.width()
        height_scale = view_size.height() / image_size.height()

        # Use the smaller scaling factor to fit the entire image
        min_size_area = 0.8 # 0.8 = 80% of the area of the view
        self.min_zoom = min(width_scale, height_scale) * min_size_area

        # Set the initial zoom to fit the image
        self.resetTransform()
        self.scale(self.min_zoom, self.min_zoom)
        
    def mousePressEvent(self, event):
        if not self.is_active:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.selecting = True
            initial_pos = self.mapToScene(event.position().toPoint())
            self.active_rect = self.current_hover_rect
            self.selected_hotspot_at_click = HOTSPOT_NONE
            if not self.active_rect:
                self.active_rect = ImageRect(initial_pos)
                self.active_rect.scene = self.scene()
                self.active_rect.start = initial_pos
                self.selected_hotspot_at_click = HOTSPOT_END
            else:
                self.selected_hotspot_at_click = self.active_rect.getNearestHotspot(initial_pos)
                if self.selected_hotspot_at_click == HOTSPOT_NONE:
                    self.selection_original_pos = initial_pos 
            
    def mouseMoveEvent(self, event):
        current_pos = self.mapToScene(event.position().toPoint())
        super().mouseMoveEvent(event)
        self.updateRectUnderMouse(current_pos)

        # check the contex of the action/cursor based on the position
        self.setCursor(Qt.CursorShape.ArrowCursor)
        hotspot_on_hover_rect = self.selected_hotspot_at_click
        if not self.selecting and self.current_hover_rect != None:
            # then we are not creating a new rect, and we are 
            # just moving the mouse around the scene
            hotspot_on_hover_rect =  self.current_hover_rect.getNearestHotspot(current_pos)
            if hotspot_on_hover_rect == HOTSPOT_NONE:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
        
        if hotspot_on_hover_rect == HOTSPOT_START or hotspot_on_hover_rect == HOTSPOT_END:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        if hotspot_on_hover_rect == HOTSPOT_BOTTOM_LEFT or hotspot_on_hover_rect == HOTSPOT_TOP_RIGHT:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)

        if self.active_rect:
            if hotspot_on_hover_rect == HOTSPOT_NONE:
                self.active_rect.translate( current_pos - self.selection_original_pos)
                self.selection_original_pos = current_pos
                self.updateArrorws()
            if hotspot_on_hover_rect == HOTSPOT_END:
                self.active_rect.end = current_pos
            if hotspot_on_hover_rect == HOTSPOT_START:
                self.active_rect.start = current_pos
            if hotspot_on_hover_rect == HOTSPOT_BOTTOM_LEFT:
                self.active_rect.bottom = current_pos
            if hotspot_on_hover_rect == HOTSPOT_TOP_RIGHT:
                self.active_rect.top = current_pos

            
    def mouseReleaseEvent(self, event):
        if not self.is_active:
            return
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if event.button() == Qt.MouseButton.LeftButton:
            self.selecting = False
            self.selected_hotspot_at_click = HOTSPOT_NONE
            if self.active_rect:
                if self.current_pixmap:
                    print('creating mini image...')
                    rect_definition = self.active_rect.getDefinition()
                    self.active_rect.image = self.current_pixmap.copy(*rect_definition)
                    print(self.active_rect.image)
                self.active_rect.dimentions_change = False
                self.informRectsUpdated() # to update the displayed label. :)
                self.updateArrorws()
            if not self.active_rect in self.list_of_draw_rects:
                magnitude = getVectorMagnitude(self.active_rect._end - self.active_rect._origin)
                if magnitude >= 32: 
                    self.list_of_draw_rects.append(self.active_rect)
                    self.informRectsUpdated()
                    self.updateArrorws()
                else: ## is way to small, delete it from screen.
                    self.clearActiveRect()
            self.active_rect = None
    
    def keyPressEvent(self, event):
        # Check if Ctrl key is pressed
        self.pressed_keys.add(event.key())  # Add pressed key to the set
        if event.key() == Qt.Key.Key_Control:
            self.ctrl_pressed = True
            self.cursor_in_image_point = None
    
    def keyReleaseEvent(self, event):
        # Check if Ctrl key is released
        if Qt.Key.Key_Control in self.pressed_keys:
            if Qt.Key.Key_X in self.pressed_keys:
                if self.current_hover_rect:
                    self.current_hover_rect.clearFromScene()
                    self.list_of_draw_rects.remove(self.current_hover_rect)
                    self.informRectsUpdated()
                    self.updateArrorws()
                    self.current_hover_rect = None
            self.ctrl_pressed = False
        
        self.pressed_keys.discard(event.key())

    def wheelEvent(self, event):
        super().wheelEvent(event)

        if not self.ctrl_pressed:
            return

        # Get the mouse position in view coordinates
        cursor_in_view_pos = event.position()
        # save the first point were the zoom starts to keep 
        # it in focus for reference when zooming.
        if not self.cursor_in_image_point:
            self.cursor_in_image_point = self.mapToScene(cursor_in_view_pos.toPoint())

        # Zoom factor
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.8
        # Set the zoom factor, so the image will not
        # go smaller than the area of the graphics view
        horizontal_scale = self.transform().m11()
        new_scale = horizontal_scale * zoom_factor
        if new_scale < self.min_zoom:
            zoom_factor = self.min_zoom / horizontal_scale

        self.scale(zoom_factor, zoom_factor)

        # after applied the scale, check the new position of the 
        # cursor on the image, and translate it by the diff with
        # the old position on the image.
        has_scroll_h = self.horizontalScrollBar().isVisible()
        has_scroll_v = self.verticalScrollBar().isVisible()

        if has_scroll_h or has_scroll_v:
            new_cursor_in_image_pos = self.mapToScene(cursor_in_view_pos.toPoint())
            # Adjust the view to keep the mouse position fixed
            delta = new_cursor_in_image_pos - self.cursor_in_image_point
            self.translate(delta.x(), delta.y())

    def informRectsUpdated(self):
        if self.parent:
            self.parent.updateInfoAreas(self.list_of_draw_rects, self.active_rect)
        
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.scene() and not self.scene().items():
            return