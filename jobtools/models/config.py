# app/model.py
import json
from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from ..utils import get_config_dir
from .jobsdata import JobsDataModel


class TreeItem:
    """ A node in the configuration tree. """
    def __init__(self, data: list, parent=None):
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
    
    def find_child(self, key: str):
        for child in self._child_items:
            if child.data(0) == key:
                return child
        return None


class ConfigModel(QAbstractItemModel):
    """ The central configuration model. """

    jobs: JobsDataModel
    """ The JobsData instance managed by this model. """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_item = TreeItem(["Property", "Value"])

        # Path to persistent config file
        self._cfg_path = str(get_config_dir() / "persistent.json")

        # Auto-save on data change
        self.dataChanged.connect(lambda: self.save_to_file(self._cfg_path))

    def load_last_config(self):
        """ Load the last saved configuration from the persistent file. """
        self.load_from_file(self._cfg_path)

    def register_page(self, page_name: str, defaults: dict) -> QModelIndex:
        """ Register a new page in the configuration model.

        Parameters
        ----------
        page_name : str
            Name identifier for the page.
        defaults : dict
            Default configuration values for the page.

        Returns
        -------
        QModelIndex
            The index of the root item for the registered page.
        """
        root = self._root_item
        page_item = root.find_child(page_name)

        if not page_item:
            self.beginInsertRows(QModelIndex(), root.child_count(), root.child_count())
            page_item = TreeItem([page_name, None], root)
            root.append_child(page_item)
            self._build_tree(defaults, page_item)
            self.endInsertRows()
        else:
            self._merge_defaults(defaults, page_item)

        return self.index(page_item.row(), 0, QModelIndex())
    
    def _build_tree(self, data: dict, parent_item: TreeItem):
        for key, value in data.items():
            if isinstance(value, dict):
                child_item = TreeItem([key, None], parent_item)
                parent_item.append_child(child_item)
                self._build_tree(value, child_item)
            else:
                child_item = TreeItem([key, value], parent_item)
                parent_item.append_child(child_item)

    def _merge_defaults(self, defaults: dict, parent_item: TreeItem):
        for key, value in defaults.items():
            child_item = parent_item.find_child(key)
            if not child_item:
                if isinstance(value, dict):
                    new_item = TreeItem([key, None], parent_item)
                    parent_item.append_child(new_item)
                    self._build_tree(value, new_item)
                else:
                    new_item = TreeItem([key, value], parent_item)
                    parent_item.append_child(new_item)
            else:
                if isinstance(value, dict):
                    self._merge_defaults(value, child_item)

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

    def save_to_file(self, filepath: str):
        """ Save the current configuration to a JSON file. """
        if not filepath.endswith(".json"):
            raise ValueError(f"Filepath must point to a JSON file. Got: {filepath}")
        data = self._recursive_dump(self._root_item)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    def load_from_file(self, filepath: str):
        """ Load configuration from a JSON file. """
        if not filepath.endswith(".json"):
            raise ValueError(f"Filepath must point to a JSON file. Got: {filepath}")
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            self._recursive_load(data, self._root_item)
            self.dataChanged.emit(QModelIndex(), QModelIndex())
        except FileNotFoundError:
            pass

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
        for key, value in data_dict.items():
            child_item = parent_item.find_child(key)
            if not child_item:
                # Key not found in model -> Create new item
                if isinstance(value, dict):
                    new_item = TreeItem([key, None], parent_item)
                    parent_item.append_child(new_item)
                    self._recursive_load(value, new_item)
                else:
                    new_item = TreeItem([key, value], parent_item)
                    parent_item.append_child(new_item)
            else:
                if isinstance(value, dict):
                    self._recursive_load(value, child_item)
                else:
                    child_item.set_data(1, value)

    def get_saved_config_names(self) -> list[str]:
        """ Get a list of saved configuration names in the config directory. """
        config_dir = get_config_dir()
        config_names = []
        for config_file in config_dir.iterdir():
            if config_file.suffix == ".json" and config_file.name != "persistent.json":
                config_names.append(config_file.stem.strip().replace("_", " ").title())
        return config_names
    
    def get_config_dict(self) -> dict:
        """ Get the entire configuration as a dictionary. """
        return self._recursive_dump(self._root_item)
