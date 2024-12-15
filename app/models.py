# app/models.py

from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex, QVariant
from PyQt6.QtGui import QBrush, QColor
import pandas as pd
import logging

class PandasModel(QAbstractTableModel):
    def __init__(self, df=pd.DataFrame(), table=None, parent=None):  # Add table=None here
        super().__init__(parent)
        self._df = df.copy()
        self._undo_stack = []
        self._redo_stack = []
        self.table = table  # Now you can assign it

    def rowCount(self, parent=QModelIndex()):
        return len(self._df.index)

    def columnCount(self, parent=QModelIndex()):
        return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            value = self._df.iloc[index.row(), index.column()]
            return str(value)
        elif role == Qt.ItemDataRole.BackgroundRole:
            column_name = self._df.columns[index.column()]
            # Primjer: Crvena boja za neispravne unose u 'EPISODE NUMBER'
            if column_name == 'EPISODE NUMBER' and not str(self._df.iloc[index.row(), index.column()]).isdigit():
                return QBrush(QColor(255, 0, 0, 100))  # Crvena transparentna boja
        return QVariant()

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._df.columns[section])
            else:
                return str(self._df.index[section])
        return QVariant()

    def flags(self, index):
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if index.isValid() and role == Qt.ItemDataRole.EditRole:
            column_name = self._df.columns[index.column()]
            
            # Primjer validacije za EPISODE NUMBER da bude broj
            if column_name == 'EPISODE NUMBER':
                if not str(value).isdigit():
                    logging.warning(f"Neispravan unos za EPISODE NUMBER: {value}")
                    return False
            
            # Dodajte druge validacije prema potrebama
            # Na primjer, validacija formata datuma ili vremena
            
            # Spremi trenutno stanje prije izmjene
            self._undo_stack.append(self._df.copy())
            self._redo_stack.clear()

            self._df.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
            return True
        return False

    def get_dataframe(self):
        return self._df.copy()

    def undo(self):
        if self._undo_stack:
            self._redo_stack.append(self._df.copy())
            self._df = self._undo_stack.pop()
            self.layoutChanged.emit()
            logging.info("Undo operacija izvršena.")
            return True
        logging.info("Nema izmjena za poništiti.")
        return False

    def redo(self):
        if self._redo_stack:
            self._undo_stack.append(self._df.copy())
            self._df = self._redo_stack.pop()
            self.layoutChanged.emit()
            logging.info("Redo operacija izvršena.")
            return True
        logging.info("Nema izmjena za ponovno primijeniti.")
        return False

    def insert_row(self, position):
        """Umetanje praznog reda na specificiranu poziciju."""
        self.beginInsertRows(QModelIndex(), position, position)
        self._undo_stack.append(self._df.copy())
        self._redo_stack.clear()
        # Force the QTableView to update:
        #self.table.viewport().update() 

        # Create a new empty row with the correct number of columns
        new_row = pd.DataFrame([[pd.NA] * len(self._df.columns)], columns=self._df.columns)

        # Insert the new row at the specified position
        self._df = pd.concat([self._df.iloc[:position], new_row, self._df.iloc[position:]]).reset_index(drop=True)

        self.endInsertRows()
        logging.info(f"Redak umetnut na poziciju {position}.")

        # Emit layoutChanged signal to force a complete update
        self.layoutChanged.emit()

        # Force the QTableView to update:
        self.table.viewport().update()

    def remove_row(self, position):
        """Uklanjanje reda na specificiranu poziciju."""
        if position < 0 or position >= self.rowCount():
            logging.warning(f"Pokušaj uklanjanja nepostojećeg reda na poziciji {position}.")
            return False
        self.beginRemoveRows(QModelIndex(), position, position)
        self._undo_stack.append(self._df.copy())
        self._redo_stack.clear()
        self._df = self._df.drop(self._df.index[position]).reset_index(drop=True)
        self.endRemoveRows()
        # Force the QTableView to update:
        self.table.viewport().update() 
        logging.info(f"Redak uklonjen na poziciji {position}.")
        return True
