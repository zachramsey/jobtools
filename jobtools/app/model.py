# app/model.py
import json
import os
from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from .utils import get_config_dir


class TreeItem:
    """ A node in the configuration tree. """
    def __init__(self, data: list, parent: 'TreeItem'|None = None):
        self._item_data = data  # [Key, Value]
        self._parent = parent
        self._child_items: list[TreeItem] = []

    def append_child(self, item):
        self._child_items.append(item)

    def child(self, row):
        if 0 <= row < len(self._child_items):
            return self._child_items[row]
        return None

    def child_count(self):
        return len(self._child_items)

    def column_count(self):
        return len(self._item_data)

    def data(self, column):
        if 0 <= column < len(self._item_data):
            return self._item_data[column]
        return None
    
    def set_data(self, column, value):
        if 0 <= column < len(self._item_data):
            self._item_data[column] = value
            return True
        return False

    def parent_item(self):
        return self._parent

    def row(self):
        if self._parent:
            return self._parent._child_items.index(self)
        return 0


class ConfigModel(QAbstractItemModel):
    """ The central configuration model. """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_item = TreeItem(["Property", "Value"])
        # Structure: Category -> Setting Name -> Value
        
        # Collector Config Page
        collect = TreeItem(["collect", ""], self._root_item)
        collect.append_child(TreeItem(["proxy", ""], collect))
        collect.append_child(TreeItem(["data_source", ""], collect))
        collect.append_child(TreeItem(["sites", []], collect))
        collect.append_child(TreeItem(["queries", []], collect))
        self._root_item.append_child(collect)

        # Filter Config Page
        filt = TreeItem(["filter", ""], self._root_item)
        filt.append_child(TreeItem(["work_models", []], filt))
        filt.append_child(TreeItem(["job_types", []], filt))
        filt.append_child(TreeItem(["title_exclude", {"selected": [], "available": []}], filt))
        filt.append_child(TreeItem(["title_require", {"selected": [], "available": []}], filt))
        filt.append_child(TreeItem(["descr_exclude", {"selected": [], "available": []}], filt))
        filt.append_child(TreeItem(["descr_require", {"selected": [], "available": []}], filt))
        self._root_item.append_child(filt)

        # Sorting Config Page
        sort = TreeItem(["sort", ""], self._root_item)
        sort.append_child(TreeItem(["degree_values", (0,0,0)], sort))
        sort.append_child(TreeItem(["location_order", []], sort))
        sort.append_child(TreeItem(["term_emphasis", {}], sort))
        self._root_item.append_child(sort)

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if parent.isValid():
            child_item = parent.internalPointer().child(row)
        else:
            child_item = self._root_item.child(row)

        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent_item()

        if parent_item == self._root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        if parent.isValid():
            return parent.internalPointer().child_count()
        return self._root_item.child_count()

    def columnCount(self, parent=QModelIndex()):
        return self._root_item.column_count()

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        item = index.internalPointer()
        
        # EditRole returns the raw Python object (list, dict, etc.)
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return item.data(index.column())
        
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (Qt.ItemFlag.ItemIsEnabled | 
                Qt.ItemFlag.ItemIsSelectable | 
                Qt.ItemFlag.ItemIsEditable)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole:
            item = index.internalPointer()
            if item.set_data(index.column(), value):
                self.dataChanged.emit(index, index, [
                    Qt.ItemDataRole.EditRole, Qt.ItemDataRole.DisplayRole])
                return True
        return False
        
    def headerData(self, section, orientation, role):
        if (orientation == Qt.Orientation.Horizontal and 
            role == Qt.ItemDataRole.DisplayRole):
            return self._root_item.data(section)
        return None

    def save_to_file(self, filename: str):
        """ Dump the current configuration to a JSON file. """
        data = self._recursive_dump(self._root_item)
        filepath = os.path.join(get_config_dir(), f"{filename}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    def load_from_file(self, filename: str):
        """ Load configuration from a JSON file. """
        try:
            filepath = os.path.join(get_config_dir(), f"{filename}.json")
            with open(filepath, 'r') as f:
                data = json.load(f)
            self.beginResetModel()
            self._recursive_load(data, self._root_item)
            self.endResetModel()
        except FileNotFoundError:
            print("Config file not found, keeping defaults.")

    def _recursive_dump(self, item):
        if item.child_count() == 0:
            # Leaf item -> return its value 
            return item.data(1)
        # Item has children -> go deeper
        result = {}
        for i in range(item.child_count()):
            child = item.child(i)
            key = child.data(0)
            result[key] = self._recursive_dump(child)
        return result

    def _recursive_load(self, data_dict, parent_item):
        if not isinstance(data_dict, dict):
            # Not a dict -> backtrack
            return
        # Iterate over children of parent_item
        for i in range(parent_item.child_count()):
            child = parent_item.child(i)
            key = child.data(0)
            if key in data_dict:
                val = data_dict[key]
                if child.child_count() > 0:
                     # Item has children -> go deeper
                    self._recursive_load(val, child)
                else:
                    # Leaf item -> set value
                    child.set_data(1, val)