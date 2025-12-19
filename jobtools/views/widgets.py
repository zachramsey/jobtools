__all__ = [
    "QHeader",
    "QAdaptivePlainTextEdit",
    "QPlainTextListEdit",
    "QFlowLayout",
    "QChipSelect",
    "QCheckBoxSelect",
]

from enum import Enum
from PySide6.QtCore import Qt, QEvent, Slot, QPoint, QRect, QSize, Signal, QUrl
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import (
    QWidget, QWidgetItem, QSizePolicy, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QPushButton, QLayout, QFrame, QLineEdit,
    QStackedLayout, QMenu, QCheckBox, QLabel
)
from ..utils import get_icon
from ..utils.logger import JDLogger


class QHeader(QWidget):
    """ Header widget with title and optional help tooltip. """

    def __init__(self, title: str, header_level: int = 2, tooltip: str = ""):
        """ Initialize the header widget.

        Parameters
        ----------
        title : str
            The header title text.
        header_level : int, optional
            The header level (e.g., 1 for h1, 2 for h2).
        tooltip : str, optional
            Optional tooltip text for help icon.
        """
        super().__init__()
        self.setLayout(QHBoxLayout(self))
        self.layout().addWidget(QLabel(f"<h{header_level}>{title}</h{header_level}>"))  # type: ignore
        if tooltip:
            help = QPushButton()
            help.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
            help.setIcon(get_icon("help", color="primaryLightColor"))
            help.setIconSize(QSize(16, 16))
            help.setCursor(Qt.CursorShape.PointingHandCursor)
            help.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            help.setProperty("class", "help-button")
            help.setToolTip(tooltip)
            self.layout().addWidget(help)   # type: ignore
        self.layout().addStretch()          # type: ignore


class QWebImageLabel(QLabel):
    """ QLabel that loads and displays an image from a web URL. """

    def __init__(self, url: str):
        """ Initialize the web image label.

        Parameters
        ----------
        url : str
            URL of the image to load.
        """
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Loading...")
        
        self._manager = QNetworkAccessManager(self)
        self._manager.finished.connect(self._on_finished)
        self._manager.get(QNetworkRequest(QUrl(url)))
        
    @Slot(QNetworkReply)
    def _on_finished(self, reply: QNetworkReply):
        """ Handle the finished network reply. """
        if reply.error() != QNetworkReply.NetworkError.NoError:
            JDLogger().warning(f"Failed to load image from URL: {reply.errorString()}")
            self.setText("Failed to load image.")
            return
        image = QImage()
        image.loadFromData(reply.readAll())
        pixmap = QPixmap.fromImage(image)
        self.setPixmap(pixmap)


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
        self._vert_margins = self.contentsMargins().top() + self.contentsMargins().bottom() + 17
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
    """ Widget for editing a list of plain text items. """

    itemsChanged = Signal(list)
    """ Signal emitted when the list of items changes. """

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
        self.rows: list[dict] = []
        """ List of editor row dictionaries. Each dictionary contains:
            - container: QWidget
            - editor: QPlainTextEdit
            - btn_container: QWidget
            - btn_layout: QHBoxLayout
            - delete_btn: QPushButton
        """
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
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        """ Event filter to handle FocusIn events on editors.

        Only activate editors when focus change is due to an actual user interaction
        (mouse, tab, backtab, or keyboard shortcut), not programmatic focus changes.
        """
        # Handle Activation
        if isinstance(watched, QPlainTextEdit) and event.type() == QEvent.Type.FocusIn:
            # Get the corresponding row
            row = next((r for r in self.rows if r["editor"] is watched), None)
            if row is not None and row["editor"].isReadOnly():
                # Inactive row exists -> Activate it
                row["editor"].setReadOnly(False)
                if row["editor"].toPlainText() == self._placeholder_text:
                    # Clear placeholder text
                    row["editor"].setPlainText("")
                # Show delete button
                row["delete_btn"].setVisible(True)
                self._restore_delete_button(row)
                if self.rows and self.rows[-1]["editor"] is watched:
                    # Last row activated -> Add new inactive row
                    self._add_editor_row()
        # Handle Content Change
        if isinstance(watched, QPlainTextEdit) and event.type() == QEvent.Type.KeyRelease:
            self.itemsChanged.emit(self.get_items())
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
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.clicked.connect(lambda _, r=row: self._on_confirm_delete(r))
        row["btn_layout"].addWidget(confirm_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(lambda _, r=row: self._on_cancel_delete(r))
        row["btn_layout"].addWidget(cancel_btn)

    @Slot()
    def _on_confirm_delete(self, row):
        """ Handle confirm delete button click for a row. """
        if row not in self.rows:
            return
        try:
            # Clear focus from editor if needed
            row["editor"].clearFocus()
            # Remove row from layout and schedule deletion
            self.layout().removeWidget(row["container"])
        except Exception:
            pass
        row["container"].hide()
        row["container"].setParent(None)
        row["container"].deleteLater()
        try:
            # Remove row from list
            self.rows.remove(row)
        except ValueError:
            pass
        if not self.rows:
            # No rows left -> add a new inactive row
            self._add_editor_row()
        else:
            # Ensure trailing inactive editor
            last_editor = self.rows[-1]["editor"]
            if not last_editor.isReadOnly():
                self._add_editor_row()
        # Emit items changed signal
        self.itemsChanged.emit(self.get_items())

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
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                
    def get_items(self) -> list[str]:
        """ Get the list of items from all non-empty editors. """
        items = []
        for row in self.rows:
            text = row["editor"].toPlainText().strip()
            if text and text != self._placeholder_text:
                items.append(text)
        return items
    
    def set_items(self, items: list[str]):
        """ Set the list of items, replacing existing editors.

        Parameters
        ----------
        items : list[str]
            List of strings to set as editor contents.
        """
        # Clear existing rows
        for row in self.rows:
            try:
                self.layout().removeWidget(row["container"])    # type: ignore
            except Exception:
                pass
            row["container"].hide()
            row["container"].setParent(None)
            row["container"].deleteLater()
        self.rows.clear()
        # Add new rows
        for text in items:
            self._add_editor_row()
            row = self.rows[-1]
            row["editor"].setPlainText(text)
            row["editor"].setReadOnly(False)
            row["delete_btn"].setVisible(True)
            self._restore_delete_button(row)
        if not self.rows or not self.rows[-1]["editor"].isReadOnly():
            # Ensure trailing inactive editor
            self._add_editor_row()
    

class QFlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, h_spacing=10, v_spacing=10):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._item_list = []

    def insertWidget(self, index: int, widget):
        """Insert a widget into the layout at the given index."""
        item = QWidgetItem(widget)
        self._item_list.insert(index, item)
        self.addChildWidget(widget)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins().top()
        size += QSize(2 * margin, 2 * margin)
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self._h_spacing

        for item in self._item_list:
            wid = item.widget()
            space_x = spacing + wid.style().layoutSpacing(
                QSizePolicy.ControlType.PushButton,
                QSizePolicy.ControlType.PushButton,
                Qt.Orientation.Horizontal)
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + self._v_spacing
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class ChipMode(Enum):
    STANDARD = 0 
    CREATOR = 1


class QChip(QWidget):
    """ A selectable and optionally modifiable chip widget. """

    clicked = Signal()
    """ Signal emitted when the chip is clicked. """
    delete_requested = Signal(QWidget)
    """ Signal emitted when the user requests deletion of the chip. """
    new_text_entered = Signal(str)
    """ Signal emitted when the user enters new text in creator mode. """

    def __init__(self,
                 text: str|None = None,
                 mode: ChipMode = ChipMode.STANDARD,
                 is_selected: bool = False,
                 is_custom: bool = False):
        """ Initialize the custom chip.

        Parameters
        ----------
        text : str
            Initial text for the chip.
        is_selected : bool
            Whether the chip is in selected state.
        is_custom : bool
            Whether the chip can be edited/deleted by the user.
        """
        super().__init__()
        self.mode = mode
        self.is_selected = is_selected
        self._is_custom = is_custom

        # Stacked Layout: idx=0->Button, idx=1->LineEdit
        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)

        # Button view
        self.btn = QPushButton()
        if text is not None:
            self.btn.setText(text)
        else:
            self.btn.setIcon(get_icon("add"))
            self.btn.setIconSize(QSize(16, 16))
        self.btn.setProperty("class", "chip")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Keep the button width tight to its contents:
        self.btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        # Keep visual selection state consistent with provided value
        if self.mode == ChipMode.STANDARD:
            self.btn.setCheckable(True)
            self.btn.clicked.connect(self.clicked.emit)
            self.btn.setChecked(self.is_selected)
            self.set_is_custom(is_custom)
        else:
            self.btn.clicked.connect(self.start_editing)
        self.stack.addWidget(self.btn)

        # Editor view
        self.editor = QLineEdit()
        self.editor.setPlaceholderText("Enter chip text...")
        self.editor.returnPressed.connect(self.commit_edit)
        self.editor.installEventFilter(self)    # Handle Esc / FocusOut
        self.stack.addWidget(self.editor)

    @property
    def text(self) -> str:
        """ Text of the chip. """
        return self.btn.text()
    
    @text.setter
    def text(self, text: str):
        self.btn.setText(text)

    @property
    def is_custom(self) -> bool:
        """ Whether the chip is user-editable/deletable. """
        return self._is_custom

    def set_is_custom(self, value: bool):
        self._is_custom = value
        if self.is_custom:
            self.btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.btn.customContextMenuRequested.connect(self.show_context_menu)
            self.btn.setToolTip("Right-click to Edit/Delete")
        else:
            self.btn.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            self.btn.setToolTip("")

    def show_context_menu(self, pos: QPoint):
        if not self.is_custom:
            return

        menu = QMenu(self)
        edit = menu.addAction("Edit")
        menu.addSeparator()
        delete = menu.addAction("Delete")

        action = menu.exec(self.btn.mapToGlobal(pos))
        if action == edit:
            self.start_editing()
        elif action == delete:
            self.delete_requested.emit(self)

    def start_editing(self):
        if self.mode == ChipMode.STANDARD:
            self.editor.setText(self.btn.text())
        else:
            self.editor.clear()
        self.stack.setCurrentIndex(1)
        self.editor.setFocus()

    def commit_edit(self):
        text = self.editor.text().strip()
        if self.mode == ChipMode.CREATOR:
            if text:
                self.new_text_entered.emit(text)
            self.editor.clear()
        else:
            if text:
                self.btn.setText(text)
        self.stack.setCurrentIndex(0)

    def cancel_edit(self):
        self.editor.clear()
        self.stack.setCurrentIndex(0)

    def eventFilter(self, obj, event):
        if obj == self.editor:
            if event.type() == QEvent.Type.FocusOut:
                if self.mode == ChipMode.CREATOR:
                    self.cancel_edit()
                else:
                    self.commit_edit()
                return True
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                self.cancel_edit()
                return True
        return super().eventFilter(obj, event)        

    def sizeHint(self) -> QSize:
        """Return a size hint based on the current visible widget (button/editor).
        This ensures the chip width follows the content width."""
        current_widget = self.stack.currentWidget()
        if current_widget is None:
            current_widget = self.btn
        sh = current_widget.sizeHint()
        margins = self.contentsMargins()
        return QSize(sh.width() + margins.left() + margins.right(),
                     sh.height() + margins.top() + margins.bottom())


class QChipSelect(QWidget):
    """ Widget for selecting options using chips. """

    selectionChanged = Signal(list)
    availableChanged = Signal(list)
    """ Signal emitted when the selection changes. """

    def __init__(self,
                 base_items: list[str]=[],
                 enable_creator: bool = True):
        """ Initialize the chip selection widget.

        Parameters
        ----------
        base_items : list[str], optional
            List of initially available options.
        enable_creator : bool, optional
            Whether to allow user-defined items.
        """
        super().__init__()
        self.base_items = base_items
        self.creator_chip: QChip|None = None
        self.setLayout(QVBoxLayout(self))
        # Container for selected chips
        self.selected_container = QWidget()
        self.selected_layout = QFlowLayout(self.selected_container)
        self.layout().addWidget(self.selected_container)        # type: ignore
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout().addWidget(line)                           # type: ignore
        # Container for available chips
        self.available_container = QWidget()
        self.available_layout = QFlowLayout(self.available_container)
        self.layout().addWidget(self.available_container)       # type: ignore
        # Initialization
        if base_items:
            for text in base_items:
                self.add_standard_chip(text, self.available_layout)
        if enable_creator:
            self.add_creator_chip()

    def add_standard_chip(self, text: str,
                          target_layout: QFlowLayout,
                          selected: bool = False,
                          is_custom: bool = False):
        # Add a standard chip to the specified layout.
        chip = QChip(text,
                     mode=ChipMode.STANDARD,
                     is_selected=selected,
                     is_custom=is_custom)
        chip.clicked.connect(lambda: self._on_move_chip(chip))
        chip.delete_requested.connect(self._on_delete_chip)
        target_layout.addWidget(chip)
        # Keep the button's checked state consistent with `selected`
        if chip.mode == ChipMode.STANDARD:
            chip.btn.setChecked(selected)

    def add_creator_chip(self):
        if self.creator_chip is None:
            self.creator_chip = QChip(mode=ChipMode.CREATOR)
            self.creator_chip.new_text_entered.connect(self._on_create_chip)
        self.available_layout.addWidget(self.creator_chip)

    @Slot()
    def _on_create_chip(self, text: str):
        # Add new standard chip to selected layout
        self.add_standard_chip(text, self.selected_layout,
                               selected=True, is_custom=True)
        # Emit selection changed signal
        self.selectionChanged.emit(self.get_selected())
        
    @Slot()
    def _on_move_chip(self, chip: QChip):
        current_layout = chip.parentWidget().layout()   # type: ignore
        if current_layout == self.available_layout:
            # Is available -> move to selected
            self.available_layout.removeWidget(chip)
            chip.is_selected = True
            self.selected_layout.addWidget(chip)
        else:
            # Is selected -> move to available
            self.selected_layout.removeWidget(chip)
            chip.is_selected = False
            if self.creator_chip:
                # Ensure creator chip stays at end
                self.available_layout.removeWidget(self.creator_chip)
                self.available_layout.addWidget(chip)
                self.available_layout.addWidget(self.creator_chip)
            elif self.base_items and chip.text in self.base_items:
                # Insert in sorted order among base items
                insert_idx = 0
                chip_idx = self.base_items.index(chip.text)
                for item in self.__get_items(self.available_layout):
                    if item in self.base_items:
                        if self.base_items.index(item) < chip_idx:
                            insert_idx += 1
                self.available_layout.insertWidget(insert_idx, chip)
            else:
                self.available_layout.addWidget(chip)
                    
        # Emit signals
        self.selectionChanged.emit(self.__get_items(self.selected_layout))
        self.availableChanged.emit(self.__get_items(self.available_layout))

    @Slot()
    def _on_delete_chip(self, chip: QChip):
        is_selected = chip.is_selected
        layout = chip.parentWidget().layout()   # type: ignore
        layout.removeWidget(chip)               # type: ignore
        chip.deleteLater()
        if is_selected:
            # Deleted from selected -> Emit selected chips
            self.selectionChanged.emit(self.get_selected())
        else:
            # Deleted from available -> Emit available chips
            self.availableChanged.emit(self.get_available())

    def __get_items(self, layout: QFlowLayout) -> list[str]:
        items = []
        for i in range(layout.count()):
            chip: QChip = layout.itemAt(i).widget()
            if chip is not self.creator_chip:
                items.append(chip.btn.text())
        return items

    def get_selected(self) -> list[str]:
        """ List of selected items' text. """
        return self.__get_items(self.selected_layout)
    
    def get_available(self) -> list[str]:
        """ List of available items' text. """
        return self.__get_items(self.available_layout)
    
    def __set_items(self,
                    set_layout: QFlowLayout,
                    other_layout: QFlowLayout,
                    items: list[str]):
        for i, text in enumerate(items):
            if text in self.__get_items(other_layout):
                # Find and remove from other layout
                for j in range(other_layout.count()):
                    item = other_layout.itemAt(j)
                    if not item:
                        continue
                    chip: QChip = item.widget()
                    if chip and chip.btn.text() == text:
                        other_layout.removeWidget(chip)
                        chip.setParent(None)
                        chip.deleteLater()
                        break
            is_custom = text not in self.base_items
            if i < set_layout.count():
                # Bootstrap existing chip at this index
                chip = set_layout.itemAt(i).widget()
                chip.btn.setText(text)
                chip.set_is_custom(is_custom)
            else:
                # Otherwise, create a new chip and add it
                self.add_standard_chip(text, set_layout,
                                       selected=(set_layout == self.selected_layout),
                                       is_custom=is_custom)
        while set_layout.count() > len(items):
            # Remove excess chips
            item = set_layout.takeAt(len(items))
            if item.widget():
                item.widget().deleteLater()
    
    def set_selected(self, items: list[str]):
        """ Overwrite selected items with the given list,
        removing items from available as needed.

        Parameters
        ----------
        items : list[str]
            List of items to set as selected.
        """
        self.__set_items(self.selected_layout, self.available_layout, items)
    
    def set_available(self, items: list[str]):
        """ Overwrite available items with the given list,
        removing items from selected as needed.

        Parameters
        ----------
        items :  list[str]
            List of items to set as available.
        """
        if self.creator_chip:
            # Temporarily removes creator chip to avoid interference
            self.available_layout.removeWidget(self.creator_chip)
            self.__set_items(self.available_layout, self.selected_layout, items)
            self.available_layout.addWidget(self.creator_chip)
        else:
            self.__set_items(self.available_layout, self.selected_layout, items)


class QCheckBoxSelect(QWidget):
    """ A simple checkbox selection widget. """

    selectionChanged = Signal(list)
    """ Signal emitted when the selection changes. """

    def __init__(self, labels: list[str] = []):
        """ Initialize the checkbox selection widget.

        Parameters
        ----------
        labels : list[str], optional
            List of checkbox labels.
        """
        super().__init__()
        self.setLayout(QHBoxLayout(self))
        # Create checkbox for each label
        self.checkboxes: dict[str, QCheckBox] = {}
        for label in labels:
            cb = QCheckBox(label)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.clicked.connect(self._on_change)
            self.layout().addWidget(cb)     # type: ignore
            self.checkboxes[label] = cb
        # Set checkbox widths to the maximum content width
        max_width = 0
        for cb in self.checkboxes.values():
            max_width = max(max_width, cb.sizeHint().width())
        for cb in self.checkboxes.values():
            cb.setFixedWidth(max_width + 5)
        # Push content to the left
        self.layout().addStretch()          # type: ignore

    @Slot()
    def _on_change(self):
        """ Emit current selection when changed. """
        self.selectionChanged.emit(self.get_selected())

    def get_selected(self) -> list[str]:
        """ The list of selected checkbox labels. """
        return [label for label, cb in self.checkboxes.items() if cb.isChecked()]
    
    def set_selected(self, labels: list[str]):
        """ Set selected checkboxes by label.

        Parameters
        ----------
        labels : list[str]
            List of labels to set as selected.
        """
        for label, cb in self.checkboxes.items():
            cb.setChecked(label in labels)
