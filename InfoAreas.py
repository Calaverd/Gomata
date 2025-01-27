from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QTabWidget, QListWidget, QListWidgetItem,
    QSizePolicy, QPushButton, QTextEdit)
from PyQt6.QtGui import  QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QObject
from PyQt6 import sip


class CollapsibleSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Create a layout for the section
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def addWidget(self, widget):
        self.layout.addWidget(widget)  

class ListOfImagesArea(CollapsibleSection):
    def __init__(self):
        super().__init__()
        self.addWidget(QLabel("List of images"))

        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # Allow the widget to resize within the scroll area

         # Create a widget to hold the content
        self.list_area = QWidget()
        self.widget_list_images = QVBoxLayout(self.list_area)
        self.widget_list_images.setAlignment(Qt.AlignmentFlag.AlignTop) 

        # Add a large amount of content to the widget
        #for i in range(50):
        #    self.widget_list_images.addWidget(QLabel(f"Label {i + 1}"))

        # Set the content widget to the scroll area
        scroll_area.setWidget(self.list_area)

        self.addWidget(scroll_area)

    def clearImageList(self):
        # Clear existing thumbnails
        for i in reversed(range(self.widget_list_images.count())):
            self.widget_list_images.itemAt(i).widget().setParent(None)
    
    def addImageTumbnail(self, image):
        self.widget_list_images.addWidget(image)


class ReorderableListWidget(QListWidget):
    # Custom signal to emit when the list is reordered
    orderChanged = pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding 
        )

    def dropEvent(self, event):
        # Call the base class implementation to handle the drop
        super().dropEvent(event)

        new_order = [self.item(index).data(0) for index in range(self.count())]
        # Emit the custom signal
        self.orderChanged.emit(new_order)

class ListRectItem(QWidget):
    def __init__(self, rect):
        super().__init__()
        self.show_full_details = False

        self.detail_raw_charactes_found = rect.detected_characters if rect.detected_characters else '...' 
        self.detail_proposed_transaltion = rect.machine_translation if rect.machine_translation else '???'

        self.base_layout = QVBoxLayout()
        self.setLayout(self.base_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.toggle_button = QPushButton("Show more")
        self.toggle_button.clicked.connect(self.showThisRectDetails)

        self.parent = None
        self.rect_item = rect

        self.rect_main_info = None
        self.render()
    
    def showThisRectDetails(self):
        if self.parent:
            self.parent.goToDetails(self.rect_item)
        
    
    def clear(self):
        if self.rect_main_info:
            self.base_layout.removeWidget(self.toggle_button)
            self.base_layout.removeWidget(self.rect_main_info)
            sip.delete(self.rect_main_info)
            self.rect_main_info = None

    def render(self):
        self.clear()
        self.rect_main_info = QWidget()
        simple_layout = QVBoxLayout()
        self.rect_main_info.setLayout(simple_layout)

        text_i_detected = QLabel()
        text_i_detected.setText(f'Charactes: <span style="font-style: bold;">{self.detail_raw_charactes_found}</span>')
        simple_layout.addWidget(text_i_detected)

        text_tranlation = QLabel()
        text_tranlation.setText(f'Translation: <span style="font-style: bold;">{self.detail_proposed_transaltion}</span>')
        simple_layout.addWidget(text_tranlation)

        self.base_layout.addWidget(self.rect_main_info)
        self.base_layout.addWidget(self.toggle_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

class HoverHandler(QObject):
    # Custom signal to emit when the mouse enters or leaves
    hovered = pyqtSignal(bool)

    def eventFilter(self, obj, event):
        # Handle hover events
        if event.type() == QEvent.Type.Enter:
            self.hovered.emit(True)
        elif event.type() == QEvent.Type.Leave:
            self.hovered.emit(False)
        return super().eventFilter(obj, event)


def addToLayoutField( layout, name, content, read_only=False):
    text_title = QLabel()
    text_title.setText(name)

    text_content = QTextEdit()
    #text_content.setMaximumHeight(50)
    if not read_only:
        text_content.setStyleSheet("background-color: lightgray; color: black; ")
        text_content.setText(content)
    else:
        text_content.setText(f'<span style="font-style: italic; color: blue; ">{content}</span>')
        text_content.setStyleSheet("background-color: gray;  border: 1px dashed #a0a0a0; padding: 5px;")
        text_content.setReadOnly(True)
    text_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    text_content.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    layout.addWidget(text_title)
    layout.addWidget(text_content)

    return text_content


class AreaDetails(CollapsibleSection):
    def __init__(self):
        super().__init__()
        self.tab_rect_details = None
        self.createTabRectDetails()
        self.updateTabPageTranslation()

        self.tab_bar = QTabWidget()
        self.tab_bar.addTab(self.tab_list_of_rects, 'List Rects')
        self.tab_bar.addTab(self.tab_rect_details, 'Rect Details')

        self.tab_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding 
        )

        self.parent = None
        self.active_rect_details = None
        self.addWidget(self.tab_bar)

    def goToDetails(self, rect_item):
        print(f'go to details! {rect_item}')
        self.tab_bar.setCurrentIndex(1)
        self.clearRectDetails()
        self.updateTabPageTranslation(rect_item)
        self.parent.view.showHithlightArrow(rect_item.id)
        


    def clearListRects(self):
        self.widget_list_details.clear()

    def clearRectDetails(self):
        widget = self.tab_rect_details.widget()
        if widget:
            # Get the layout of the widget
            layout = widget.layout()
            while layout.count():
                child = layout.takeAt(0)
                child_widget = child.widget()
                if child_widget:
                    layout.removeWidget(child_widget)
                    sip.delete(child_widget)
            widget.update()

    def addRectsToList(self, list_of_rects):
        for rect in list_of_rects:
            widget = QWidget()
            main_container = QHBoxLayout()
            main_container.setAlignment(Qt.AlignmentFlag.AlignLeft)
            main_container.setContentsMargins(0, 0, 0, 0)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            widget.setLayout(main_container)

            # Add a QLabel with the QPixmap to the custom widget
            pixmap_label = QLabel()
            if rect.image:
                scaled_pixmap = rect.image.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)
                pixmap_label.setPixmap(scaled_pixmap)  # Resize pixmap
            else:
                pixmap_label.setText("[]")
            
            main_container.addWidget(pixmap_label)
            main_container.setAlignment(Qt.AlignmentFlag.AlignLeft)
            
            rect_item = ListRectItem(rect)
            rect_item.parent = self
            main_container.addWidget(rect_item)
            
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setData(0, rect.id)
            # Set the resized image on the label
            
            self.widget_list_details.addItem(item)
            self.widget_list_details.setItemWidget(item, widget)
    
    def onRectListOrderChange(self, new_order):
        print('order changed!', new_order )
        self.parent.view.updateOrderRects(new_order)
    
    def createTabRectDetails(self):
        # Create a scroll area
        self.tab_list_of_rects = QScrollArea()
        #self.tab_rect_details.setSizePolicy(QSizePolicy.Policy.Expanding)
        self.tab_list_of_rects.setWidgetResizable(True)  # Allow the widget to resize within the scroll area

        self.tab_list_of_rects.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding 
        )

         # Create a widget to hold the content
        details = QWidget()
        self.widget_list_details = ReorderableListWidget(details)

        self.widget_list_details.setDragEnabled(True)  # Allow dragging items
        self.widget_list_details.setAcceptDrops(True)  # Allow dropping items
        self.widget_list_details.setDropIndicatorShown(True)  # Show drop indicator
        self.widget_list_details.setDragDropMode(QListWidget.DragDropMode.InternalMove) 

        self.widget_list_details.orderChanged.connect(self.onRectListOrderChange)
        # Set the content widget to the scroll area
        
        self.tab_list_of_rects.setWidget(self.widget_list_details)
    
    def on_hover(self, hovered):
        # Slot to handle the hover signal
        if hovered and self.active_rect_details:
            print(f'higtligth rect data... {self.active_rect_details.id}')
            self.parent.view.showHithlightArrow(self.active_rect_details.id)
        else:
            self.parent.view.removeHighlightArrow()
            print('stop higtlingthing')

    def updateTabPageTranslation(self, rect=None):
        # Create a scroll area
        if not self.tab_rect_details:
            self.tab_rect_details = QScrollArea()
            self.tab_rect_details.setWidgetResizable(True)  # Allow the widget to resize within the scroll area
            self.hover_handler = HoverHandler()
            self.tab_rect_details.installEventFilter(self.hover_handler)

            # Connect the hover signal to the highlight slot
            self.hover_handler.hovered.connect(self.on_hover)

        self.active_rect_details = rect
        # Create a widget to hold the content
        overview = QWidget()
        layout = QVBoxLayout(overview)
        print(f'new layout {layout}')
        if self.tab_rect_details.widget():
            overview = self.tab_rect_details.widget()
            layout = overview.layout()
        else:
            self.tab_rect_details.setWidget(overview)

        if rect == None:
            text_tranlation = QLabel()
            text_tranlation.setText(f'<span style="font-style: bold;">No rect active</span>')
            layout.addWidget(text_tranlation)
            return

        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(8)

        pixmap_label = QLabel()
        if rect.image:
            scaled_pixmap = rect.image.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio)
            pixmap_label.setPixmap(scaled_pixmap)  # Resize pixmap
        else:
            pixmap_label.setText("[]")
        pixmap_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        found_text = rect.detected_characters if rect.detected_characters else '[searching...]' 
        machine_text =  rect.machine_translation if rect.machine_translation else '[no data]'

        layout.addWidget(pixmap_label)

        addToLayoutField(layout, 'Detected text', found_text, read_only=True)
        addToLayoutField(layout, 'Machine translation', machine_text, read_only=True)
        """
        addToLayoutField(layout, 'Contextual meaming', '', read_only=True)
        addToLayoutField(layout, 'Cultural notes', '', read_only=True)
        addToLayoutField(layout, 'Proposed translation', '', read_only=True)

        addToLayoutField(layout, 'Context', '')
        addToLayoutField(layout, 'Type Text', '')
        addToLayoutField(layout, 'Aproved translation', '')
        """

        layout.addStretch()