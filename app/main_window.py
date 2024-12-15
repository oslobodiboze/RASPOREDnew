import os
import sys
import re
import logging
import ftplib
import configparser
from zoneinfo import ZoneInfo
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QProgressDialog, QScrollArea, QMessageBox, QFileDialog, QMenu, QStatusBar, QWidget,QLineEdit,QDialog, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
from lxml import etree
import pandas as pd
from app.edit_window import EditWindow
from utils.excel_processor import process_excel
from utils.xmltv_converter import dataframe_to_xmltv, validate_xmltv, download_dtd


class LoadExcelThread(QThread):
    finished = pyqtSignal(pd.DataFrame, pd.DataFrame, str)
    error = pyqtSignal(Exception)

    def __init__(self, file_path, timezone):
        super().__init__()
        self.file_path = file_path
        self.timezone = timezone

    def run(self):
        try:
            display_df, internal_df = process_excel(self.file_path, self.timezone)
            self.finished.emit(display_df, internal_df, self.file_path)
        except Exception as e:
            self.error.emit(e)


class SaveXMLTVThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(Exception)

    def __init__(self, display_df, internal_df, save_path):
        super().__init__()
        self.display_df = display_df
        self.internal_df = internal_df
        self.save_path = save_path

    def run(self):
        try:
            xml_tree = dataframe_to_xmltv(self.display_df, self.internal_df, self.parent().TIMEZONE)
            xml_str = etree.tostring(xml_tree, pretty_print=True, encoding='UTF-8', xml_declaration=True)
            dtd_path = 'resources/xmltv.dtd'

            if not os.path.exists(dtd_path):
                download_dtd(dtd_path)

            validate_xmltv(etree.ElementTree(etree.fromstring(xml_str)), dtd_path)

            with open(self.save_path, 'wb') as f:
                f.write(xml_str)
            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(e)


class ExcelToXMLTVApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Excel to XMLTV Converter/Editor - DIADORA TV")
        self.setWindowIcon(QIcon('resources/icon.ico'))
        self.setGeometry(100, 100, 800, 400)

        self.TIMEZONE = ZoneInfo("Europe/Zagreb")
        self.display_df = None
        self.internal_df = None
        self.excel_file_path = None
        self.xmltv_file_path = None
        self.ftp_credentials = None
        self.excel_save_dir = os.path.join(os.getcwd(), 'saved_excels')
        os.makedirs(self.excel_save_dir, exist_ok=True)

        # Initialize logging
        logging.basicConfig(filename='converter.log', level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        

        self.init_ui()
        self.create_status_bar()
        self.create_menu()
        self.load_default_ftp_credentials()
        self.load_ftp_credentials() # Load saved FTP credentials after loading defaults


    def load_default_ftp_credentials(self):
        """Load FTP credentials from config.ini."""
        self.default_ftp_credentials = {
            'host': '',
            'username': '',
            'password': '',
            'port': 21
        }
        config_path = os.path.join(self.excel_save_dir, 'config.ini')

        if not os.path.exists(config_path):
            logging.warning(f"Config file {config_path} not found. Using default FTP credentials.")
            return

        try:
            config = configparser.ConfigParser()
            config.read(config_path)

            if 'FTP' in config:
                self.default_ftp_credentials.update({
                    'host': config['FTP'].get('host', ''),
                    'username': config['FTP'].get('username', ''),
                    'password': config['FTP'].get('password', ''),
                    'port': config['FTP'].getint('port', 21),
                })
            logging.info(f"Loaded FTP credentials from {config_path}: {self.default_ftp_credentials}")
        except Exception as e:
            logging.error(f"Error loading config file {config_path}: {e}")
            
    def convert_time_format(time_str):
        """Converts time string from HH.mm to HH:mm format."""
        if isinstance(time_str, str):
            match = re.match(r'^(\d{2})\.(\d{2})$', time_str)  # Check for HH.mm format
            if match:
                return f"{match.group(1)}:{match.group(2)}"
        return time_str  # Return original if no match        
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Učitaj Excel datoteku")
        self.load_button.clicked.connect(self.load_excel)
        button_layout.addWidget(self.load_button)

        self.save_button = QPushButton("Spremi kao XMLTV datoteku")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_xmltv)
        button_layout.addWidget(self.save_button)

        self.edit_button = QPushButton("Uredi Excel datoteku")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_excel)
        button_layout.addWidget(self.edit_button)

        self.upload_button = QPushButton("Pošalji na FTP")
        self.upload_button.setEnabled(False)
        self.upload_button.clicked.connect(self.upload_to_ftp)
        button_layout.addWidget(self.upload_button)

        self.close_button = QPushButton("Izlaz")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

        self.message = QLabel("")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.message)

        self.excel_list_widget = QListWidget()
        self.excel_list_widget.itemDoubleClicked.connect(self.open_excel_file)
        self.excel_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.excel_list_widget.customContextMenuRequested.connect(self.open_excel_context_menu)
        main_layout.addWidget(QLabel("Spremljene Excel datoteke:"))
        main_layout.addWidget(self.excel_list_widget)

        self.load_excel_file_list()
        
    def enter_ftp_credentials(self):
        """Open the FTP credentials dialog and save credentials if modified."""
        dialog = FTPCredentialsDialog(self.default_ftp_credentials, self)
        if dialog.exec():
            # Retrieve the entered credentials
            self.ftp_credentials = dialog.get_credentials()

            # Save the credentials to config.ini
            self.save_ftp_credentials()
            QMessageBox.information(self, "Uspjeh", "FTP podaci su uspješno spremljeni.")
            
    def load_ftp_credentials(self):
        config_path = os.path.join(self.excel_save_dir, 'config.ini')
        self.ftp_credentials = self.default_ftp_credentials.copy() # Start with defaults

        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            try:
                config.read(config_path)
                if 'FTP' in config:
                    self.ftp_credentials.update({
                        'host': config['FTP'].get('host', ''),
                        'username': config['FTP'].get('username', ''),
                        'password': config['FTP'].get('password', ''),
                        'port': config['FTP'].getint('port', 21),
                    })
                    logging.info(f"Loaded FTP credentials from {config_path}: {self.ftp_credentials}")
            except Exception as e:
                logging.error(f"Error loading config file {config_path}: {e}. Using default credentials.")

    def save_ftp_credentials(self):
        """Save the FTP credentials to config.ini."""
        config = configparser.ConfigParser()
        config['FTP'] = {
            'host': self.ftp_credentials['host'],
            'username': self.ftp_credentials['username'],
            'password': self.ftp_credentials['password'],
            'port': str(self.ftp_credentials['port']),
        }
        config_path = os.path.join(self.excel_save_dir, 'config.ini')
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        logging.info(f"FTP credentials saved to {config_path}")

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('Datoteka')

        load_action = QAction('Učitaj Excel datoteku', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.load_excel)
        file_menu.addAction(load_action)

        save_action = QAction('Spremi kao XMLTV datoteku', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_xmltv)
        save_action.setEnabled(False)
        file_menu.addAction(save_action)
        self.save_action = save_action

        exit_action = QAction('Izlaz', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        
        
        # FTP Menu
        ftp_menu = menubar.addMenu('FTP')

        ftp_credentials_action = QAction('FTP Podaci', self)
        ftp_credentials_action.triggered.connect(self.enter_ftp_credentials)
        ftp_menu.addAction(ftp_credentials_action)

        upload_action = QAction('Pošalji XMLTV na FTP', self)
        upload_action.triggered.connect(self.upload_to_ftp)
        ftp_menu.addAction(upload_action)
        
        # Pomoć meni
        help_menu = menubar.addMenu('Pomoć')
        
        help_action = QAction('Pomoć', self)
        help_action.triggered.connect(self.show_help_dialog)
        help_menu.addAction(help_action)
        
        about_action = QAction('O aplikaciji', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('Spreman za rad')

    def load_excel_file_list(self):
        self.excel_list_widget.clear()
        if os.path.exists(self.excel_save_dir):
            for file_name in os.listdir(self.excel_save_dir):
                if file_name.endswith(('.xlsx', '.xls')):
                    self.excel_list_widget.addItem(QListWidgetItem(file_name))

    def load_excel(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Odaberi Excel datoteku", self.excel_save_dir, "Excel datoteke (*.xlsx *.xls)") # Directly open file dialog
        if file_path:
            self.excel_file_path = file_path
            self.progress_dialog = QProgressDialog("Učitavanje Excel datoteke...", "Prekid", 0, 0, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.progress_dialog.setAutoClose(True)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setCancelButton(None)
            self.status_bar.showMessage("Učitavanje...", 3000)

            self.load_thread = LoadExcelThread(file_path, self.TIMEZONE)
            self.load_thread.finished.connect(self.on_load_finished)
            self.load_thread.error.connect(self.on_load_error)
            self.load_thread.start()
            self.progress_dialog.show()
            
    def on_load_finished_modified(self, display_df, internal_df, file_path):
        # Convert time format before passing to EditWindow
        display_df['START TIME'] = display_df['START TIME'].apply(self.convert_time_format)

        self.progress_dialog.close()
        self.display_df = display_df
        self.internal_df = internal_df
        self.excel_file_path = file_path
        self.message.setText("Excel datoteka uspješno učitana i obrađena.")
        self.save_action.setEnabled(True)
        self.save_button.setEnabled(True)
        self.edit_button.setEnabled(True)

    def convert_time_format(self, time_str):
        """Converts time string from HH.mm to HH:mm format."""
        if isinstance(time_str, str):
            match = re.match(r'^(\d{2})\.(\d{2})$', time_str)  # Check for HH.mm format
            if match:
                return f"{match.group(1)}:{match.group(2)}"
        return time_str  # Return original if no match

    def on_load_finished(self, display_df, internal_df, file_path):
        self.progress_dialog.close()
        self.display_df = display_df
        self.internal_df = internal_df
        self.excel_file_path = file_path
        self.message.setText("Excel datoteka uspješno učitana i obrađena.")
        self.save_action.setEnabled(True)
        self.save_button.setEnabled(True)
        self.edit_button.setEnabled(True)

    def on_load_error(self, e):
        self.progress_dialog.close()
        QMessageBox.critical(self, "Greška", f"Greška pri učitavanju Excel datoteke: {str(e)}")
        
    def on_save_finished(self, save_path):
        self.progress_dialog.close()
        self.message.setText("XMLTV datoteka uspješno spremljena i validirana.")
        self.message.setProperty("state", "success")
        self.upload_button.setEnabled(True)
        self.xmltv_file_path = save_path
        QMessageBox.information(self, "Uspjeh", f"XMLTV datoteka je uspješno spremljena!")
        logging.info(f"XMLTV datoteka spremljena na: {save_path}")

    def on_save_error(self, e):
        self.progress_dialog.close()
        self.message.setText("Došlo je do greške prilikom spremanja XMLTV datoteke.")
        self.message.setProperty("state", "error")
        QMessageBox.critical(self, "Greška", f"Greška prilikom spremanja XMLTV datoteke:\n{str(e)}")
        logging.error("Greška prilikom spremanja XMLTV datoteke:", exc_info=True)

    def save_xmltv(self):
        if self.display_df is None or self.internal_df is None:
            QMessageBox.warning(self, "Upozorenje", "Nema učitane Excel datoteke.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Spremi XMLTV datoteku", self.excel_save_dir, "XMLTV datoteke (*.xml)")
        if save_path:
            self.progress_dialog = QProgressDialog("Spremanje XMLTV datoteke...", None, 0, 0, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.progress_dialog.setCancelButton(None)
            self.progress_dialog.show()

            self.save_thread = SaveXMLTVThread(self.display_df, self.internal_df, save_path)
            self.save_thread.setParent(self) #Crucial line: Set the parent explicitly
            self.save_thread.finished.connect(self.on_save_finished)
            self.save_thread.error.connect(self.on_save_error)
            self.save_thread.start()

    def edit_excel(self):
        if self.excel_file_path and self.display_df is not None:
            edit_window = EditWindow(self.display_df, self.internal_df, self.excel_file_path, self.excel_save_dir, self)
        edit_window.data_saved.connect(self.on_edit_window_data_saved) #Connect the signal
        edit_window.exec()

    def on_edit_window_data_saved(self): #New slot to handle signal
        self.load_excel_file_list()  # Refresh file list

    def upload_to_ftp(self):
        if not self.xmltv_file_path:
            QMessageBox.warning(self, "Upozorenje", "Nema generirane XMLTV datoteke za upload.")
            return

        # Access credentials directly from the object
        if not self.ftp_credentials: # Check if credentials were loaded at all
            QMessageBox.warning(self, "Upozorenje", "FTP podaci nisu uneseni ili učitani.")
            self.enter_ftp_credentials() #Prompt to enter if not available
            if not self.ftp_credentials:
                return #Exit if still not available

        try:
            ftp = ftplib.FTP()
            ftp.connect(self.ftp_credentials['host'], self.ftp_credentials['port'])
            ftp.login(self.ftp_credentials['username'], self.ftp_credentials['password'])
            with open(self.xmltv_file_path, 'rb') as file:
                ftp.storbinary(f"STOR {os.path.basename(self.xmltv_file_path)}", file)
            ftp.quit()
            QMessageBox.information(self, "Uspjeh", "XMLTV datoteka je uspješno poslana na FTP server.")
        except Exception as e:
            QMessageBox.critical(self, "Greška", f"Greška pri slanju na FTP: {e}")

    def open_excel_file(self, item):
        file_name = item.text()
        file_path = os.path.join(self.excel_save_dir, file_name)
        if os.path.exists(file_path):
            self.load_excel(file_path)

    def open_excel_context_menu(self, position):
        """Open a context menu on right-click for the Excel list."""
        menu = QMenu()

        # Add "Učitaj Excel" option
        load_action = QAction("Učitaj Excel", self)
        load_action.triggered.connect(self.load_selected_excel)
        menu.addAction(load_action)

        # Add "Obriši datoteku" option
        delete_action = QAction("Obriši datoteku", self)
        delete_action.triggered.connect(self.delete_selected_excel)
        menu.addAction(delete_action)
        
        # Add "Otvori izvorišnu mapu" option
        open_folder_action = QAction("Otvori izvorišnu mapu", self)
        open_folder_action.triggered.connect(self.open_source_folder)
        menu.addAction(open_folder_action)

        # Display the menu
        menu.exec(self.excel_list_widget.viewport().mapToGlobal(position))
        
    def open_source_folder(self):
        """Opens the folder containing the saved Excel files."""
        item = self.excel_list_widget.currentItem()
        if item:
            file_name = item.text()
            file_path = os.path.join(self.excel_save_dir, file_name)
            if os.path.exists(file_path):
                try:
                    os.startfile(self.excel_save_dir) # Opens the directory in Windows Explorer
                except OSError as e:
                    QMessageBox.critical(self, "Greška", f"Došlo je do greške pri otvaranju mape: {e}")
            else:
                QMessageBox.warning(self, "Upozorenje", "Odabrana datoteka ne postoji.")
        else:
            QMessageBox.warning(self, "Upozorenje", "Niste odabrali datoteku.")

        
    def load_selected_excel(self):
        """Load the selected Excel file."""
        item = self.excel_list_widget.currentItem()
        if item:
            file_name = item.text()
            file_path = os.path.join(self.excel_save_dir, file_name)
            if os.path.exists(file_path):
                # Call the load_excel function for the selected file
                self.load_excel(file_path)
            else:
                QMessageBox.warning(self, "Upozorenje", "Odabrana datoteka ne postoji.")
        else:
            QMessageBox.warning(self, "Upozorenje", "Niste odabrali datoteku za učitavanje.")

    def delete_selected_excel(self):
        """Delete the selected Excel file."""
        item = self.excel_list_widget.currentItem()
        if item:
            file_name = item.text()
            file_path = os.path.join(self.excel_save_dir, file_name)
            reply = QMessageBox.question(
                self,
                "Potvrda brisanja",
                f"Jeste li sigurni da želite obrisati datoteku '{file_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.remove(file_path)
                    self.load_excel_file_list()  # Refresh the list
                    QMessageBox.information(self, "Obavijest", f"Datoteka '{file_name}' je uspješno obrisana.")
                except Exception as e:
                    QMessageBox.critical(self, "Greška", f"Došlo je do greške prilikom brisanja datoteke:\n{e}")
        else:
            QMessageBox.warning(self, "Upozorenje", "Niste odabrali datoteku za brisanje.")

    def show_about_dialog(self):
        QMessageBox.information(self, "O aplikaciji", "Excel to XMLTV Converter\nVerzija 3.6\nAutor: Daniel Vučinović")
        
    def show_help_dialog(self):
        help_text = """
        <h1>DiadoraTV XMLTV Editor - Upute za korištenje</h1>

        <h2>1. Uvod:</h2>
        <p>DiadoraTV XMLTV Editor je alat za stvaranje XMLTV datoteka iz Excel proračunskih tablica. Ova aplikacija pomaže vam u jednostavnom upravljanju i uređivanju podataka o TV programu, osiguravajući dosljedno oblikovanje i pružajući praktične značajke za pojednostavljenje vašeg radnog procesa.</p>

        <h2>3. Glavni prozor:</h2>
        <p><b>Odabir datoteke:</b> Glavni prozor prikazuje popis Excel datoteka pronađenih u direktoriju <code>saved_excels</code>.</p>
        <p><b>Učitavanje Excel datoteka:</b> Kliknite "Učitaj Excel" da biste otvorili dijalog za odabir datoteke ili jednostavno povucimo i ispustimo Excel datoteku (.xls, .xlsx) izravno na popis. Traka napretka pokazuje napredak učitavanja. Statusna traka će prikazati poruke o statusu učitavanja.</p>
        <p><b>Kontekstni izbornik Excel datoteke:</b> Desni klik na Excel datoteku na popisu pruža sljedeće opcije:</p>
        <ul>
            <li>"Učitaj Excel": Učitava odabranu Excel datoteku za uređivanje.</li>
            <li>"Obriši datoteku": Briše odabranu Excel datoteku. Ova radnja zahtijeva potvrdu.</li>
            <li>"Otvori izvorišnu mapu": Otvara direktorij <code>saved_excels</code> u Windows Exploreru.</li>
        </ul>

        <h2>4. Prozor za uređivanje:</h2>
        <p><b>Unos podataka:</b> Nakon učitavanja Excel datoteke, otvara se prozor za uređivanje. Možete izravno uređivati tablicu. Prilikom unosa podataka u stupac "POČETAK", jednostavno unesite sate i minute (npr. "1430"). Aplikacija automatski dodaje dvotočku.</p>
        <p><b>Dodavanje redaka:</b> Desni klik u tablici za dodavanje ili brisanje redaka ili korištenje gumba "Dodaj red" i "Obriši red" na alatnoj traci.</p>
        <p><b>Pretraživanje i zamjena:</b> Upotrijebite polja "Traži" i "Zamijeni sa" za pretraživanje i zamjenu teksta u tablici. Gumb zamijeni koristi tekst unesen u ova polja.</p>
        <p><b>Pomicanje datuma:</b> Upotrijebite gumbe "Datum +7" i "Datum +14" za pomicanje datuma u stupcu "DATUM" za 7 ili 14 dana, redom. Funkcionalnost poništavanja/ponavljanja dostupna je pomoću gumba "Poništi" i "Ponovi".</p>
        <p><b>Spremanje promjena:</b> Kliknite "Spremi" za spremanje promjena u trenutno otvorenu Excel datoteku ili "Spremi kao" za spremanje u novu Excel datoteku. Aplikacija provjerava preklapanja vremena između programa prije spremanja. Ako se otkrije preklapanje, prikazat će se upozorenje. Ako su podaci neispravni, to će također biti otkriveno.</p>

        <h2>5. Validacija podataka:</h2>
        <p>Aplikacija provjerava preklapanja vremena između programa prije spremanja. Ako se otkrije preklapanje vremena, prikazat će se upozorenje, sprječavajući spremanje datoteka s nevažećim podacima. Također će biti otkrivena i nedostajuća obvezna polja.</p>

        <h2>6. Poništavanje/ponavljanje:</h2>
        <p>Upotrijebite gumbe "Poništi" i "Ponovi" ili njihove ekvivalente u kontekstnom izborniku za poništavanje i ponavljanje promjena napravljenih tijekom uređivanja.</p>

        <h2>7. Zatvaranje aplikacije:</h2>
        <p>Kada zatvarate aplikaciju, provjerava se ima li nespremljenih promjena. Ako ih ima, prikazat će se dijalog koji će vas pitati želite li spremiti promjene prije izlaska.</p>

        <h2>8. FTP Funkcionalnost:</h2>
        <p>Aplikacija podržava slanje generirane XMLTV datoteke na FTP server.  Da biste koristili ovu značajku:</p>
        <ol>
            <li>Idite na meni <b>'FTP' > 'FTP Podaci'</b> i unesite potrebne podatke (host, korisničko ime, lozinka i port).</li>
            <li>Kliknite na gumb <b>'Pošalji na FTP'</b> nakon što ste spremili XMLTV datoteku.</li>
        </ol>

        <h3>Prečaci na tipkovnici:</h3>
        <ul>
            <li><b>Ctrl+O</b> - Učitaj Excel datoteku</li>
            <li><b>Ctrl+S</b> - Spremi kao XMLTV datoteku</li>
            <li><b>Ctrl+E</b> - Uredi Excel datoteku</li>
            <li><b>Ctrl+Q</b> - Izlaz iz aplikacije</li>
        </ul>
        """

        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Upute za korištenje")
        layout = QVBoxLayout()
        label = QLabel(help_text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.addWidget(label)
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        close_button = QPushButton("Zatvori")
        close_button.clicked.connect(help_dialog.accept)
        layout.addWidget(close_button)
        help_dialog.setLayout(layout)
        help_dialog.resize(600, 500)
        help_dialog.exec()

class FTPCredentialsDialog(QDialog):
    def __init__(self, default_credentials=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FTP Podaci")
        self.setGeometry(100, 100, 300, 200)

        self.default_credentials = default_credentials or {}

        # Set up the form
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()
        self.setLayout(layout)

        # Input fields
        self.host_input = QLineEdit(self)
        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.port_input = QLineEdit(self)

        # Mask password input
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Populate with default values
        self.host_input.setText(self.default_credentials.get('host', ''))
        self.username_input.setText(self.default_credentials.get('username', ''))
        self.password_input.setText(self.default_credentials.get('password', ''))
        self.port_input.setText(str(self.default_credentials.get('port', 21)))

        layout.addRow("FTP Host:", self.host_input)
        layout.addRow("Korisničko ime:", self.username_input)
        layout.addRow("Lozinka:", self.password_input)
        layout.addRow("Port:", self.port_input)

        # Save button
        save_button = QPushButton("Spremi")
        save_button.clicked.connect(self.accept)
        layout.addWidget(save_button)

    def get_credentials(self):
        """Retrieve entered credentials."""
        return {
            'host': self.host_input.text(),
            'username': self.username_input.text(),
            'password': self.password_input.text(),
            'port': int(self.port_input.text()) if self.port_input.text().isdigit() else 21,
        }