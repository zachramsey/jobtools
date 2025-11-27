from PySide6.QtWidgets import (
    QApplication, QSizePolicy, QWidget,
    QVBoxLayout, QHBoxLayout, 
    QPlainTextEdit, QPushButton
)
from PySide6.QtCore import Qt, QEvent, Slot


class QAdaptivePlainTextEdit(QPlainTextEdit):
    """ QPlainTextEdit that adapts its height to content. """

    def __init__(self, max_lines : int = 5):
        """ Initialize the adaptive plain text editor.
        
        Parameters
        ----------
        max_lines : int
            Maximum number of lines before scroll bar appears.
        """
        super().__init__()
        self._font_height = self.fontMetrics().lineSpacing()
        self._vert_margins = self.contentsMargins().top() + self.contentsMargins().bottom() + 8
        self._min_height = self._font_height + self._vert_margins
        self._max_height = (self._font_height * max_lines) + self._vert_margins
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().documentLayout().documentSizeChanged.connect(self._update_height)

    @Slot()
    def _update_height(self, size):
        """ Update height based on content size, up to max lines. """
        doc_height = self.document().size().height() * self._font_height
        height = max(self._min_height, doc_height + self._vert_margins)
        if height > self._max_height:
            height = self._max_height
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(int(height))
    

class QPlainTextListEdit(QWidget):
    def __init__(self, placeholder_text: str = "Add new item..."):
        """ Initialize the plain text list editor.

        Parameters
        ----------
        placeholder_text : str
            Placeholder text for inactive editors.
        """
        super().__init__()
        self._placeholder_text = placeholder_text
        self.setLayout(QVBoxLayout(self))
        # Track editor rows
        self.rows: list[dict] = []
        # start with a single inactive editor
        self._add_editor_row()

    def _add_editor_row(self):
        """ Add a new editor row to the layout. """
        # Create row container
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        # Create text editor
        editor = QAdaptivePlainTextEdit()
        editor.setPlainText(self._placeholder_text)
        editor.setReadOnly(True)
        editor.installEventFilter(self)
        editor.setStyleSheet("color: #888;")
        row_layout.addWidget(editor)
        # Create button container
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(btn_container, alignment=Qt.AlignmentFlag.AlignTop)
        # Create delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        delete_btn.setVisible(False)
        btn_layout.addWidget(delete_btn)
        # Add row to main layout
        self.layout().addWidget(row_widget)
        row = {"container": row_widget,
               "editor": editor,
               "btn_container": btn_container,
               "btn_layout": btn_layout,
               "delete_btn": delete_btn}
        self.rows.append(row)
        # Connect delete button
        delete_btn.clicked.connect(lambda _, r=row: self._on_delete(r))

    def eventFilter(self, watched, event):
        """ Event filter to handle FocusIn events on editors. """
        # Activate editor on focus in
        if isinstance(watched, QPlainTextEdit) and event.type() == QEvent.Type.FocusIn:
            # Find corresponding row
            row = None
            for r in self.rows:
                if r["editor"] is watched:
                    row = r
                    break
            # Activate editor if it is inactive
            if row is not None and row["editor"].isReadOnly():
                # Activate editor
                row["editor"].setReadOnly(False)
                if row["editor"].toPlainText() == self._placeholder_text:
                    row["editor"].setPlainText("")
                row["editor"].setStyleSheet("color: #222;")
                row["delete_btn"].setVisible(True)
                # Add delete button to activated editor
                self._restore_delete_button(row)
                # Ensure there is always a trailing inactive editor
                if self.rows and self.rows[-1]["editor"] is watched:
                    self._add_editor_row()
        return super().eventFilter(watched, event)

    @Slot()
    def _on_delete(self, row):
        """ Handle delete button click for a row. """
        if row not in self.rows:
            return
        # Replace delete button with confirm/cancel buttons
        self._clear_layout(row["btn_layout"])
        confirm_btn = QPushButton("Confirm")
        confirm_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        confirm_btn.clicked.connect(lambda _, r=row: self._on_confirm_delete(r))
        row["btn_layout"].addWidget(confirm_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancel_btn.clicked.connect(lambda _, r=row: self._on_cancel_delete(r))
        row["btn_layout"].addWidget(cancel_btn)

    @Slot()
    def _on_confirm_delete(self, row):
        """ Handle confirm delete button click for a row. """
        if row not in self.rows:
            return
        # Clear focus if editor is focused
        try:
            app = QApplication.instance()
            if app is not None and app.focusWidget() is row["editor"]:
                try:
                    self.setFocus()
                except Exception:
                    pass
                row["editor"].clearFocus()
        except Exception:
            pass
        # Remove row from layout and schedule deletion
        try:
            self.layout().removeWidget(row["container"])
        except Exception:
            pass
        row["container"].hide()
        row["container"].setParent(None)
        row["container"].deleteLater()
        # Remove row from list
        try:
            self.rows.remove(row)
        except ValueError:
            pass
        # Ensure at least one inactive editor remains
        if not self.rows:
            self._add_editor_row()
        else:
            last_editor = self.rows[-1]["editor"]
            if not last_editor.isReadOnly():
                self._add_editor_row()

    @Slot()
    def _on_cancel_delete(self, row):
        """ Handle cancel delete button click for a row. """
        if row not in self.rows:
            return
        self._restore_delete_button(row)

    def _restore_delete_button(self, row):
        """ Restore the delete button in the row's button layout. """
        self._clear_layout(row["btn_layout"])
        row["btn_layout"].addWidget(row["delete_btn"])
        row["delete_btn"].setVisible(not row["editor"].isReadOnly())

    @staticmethod
    def _clear_layout(layout):
        """ Clear all widgets from a layout. """
        # remove all widgets from a layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def get_items(self) -> list[str]:
        """ Access current list of non-empty items. """
        items = []
        for row in self.rows:
            text = row["editor"].toPlainText().strip()
            if text and text != self._placeholder_text:
                items.append(text)
        return items