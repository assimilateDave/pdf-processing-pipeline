import sys
from PyQt5 import QtWidgets, QtCore
from database import init_db
import sqlite3

class DocumentTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super(DocumentTable, self).__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["ID", "File Name", "Type", "Processed At"])
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

    def load_data(self):
        self.setRowCount(0)
        conn = sqlite3.connect("documents.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_name, document_type, processed_at FROM documents ORDER BY processed_at DESC")
        for row_data in cursor.fetchall():
            row = self.rowCount()
            self.insertRow(row)
            for col, data in enumerate(row_data):
                item = QtWidgets.QTableWidgetItem(str(data))
                self.setItem(row, col, item)
        conn.close()

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Document Processing Progress")
        self.resize(700, 400)
        layout = QtWidgets.QVBoxLayout()
        self.table = DocumentTable(self)
        layout.addWidget(self.table)
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self.table.load_data)
        layout.addWidget(refresh_button)
        self.setLayout(layout)
        self.table.load_data()

if __name__ == '__main__':
    init_db()  # Initialize the database on startup
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())