import sys
import logging
from PyQt6 import QtGui
from PyQt6.QtWidgets import QApplication
import os

from app.main_window import ExcelToXMLTVApp  # Import your main GUI application

basedir = os.path.dirname(__file__)

# Optional: Set Windows App User Model ID for better taskbar handling on Windows
try:
    from ctypes import windll  # Only exists on Windows.
    myappid = 'diadoratv.xmltveditor.beta.one'  # Arbitrary app ID for taskbar grouping
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

def main():
    # Create the logs directory if it doesn't exist
    log_dir = os.path.join(basedir, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logging
    log_file = os.path.join(log_dir, 'excel_to_xmltv.log')
    logging.basicConfig(
        filename=log_file,
        filemode='a',
        format='%(asctime)s %(levelname)s:%(message)s',
        level=logging.DEBUG
    )
    logging.info("Aplikacija je pokrenuta.")  # Log that the app has started

    # Create the QApplication
    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(basedir, 'resources', 'icon.ico')))
    
    # Initialize the main window *FIRST*
    window = ExcelToXMLTVApp()
    window.show()

    # Load and apply stylesheet *AFTER* creating the window
    style_path = os.path.join(basedir, 'resources', 'styles.qss')
    if os.path.exists(style_path):
        with open(style_path, 'r') as f:
            qss = f.read()
            app.setStyleSheet(qss)  # Now applied AFTER window creation
    else:
        logging.warning(f"Stylesheet not found: {style_path}")

    # Initialize and display the main window
    try:
        window = ExcelToXMLTVApp()  # Main window instance
        window.show()
        exit_code = app.exec()
        logging.info("Aplikacija je zatvorena.")  # Log application exit
        sys.exit(exit_code)
    except Exception as e:
        logging.critical("Dogodila se neočekivana greška:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
