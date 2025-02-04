from PyQt6.QtWidgets import (QApplication, QMainWindow, 
    QGraphicsScene, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
    QFileDialog, QLabel, QSplitter, QScrollArea, QTabWidget, QSizePolicy)
from PyQt6.QtGui import QPixmap, QIcon, QAction, QImage
from PyQt6.QtCore import Qt, QRectF, QSize, QPointF
from ImageDrawingArea import ImageDrawingArea
from InfoAreas import ListOfImagesArea, CollapsibleSection, AreaDetails
from PIL import Image
import sys
import os
from uuid import UUID, uuid4 as uuid
import json
import subprocess

# this is to load dinamicaly manga-ocr
import importlib
from concurrent.futures import ThreadPoolExecutor

# google translator webscraping
import asyncio
from googletrans import Translator

translator = Translator()


def set_mime_type_linux(file_name):
    try:
        subprocess.run(["xdg-mime", "install", "--mode", "user", file_name])
        subprocess.run(["xdg-mime", "default", "application/json", file_name])
        print(f"MIME type set for {file_name}")
    except Exception as e:
        print(f"Failed to set MIME type: {e}")


class InfoProyect():
    def __init__(self):
        self.pages = []
    
    def pushPage(self, pixmap, path):
        print(f'push {pixmap} ({path})')
        self.pages.append(
            { "qtimg": pixmap,
              "path": path,
              "gui_info": {
                  "showing_order": False,
                  "showing_overlay_text": False
              },
              "text": []
            }
        )
        return len(self.pages) - 1
    
    def toString(self):
        clean_data = { 'pages':[] }
        for page in self.pages:
            clean_page_data = {
                'path': page['path'],
                'gui_info': page['gui_info'],
                'text': []
            }
            for text in page["text"]:
                start = text['initial_pos']
                end = text['end_pos']
                clean_text = {
                    'id': f'{text['id']}',
                    'start' : { 'x':int(start.x()), 'y':int(start.y()) },
                    'end' : { 'x':int(end.x()), 'y':int(end.y()) },
                    'raw_text': text['raw_text'],
                    'machine_translation': text['machine_translation']
                }
                clean_page_data['text'].append(clean_text)
            clean_data['pages'].append(clean_page_data)
        data = json.dumps(clean_data, indent=2, ensure_ascii=False)
        print(data)
        return data
    
    def setPageGuiInfo(self, page_index, setting, value):
        #print( f'set gui info of page {page_index} at "{setting}" to {value}' )
        self.pages[page_index]["gui_info"][setting] = value
    
    def getPageGuiInfo(self, page_index, setting):
        value = self.pages[page_index]["gui_info"][setting]
        #print( f'get gui info of page {page_index} at "{setting}" ({value})' )
        return value
    
    def getPixmap(self, page_index):
        return self.pages[page_index]["qtimg"]
    
    def getPath(self, page_index):
        return self.pages[page_index]["path"]
    
    def getListTexts(self, page_index):
        return self.pages[page_index]["text"]
    
    def saveTextSelections(self, page_index, list_texts):
        self.pages[page_index]["text"] = list_texts
    
    def clear(self):
        self.pages = []

LIST_QT_PIXMAPS = InfoProyect()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gomata")
        self.setGeometry(100, 100, 900, 700)

        self.executor = ThreadPoolExecutor()
        self.manga_ocr_instance = None

        self._is_showing_order = False
        self._is_showing_overlay_text = False
        self.current_file_name = None

        self.status_label = None

        self.defineActions()
        self.createMenuBar()
        self.createWindowContent()
        self.startMangaOCR()
    
    def defineActions(self):
        self.open_file_action = QAction("Open File", self)
        self.save_proyect_action = QAction("Save File", self)
        self.load_folder_action = QAction("Add folder images", self)
        self.add_image_action = QAction("Add Image", self)

        self.open_file_action.setShortcut("Ctrl+O")
        self.load_folder_action.setShortcut("Ctrl+F")
        self.save_proyect_action.setShortcut("Ctrl+S")
        self.add_image_action.setShortcut("Ctrl+I")


        self.load_folder_action.triggered.connect(self.launchOpenFolderDialog)
        self.add_image_action.triggered.connect(self.launchOpenImagenDialog)
        self.open_file_action.triggered.connect(self.openGomataFile)
        self.save_proyect_action.triggered.connect(self.saveGomataFile)

    @property
    def is_showing_order(self):
        return self._is_showing_order
    
    @is_showing_order.setter
    def is_showing_order(self, value):
        if self._is_showing_order == value:
                return
        self._is_showing_order = value

        if self.selected_page_index != None:
            LIST_QT_PIXMAPS.setPageGuiInfo(
                self.selected_page_index,
                "showing_order", value)
        
        if self.view:
            self.view.is_showing_orden_arrows = value
            self.view.updateArrorws()
        
        if self.btn_display_order == None:
            return
        if self._is_showing_order:
            self.btn_display_order.setText('Hide Read Order')
        else:
            self.btn_display_order.setText('Show Read Order')

    @property
    def is_showing_overlay_text(self):
        return self._is_showing_overlay_text
    
    @is_showing_overlay_text.setter
    def is_showing_overlay_text(self, value):
        if self._is_showing_overlay_text == value:
                return
        self._is_showing_overlay_text = value

        if self.selected_page_index != None:
            LIST_QT_PIXMAPS.setPageGuiInfo(
                self.selected_page_index,
                "showing_overlay_text", value)
        
        if self.view:
            self.view.setIsShowingText(value)
        
        if self.btn_display_overlay == None:
            return
        if self._is_showing_overlay_text:
            self.btn_display_overlay.setText('Hide Overlay Text')
        else:
            self.btn_display_overlay.setText('Show Overlay Text')


    def createMenuBar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction(self.open_file_action)
        file_menu.addAction(self.save_proyect_action)
        file_menu.addAction(self.load_folder_action)
        file_menu.addAction(self.add_image_action)

    def createWindowContent(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Buttons layout
        buton_strip = QWidget()
        button_layout = QHBoxLayout(buton_strip)
        
        
        # Load button
        self.btn_display_order = QPushButton("Show Read Order")
        self.btn_display_order.setIcon(QIcon("./icons/switch-horizontal.svg")) 
        self.btn_display_order.clicked.connect(lambda:( setattr(self, 'is_showing_order', not self.is_showing_order) ))
        button_layout.addWidget(self.btn_display_order)


        self.btn_display_overlay = QPushButton("Show Overlay Text")
        self.btn_display_overlay.setIcon(QIcon("./icons/bubble-text.svg")) 
        self.btn_display_overlay.clicked.connect(lambda:( setattr(self, 'is_showing_overlay_text', not self.is_showing_overlay_text) ))
        button_layout.addWidget(self.btn_display_overlay)

        #self.load_btn.clicked.connect(self.launchOpenImagenDialog)
        
        # Save button
        """
        self.save_btn = QPushButton("Auto Fill")
        #self.save_btn.clicked.connect(self.save_selection)
        self.save_btn.setIcon(QIcon("./icons/settings-automation.svg"))
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)
        
        # Status label
        self.status_label = QLabel("No image loaded")
        button_layout.addWidget(self.status_label)
        """
        
        #layout.addLayout(button_layout)
        
        self.selected_page_index = None
        self.image_path = None
        self.pixmap_current_item = None

        # Create a QSplitter to divide the window into resizable sections
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)  # Vertical splitter

        # Add three collapsible sections to the splitter
        self.section1 = ListOfImagesArea()
        self.section2 = CollapsibleSection()
        self.area_details = AreaDetails()

        splitter.addWidget(self.section1)
        splitter.addWidget(self.section2)
        splitter.addWidget(self.area_details)


         # Graphics View setup
        self.scene = QGraphicsScene()
        self.view = ImageDrawingArea(self.scene)
        self.view.parent = self
        self.area_details.parent = self

        self.section2.addWidget(buton_strip)
        self.section2.addWidget(self.view)

        # Add the splitter to the main layout
        layout.addWidget(splitter)

        self.status_label = QLabel("Hello")
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,  # Horizontal policy
            QSizePolicy.Policy.Fixed       # Vertical policy (fixed height)
        )
        self.status_label.setFixedHeight(20)  # Set a fixed height for the status bar
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # Align text
        # Add the status bar to the layout
        layout.addWidget(self.status_label)
    
    def updateStatusBar(self, msg):
        self.status_label.setText(msg)

    def startMangaOCR(self):
        self.updateStatusBar("Awaiting character recognition module to load")

        # Run the initialization in a background thread
        future = self.executor.submit(self.loadMangaOCRModule)
        future.add_done_callback(self.onMangaOCRLoaded)

    def loadMangaOCRModule(self):
        # Initialize manga-ocr (this is the heavy part)
        self.updateStatusBar("Initializing manga-ocr in the background...")
        manga_ocr_module = importlib.import_module("manga_ocr")
        return manga_ocr_module.MangaOcr()

    def onMangaOCRLoaded(self, future):
        try:
            # Get the initialized manga-ocr instance
            self.manga_ocr_instance = future.result()
            self.updateStatusBar("manga-ocr initialized and ready!")

            # Now you can use self.manga_ocr_instance for OCR tasks
            """
            if self.manga_ocr_instance:
                try:
                    # Example OCR usage
                    text = self.manga_ocr_instance("path_to_manga_image.png")
                    self.updateStatusBar(f"OCR Result: {text}")
                except Exception as e:
                    self.updateStatusBar(f"OCR failed: {e}")
            """
        except Exception as e:
            self.updateStatusBar(f"Failed to initialize manga-ocr: {e}")

    def qpixmapToPIL(self, pixmap):
        # Convert QPixmap to QImage
        qimage = pixmap.toImage()

        # Convert QImage to Pillow Image
        if qimage.format() == QImage.Format.Format_ARGB32:
            # Convert ARGB32 to RGBA
            qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)

        # Access the raw image data
        ptr = qimage.bits()
        ptr.setsize(qimage.height() * qimage.bytesPerLine())

        # Create a Pillow Image from the raw data
        return Image.frombuffer(
            "RGBA",  # Mode (RGBA for 32-bit images)
            (qimage.width(), qimage.height()),  # Size
            ptr,  # Raw data
            "raw",  # Decoder
            "RGBA",  # Raw mode
            qimage.bytesPerLine(),  # Stride (bytes per line)
            1  # Orientation
        )

    async def googleTranslate(self, list, rect, text, dest="es"):
        async with Translator() as translator:
            result = await translator.translate(text, dest=dest)
            rect.machine_translation = result.text

            print(f'try to transalte "{text}"\n --> {result.text}')
            self.updateInfoAreas(list, rect)
    
    def applyOCR(self, list, rect):
        pixmap = rect.image
        if not self.manga_ocr_instance:
            self.updateStatusBar("ERROR: OCR module is not ready!!!")
            return

        if pixmap.isNull():
            self.updateStatusBar("ERROR: Try to parsed invalid pixmap")
            return

        # Convert QPixmap to Pillow Image
        pil_image = self.qpixmapToPIL(pixmap)

        if pil_image:
            # Run OCR on the image
            detection_result = ''
            try:
                text = self.manga_ocr_instance(pil_image)
                detection_result = f"OCR Result: {text}"
                rect.detected_characters = text
                asyncio.run(
                    self.googleTranslate(list, rect, text, dest="es")
                )
            except Exception as e:
                detection_result = f"OCR failed: {e}"
                rect.detected_characters = '[OCR FAILED]'
            self.updateStatusBar(detection_result)
            self.updateInfoAreas(list, rect)
        else:
            self.label.setText("Failed to convert image.")


    def updateInfoAreas(self, list_of_draw_rects, active_rect = None):
        print(f'now list of rects has {len(list_of_draw_rects)} rects!')
        self.area_details.clearListRects()
        self.area_details.addRectsToList(list_of_draw_rects)
        # update the details only when a new rect is added or click on a existing one
        if active_rect and active_rect in list_of_draw_rects:
            self.area_details.clearRectDetails()
            self.area_details.updateTabPageTranslation(active_rect)

            # this is the part were we do the ocr stuff
            if not active_rect.detected_characters:
                self.applyOCR(list_of_draw_rects, active_rect)
            elif (not active_rect.machine_translation and
                active_rect.detected_characters != '[OCR FAILED]'):
                asyncio.run(
                    self.googleTranslate(list_of_draw_rects ,active_rect, active_rect.detected_characters, dest="es")
                )

    def launchOpenFolderDialog(self):
        # Open a folder dialog
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.loadImage(folder)
    
    def addImage(self, image_path):
        global LIST_QT_PIXMAPS

        print(f'loading picture: {image_path}')
        pixmap = QPixmap(image_path)
        pixmap_index = LIST_QT_PIXMAPS.pushPage(pixmap, image_path)

        # Create a button with the thumbnail as an icon
        thumbnail = QIcon(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio))  # Scale to thumbnail

        print(f'thumbnail is {type(thumbnail)}, index: {pixmap_index}')

        button = QPushButton()
        button.setIcon(thumbnail)
        button.setIconSize(QSize(100, 100))
        button.clicked.connect(lambda : self.putOnDrawingAreaImage(pixmap_index))  # Connect click event
        self.section1.addImageTumbnail(button)
        return pixmap_index

    def putOnDrawingAreaImage(self, index):
        global LIST_QT_PIXMAPS
        path = LIST_QT_PIXMAPS.getPath(index)
        pixmap = LIST_QT_PIXMAPS.getPixmap(index)
        text_selections = LIST_QT_PIXMAPS.getListTexts(index)


        if self.selected_page_index != None:
            LIST_QT_PIXMAPS.saveTextSelections(
                self.selected_page_index,
                self.view.getTextSelections())
        
        self.selected_page_index = index
        self.is_showing_order = LIST_QT_PIXMAPS.getPageGuiInfo(index, "showing_order")
        self.is_showing_overlay_text = LIST_QT_PIXMAPS.getPageGuiInfo(index, "showing_overlay_text")

        # Clear previous image if any
        self.view.clear() # view uses the scene, so it goes first
        self.updateInfoAreas([]) # clear the list on the rect
        self.scene.clear()
        
        # Add new image to scene
        self.pixmap_current_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(QRectF(pixmap.rect()))
        
        # Enable save button
        self.save_btn.setEnabled(True)
        self.status_label.setText(f"Image loaded: {path.split('/')[-1]}")
        
        # Fit view to image
        self.view.setPixmap(pixmap)
        self.view.addTextSelections(text_selections)
        self.view.updateArrorws()


    def loadImage(self, folder):
        global LIST_QT_PIXMAPS
        self.section1.clearImageList()
        LIST_QT_PIXMAPS.clear()

        # Load images from the folder
        for filename in os.listdir(folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.addImage(os.path.join(folder, filename))


    def launchOpenImagenDialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Image File",
            "",
            "Images (*.png *.xpm *.jpg *.bmp)"
        )
        
        if file_name:
            self.image_path = file_name
            pixmap_index = self.addImage(self.image_path)
            self.putOnDrawingAreaImage(pixmap_index)
    
    def openGomataFile(self):
        global LIST_QT_PIXMAPS
        filename, _ = QFileDialog.getOpenFileName(
                self,
                "Open Gomata File",
                "",
                "Gomata File (*.gmt);;All Files (*.*)"
            )
        if not filename:
            return

        content = None
        with open(filename, 'r', encoding="utf-8") as content_file:
            content = content_file.read()

        if not content:
            return

        self.current_file_name = filename
        self.section1.clearImageList()
        LIST_QT_PIXMAPS.clear()
        
        parsed = json.loads(content)
        pages = parsed['pages']
        for index, page in enumerate(pages):
            self.addImage(page['path'])
            print(index, page)
            gui_info = page['gui_info']
            LIST_QT_PIXMAPS.setPageGuiInfo(
                index,
                "showing_order", gui_info.get('showing_order') )
            LIST_QT_PIXMAPS.setPageGuiInfo(
                index,
                "showing_overlay_text", gui_info.get('showing_overlay_text') )
             
            
            text_on_page = []
            for text_info in page['text']:
                start = text_info['start']
                end = text_info['end']
                text_on_page.append({
                'initial_pos': QPointF( start['x'], start['y'] ),
                'end_pos':QPointF( end['x'], end['y'] ),
                'id': UUID(text_info['id']),
                'raw_text': text_info.get('raw_text'),
                'machine_translation': text_info.get('machine_translation')
                })

            LIST_QT_PIXMAPS.saveTextSelections( index, text_on_page)
        
        if len(LIST_QT_PIXMAPS.pages) > 0:
            self.putOnDrawingAreaImage(0)


    def saveGomataFile(self):
        global LIST_QT_PIXMAPS
        if self.current_file_name == None:
            # Save dialog
            self.current_file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save Selection",
                "",
                "Gomata File (*.gmt);;All Files (*.*)"
            )

        if not self.current_file_name:
            print('can not get filename...')
            return
        
        if not self.current_file_name.endswith(".gmt"):
            self.current_file_name += ".gmt"
        print(f'saving to {self.current_file_name}')
        
        # recal data from current active page...
        if self.selected_page_index != None:
            LIST_QT_PIXMAPS.saveTextSelections(
                self.selected_page_index,
                self.view.getTextSelections())

        f = open(self.current_file_name, "w",  encoding="utf-8")
        f.write(LIST_QT_PIXMAPS.toString())
        f.close()
        set_mime_type_linux(self.current_file_name)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())