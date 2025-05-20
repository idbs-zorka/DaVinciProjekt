from PySide6 import QtCore, QtWidgets, QtGui

class StationSelectWidget(QtWidgets.QWidget):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        QtWidgets.QTextEdit(parent=self)
