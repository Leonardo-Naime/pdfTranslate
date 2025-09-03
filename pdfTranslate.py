import sys
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QScrollArea, QFileDialog,
    QToolTip, QToolBar, QStatusBar
)
from PySide6.QtGui import QPixmap, QImage, QAction, QIcon
from PySide6.QtCore import Qt, QRectF, QPoint

class PDFViewer(QMainWindow):
    """
    Um leitor de PDF simples com funcionalidade de tradução ao passar o mouse.
    Traduz de inglês para português.
    """
    def __init__(self):
        super().__init__()

        # --- Configurações da Janela Principal ---
        self.setWindowTitle("Leitor de PDF com Tradutor")
        self.setGeometry(100, 100, 1024, 768)

        # --- Variáveis de Estado ---
        self.pdf_document = None
        self.current_page_index = 0
        self.zoom_factor = 2.0
        self.word_map = []
        self.last_hovered_word = None

        # --- Componentes da Interface ---
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMouseTracking(True)
        self.image_label.mouseMoveEvent = self.on_mouse_move

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(self.scroll_area)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Nenhum arquivo aberto.")
        self.status_bar.addWidget(self.status_label)

        # --- Tradutor ---
        self.translator = GoogleTranslator(source='en', target='pt')

        # --- Barra de Ferramentas e Ações ---
        self._create_actions()
        self._create_toolbar()

    def _create_actions(self):
        """Cria as ações para a barra de ferramentas e menus."""
        self.open_action = QAction(QIcon.fromTheme("document-open"), "&Abrir...", self)
        self.open_action.triggered.connect(self.open_pdf_file)
        self.open_action.setShortcut("Ctrl+O")

        self.prev_page_action = QAction(QIcon.fromTheme("go-previous"), "Página &Anterior", self)
        self.prev_page_action.triggered.connect(self.show_previous_page)
        self.prev_page_action.setShortcut("Left")
        self.prev_page_action.setEnabled(False)

        self.next_page_action = QAction(QIcon.fromTheme("go-next"), "&Próxima Página", self)
        self.next_page_action.triggered.connect(self.show_next_page)
        self.next_page_action.setShortcut("Right")
        self.next_page_action.setEnabled(False)

        self.zoom_in_action = QAction(QIcon.fromTheme("zoom-in"), "A&umentar Zoom", self)
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.setEnabled(False)

        self.zoom_out_action = QAction(QIcon.fromTheme("zoom-out"), "&Diminuir Zoom", self)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.setEnabled(False)

    def _create_toolbar(self):
        """Cria a barra de ferramentas superior."""
        toolbar = QToolBar("Barra de Ferramentas Principal")
        self.addToolBar(toolbar)
        toolbar.addAction(self.open_action)
        toolbar.addSeparator()
        toolbar.addAction(self.prev_page_action)
        toolbar.addAction(self.next_page_action)
        toolbar.addSeparator()
        toolbar.addAction(self.zoom_out_action)
        toolbar.addAction(self.zoom_in_action)

    def open_pdf_file(self):
        """Abre um seletor de arquivos para carregar um PDF."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Abrir arquivo PDF", "", "Arquivos PDF (*.pdf)"
        )
        if filepath:
            try:
                self.pdf_document = fitz.open(filepath)
                self.current_page_index = 0
                self.display_page(self.current_page_index)
                self.setWindowTitle(f"Leitor Tradutor - {filepath.split('/')[-1]}")
                self.update_navigation_buttons()
                self.zoom_in_action.setEnabled(True)
                self.zoom_out_action.setEnabled(True)
            except Exception as e:
                self.status_label.setText(f"Erro ao abrir o arquivo: {e}")

    def display_page(self, page_number):
        """Renderiza e exibe uma página específica do PDF."""
        if not self.pdf_document or not (0 <= page_number < self.pdf_document.page_count):
            return

        self.current_page_index = page_number
        self.status_label.setText(f"Página {page_number + 1} de {self.pdf_document.page_count}")

        page = self.pdf_document.load_page(page_number)
        mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=mat)
        
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.image_label.setPixmap(pixmap)
        self.image_label.adjustSize()

        self.word_map.clear()
        words = page.get_text("words")
        for word_info in words:
            x0, y0, x1, y1, text = word_info[:5]
            rect = QRectF(x0 * self.zoom_factor, y0 * self.zoom_factor,
                          (x1 - x0) * self.zoom_factor, (y1 - y0) * self.zoom_factor)
            self.word_map.append((rect, text))
        
        self.update_navigation_buttons()

    def on_mouse_move(self, event):
        """Chamado sempre que o mouse se move sobre a imagem do PDF."""
        mouse_pos = event.position()
        found_word = False
        
        tooltip_pos = event.globalPosition().toPoint()

        for rect, word_text in self.word_map:
            if rect.contains(mouse_pos):
                cleaned_word = ''.join(filter(str.isalpha, word_text)).lower()
                
                if cleaned_word and self.last_hovered_word != cleaned_word:
                    self.last_hovered_word = cleaned_word
                    try:
                        translation = self.translator.translate(cleaned_word)
                        QToolTip.showText(tooltip_pos + QPoint(15, 15), 
                                          f"<b>{word_text}</b><br>{translation}", self.image_label)
                    except Exception:
                        QToolTip.showText(tooltip_pos + QPoint(15, 15),
                                          f"<b>{word_text}</b><br><i>Tradução não encontrada.</i>", self.image_label)
                found_word = True
                break

        if not found_word:
            self.last_hovered_word = None
            QToolTip.hideText()

    def update_navigation_buttons(self):
        """Atualiza o estado (habilitado/desabilitado) dos botões de navegação."""
        if not self.pdf_document: return
        self.prev_page_action.setEnabled(self.current_page_index > 0)
        self.next_page_action.setEnabled(self.current_page_index < self.pdf_document.page_count - 1)
        
    def show_previous_page(self):
        if self.current_page_index > 0:
            self.display_page(self.current_page_index - 1)

    def show_next_page(self):
        if self.pdf_document and self.current_page_index < self.pdf_document.page_count - 1:
            self.display_page(self.current_page_index + 1)
            
    def zoom_in(self):
        self.zoom_factor *= 1.2
        self.display_page(self.current_page_index)

    def zoom_out(self):
        if self.zoom_factor > 0.5:
            self.zoom_factor /= 1.2
            self.display_page(self.current_page_index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = PDFViewer()
    viewer.show()
    sys.exit(app.exec())