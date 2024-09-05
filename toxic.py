#Telegram token
# 7316386678:AAEQbenWg2xxuLCOjhuGSvht67k5mPOIxrk

import os
import time
from PyQt5.QtWidgets import (QApplication, QDialog, QHBoxLayout, QVBoxLayout, QWidget, 
                             QLineEdit, QPushButton, QTableView, QMainWindow, QListWidget,
                             QSpinBox, QStatusBar, QProgressBar, QStyledItemDelegate, QMessageBox,
                             QDesktopWidget, QStyledItemDelegate, QMenu, QLabel, QDoubleSpinBox,
                             QDesktopWidget, QAction )
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QIcon, QPixmap
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel, pyqtSignal, QThread, QTimer, QByteArray, QBuffer, QIODevice
from concurrent.futures import ProcessPoolExecutor
from PyQt5.Qsci import QsciScintilla, QsciLexerPython
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import mplfinance as mpf
import pandas as pd
import sys
import numpy as np
from   scipy.stats       import t
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime, timedelta


from ib_async import *
import json
from PIL import Image
import io

from async_futures_ohlcv import *
from telegram_signal import send_telegram_message

selected_ticker = ""  

CONFIG_FILE = 'data/token/config.json'

def load_config():
    """Load configuration from the config file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    return {
        "bot_token": "",
        "channel_id": "",
        "send_signal_paused": False
    }        

def save_config(config):
    """Save configuration to the config file."""
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file, indent=4)
        

class SimplePythonEditor(QsciScintilla):
    ARROW_MARKER_NUM = 4
    def __init__(self, parent=None):
        super(SimplePythonEditor, self).__init__(parent)
        font = QFont()
        font.setFamily('Courier')
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.setFont(font)
        self.setMarginsFont(font)
        fontmetrics = QFontMetrics(font)
        self.setMarginsFont(font)
        self.setMarginWidth(0, fontmetrics.width("00000") + 6)
        self.setMarginLineNumbers(0, True)
        self.setMarginsBackgroundColor(QColor("#cccccc"))
        self.setMarginSensitivity(1, True)
        self.marginClicked.connect(self.on_margin_clicked)
        self.markerDefine(QsciScintilla.RightArrow, self.ARROW_MARKER_NUM)
        self.setMarkerBackgroundColor(QColor("#ee1111"), self.ARROW_MARKER_NUM)
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#ffe4e4"))
        lexer = QsciLexerPython()
        lexer.setDefaultFont(font)
        self.setLexer(lexer)
        text = bytearray(str.encode("utf8"))
        self.SendScintilla(QsciScintilla.SCI_STYLESETFONT, 1, text)
        self.SendScintilla(QsciScintilla.SCI_SETHSCROLLBAR, 0)
        self.setMinimumSize(600, 450)
    def on_margin_clicked(self, nmargin, nline, modifiers):
        if self.markersAtLine(nline) != 0:
            self.markerDelete(nline, self.ARROW_MARKER_NUM)
        else:
            self.markerAdd(nline, self.ARROW_MARKER_NUM)


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig, self.ax = plt.subplots( figsize=(width, height), dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)
        print('MPL Canvas calling')
        
    def plot_candlestick(self, data, symbol):
        print(f"Plotting Candlestick for symbol: {symbol}")
        self.ax.clear()
        mystyle = mpf.make_mpf_style(base_mpf_style='binance', rc={'axes.labelsize': 'small'}, gridstyle='-')
        mpf.plot(data, type='candle', ax=self.ax, show_nontrading=False, ylabel='', style=mystyle, xrotation=15, datetime_format='%Y-%m-%d')
        self.ax.grid(True)
        self.ax.set_visible(True)
        self.draw()
        print('MPL Canvas plot candlestick')
        
    def plot_vpin_cum_log_return(self, df, symbol):
        self.ax.clear()  # Clear the previous plot

        # plot_window = 1000
        # start_idx = -(plot_window + 100)
        # plot_df = df.iloc[start_idx:start_idx + plot_window].copy()
        plot_df = df.copy()
        plot_df.index = plot_df.index.astype(str)

        # Plot VPIN
        self.ax.plot(plot_df['cdf_vpin'], label='CDF VPIN', color='green')
        self.ax.axhline(y=0.8, color='r', linestyle='--')

        # Plot Cumulative Log Return
        self.ax.plot(plot_df['cum_log_return'], label='Cum Log Return', color='blue')

        # Set Title and Legend
        self.ax.set_title('CDF VPIN & Cumulative Log Return')
        self.ax.legend()

        # Remove x-ticks
        self.ax.set_xticks([])

        # Draw the updated plot
        self.draw()
        
        # check_vpin_and_send_alert(df,symbol)
        
class DataFrameModel(QAbstractTableModel):
    def __init__(self, data):
        QAbstractTableModel.__init__(self)
        self._data = data
    def rowCount(self, parent=None):
        return self._data.shape[0]
    def columnCount(self, parnet=None):
        return self._data.shape[1]
    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                value = self._data.iloc[index.row(), index.column()]
                if isinstance(value, float):
                    return float(value)
                return str(value)
        return None
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[col]
        return None
    def update_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

class NumberDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        if isinstance(value, float):
            return f"{value:,.2f}"  
        return super().displayText(value, locale)

class MyTableView(QTableView):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        self.proxy_model = QSortFilterProxyModel(self)
        self.setModel(self.proxy_model)
        self.setSortingEnabled(True)
        self.setItemDelegate(NumberDelegate(self))

        self.doubleClicked.connect(self.on_double_click)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.SingleSelection)

    def set_data(self, data):
        if not hasattr(self, 'data_model'):
            self.data_model = DataFrameModel(data)
            self.proxy_model.setSourceModel(self.data_model)
        else:
            self.data_model.update_data(data)
        self.sortByColumn(0, Qt.AscendingOrder)

    def get_row_data(self, row):
        model = self.proxy_model
        row_data = []
        for column in range(model.columnCount()):
            index = model.index(row, column)
            row_data.append(model.data(index))
        return row_data

    def on_double_click(self, index):
        row_data = self.get_row_data(index.row())
        self.act_on_row(row_data=row_data)
        print("on_double click")
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            index = self.currentIndex()
            if index.isValid():
                row_data = self.get_row_data(index.row())
                self.act_on_row(row_data=row_data)
        super().keyPressEvent(event)

    def act_on_row(self, row_data):
        symbol = row_data[0]
        selected_df = assets[symbol]
        plot_range = self.main_window.spin_box.value()
        self.main_window.canvas1.plot_candlestick(selected_df, symbol)
        self.main_window.canvas2.plot_vpin_cum_log_return(selected_df, symbol)
        pass

    def update_data(self, data):
        self.data_model.update_data(data)

class EditTokenDialog(QDialog):
    def __init__(self, file_path, title="Edit", label_text="Edit the Value:", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setGeometry(200, 200, 300, 100)

        self.file_path = file_path  # Path to the file to edit

        # Layout for the dialog
        self.layout = QVBoxLayout(self)

        # Label
        self.label = QLabel(label_text, self)
        self.layout.addWidget(self.label)

        # QLineEdit for user input
        self.input_field = QLineEdit(self)
        self.layout.addWidget(self.input_field)

        # Buttons for Save and Cancel
        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save", self)
        self.save_button.clicked.connect(self.save_file)
        self.button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.cancel_button)

        self.layout.addLayout(self.button_layout)

        self.load_file_content()

    def load_file_content(self):
        """Load content from the file into the input field."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as file:
                    content = file.readline().strip()
                    self.input_field.setText(content)
            else:
                QMessageBox.warning(self, "Error", f"File {self.file_path} does not exist!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read file: {e}")

    def save_file(self):
        # Save the modified content to the file
        new_content = self.input_field.text()

        try:
            with open(self.file_path, 'w') as file:
                file.write(new_content + '\n')

            QMessageBox.information(self, "Success", "Value updated successfully!")
            self.accept()  # Close the dialog
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORDER FLOW TOXICITY MONITOR")
        self.setWindowIcon(QIcon('favicon.ico'))
        self.setGeometry(400, 200, 1600, 900)
        
       
        self.config = load_config()
        self.send_signals = self.config.get("send_signal_paused", False)
        
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('File')

        # Add actions to the "File" menu
        new_action      = QAction('New', self)
        add_cfg_action  = QAction('Add new configuration file', self)
        edit_cfg_action = QAction('Edit configuration file', self)
        default_symbol_action = QAction('Choose default ticker to plot', self)
        open_action     = QAction('Open', self)
        exit_action     = QAction('Exit', self)


        exit_action.triggered.connect(self.close)

        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(add_cfg_action)
        file_menu.addAction(edit_cfg_action)
        file_menu.addAction(default_symbol_action)
        file_menu.addSeparator()  
        file_menu.addAction(exit_action)

        edit_menu = menu_bar.addMenu('Edit')

        cut_action = QAction('Cut', self)
        copy_action = QAction('Copy', self)
        paste_action = QAction('Paste', self)

        edit_menu.addAction(cut_action)
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)

        settings_menu        = menu_bar.addMenu('Telegram')
        telegram_token       = QAction('Bot token', self)
        telegram_channel     = QAction('Channel id', self)
        telegram_send_signal = QAction('Pause sending signal', self) 
        
        settings_menu.addAction(telegram_token)
        settings_menu.addAction(telegram_channel)
        settings_menu.addAction(telegram_send_signal)

        # Connect the actions to their respective functions
        telegram_token.triggered.connect(self.edit_telegram_token)
        telegram_channel.triggered.connect(self.edit_telegram_channel)
        telegram_send_signal.triggered.connect(self.pause_sending_signal)


        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout()
        
        # Column 1 Layout 
        column1 = QVBoxLayout()

        # Countdown Timer
        self.countdown_label = QLabel(self)
        self.countdown_label.setFixedWidth(100)
        # Initialize the timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.remaining_time = 60  # 60 seconds countdown
        
        # Start the timer (if needed)
        self.timer.start(1000)  # Update every second
        
        self.index_input = QLineEdit()
        self.index_input.setPlaceholderText("Enter Index (e.g., NKD)")
        self.add_index_button = QPushButton('+ Add Futures Symbols')
        self.add_index_button.clicked.connect(lambda: self.add_new_symbol(self.index_input))
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)  # Connect the double-click event
        self.list_widget.customContextMenuRequested.connect(self.open_context_menu)  # Connect right-click to context menu
        column1.addWidget(self.countdown_label)
        
        column1.addWidget(self.index_input)
        column1.addWidget(self.add_index_button)
        column1.addWidget(self.list_widget)
        
        #Column 2 Layout
        column2 = QVBoxLayout()
        
        #SIGMA section
        self.sigma_box = QSpinBox()
        self.sigma_label = QLabel("SIGMA_WINDOW")
        self.sigma_box.setRange(1, 100)
        self.sigma_box.setValue(40)

        sigma_layout = QHBoxLayout()
        sigma_layout.addWidget(self.sigma_label)
        sigma_layout.addWidget(self.sigma_box)
        
        #DOF section
        self.dof_box = QDoubleSpinBox()
        self.dof_label = QLabel("DOF")
        self.dof_box.setValue(0.25)
        
        dof_layout = QHBoxLayout()
        dof_layout.addWidget(self.dof_label)
        dof_layout.addWidget(self.dof_box)
        
        #Volume
        self.volume_box = QSpinBox()
        self.volume_label = QLabel("VOLUME")
        self.volume_box.setValue(25)
        
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume_box)       
        
        #VPIN_WINDOW
        self.VPIN_box = QSpinBox()
        self.VPIN_label = QLabel("VPIN_WINDOW")
        self.VPIN_box.setValue(30)
        
        VPIN_layout = QHBoxLayout()
        VPIN_layout.addWidget(self.VPIN_label)
        VPIN_layout.addWidget(self.VPIN_box)      
        
        #Here comes canvas
        self.canvas1 = MplCanvas(self, width=5, height=5, dpi=100)
        self.canvas2 = MplCanvas(self, width=5, height=5, dpi=100)

        self.table_view = MyTableView(self)

        # Add horizontal layouts and other widgets to column2
        column2.addLayout(sigma_layout)  # Use addLayout for horizontal layouts
        column2.addLayout(dof_layout)    # Use addLayout for horizontal layouts
        column2.addLayout(volume_layout) 
        column2.addLayout(VPIN_layout)       
        
        column2.addWidget(self.canvas1)
        column2.addWidget(self.canvas2)
        
        self.main_layout.addLayout(column1, 1)
        self.main_layout.addLayout(column2, 3)
        self.main_layout.addWidget(self.table_view, 4)
        
        self.main_widget.setLayout(self.main_layout)

        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.progress_bar = QProgressBar(self)
        self.statusBar.addPermanentWidget(self.progress_bar)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        self.setup_index_list()
        
        self.executor = ProcessPoolExecutor()
        self.show()
    
    def edit_telegram_token(self):
        # Open the dialog to edit the Telegram bot token
        dialog = EditTokenDialog('data/token/bot_token.txt', title="Edit Telegram Bot Token", label_text="Edit the Bot Token:")
        dialog.exec_()

    def edit_telegram_channel(self):
        # Open the dialog to edit the Telegram channel ID
        dialog = EditTokenDialog('data/token/channel_token.txt', title="Edit Telegram Channel ID", label_text="Edit the Channel ID:")
        dialog.exec_()

    def pause_sending_signal(self):
            """Pause or resume sending signals."""
            self.send_signals = not self.send_signals
            self.config['send_signal_paused'] = not self.send_signals
            save_config(self.config)
            state = "paused" if not self.send_signals else "resumed"
            QMessageBox.information(self, "Pause Sending Signal", f"Sending signals has been {state}.")

        
    def setup_index_list(self):
        # Clear the list and add items from the ./indices directory
        self.list_widget.clear()
        os.makedirs("./indices", exist_ok=True)
        for filename in os.listdir("./indices"):
            self.list_widget.addItem(filename)
    
    def add_new_symbol(self, adding_symbol):
        
        symbol_name = adding_symbol.text().strip()

        if symbol_name:  
            file_path = os.path.join("./indices", symbol_name)
            try:
                with open(file_path, 'w') as f:
                    f.write("")  

                self.setup_index_list()
            except Exception as e:
                print(f"Failed to add new symbol '{symbol_name}': {e}")
        else:
            print("Symbol name cannot be empty!")
            
    def open_context_menu(self, position):
        # Create context menu
        context_menu = QMenu(self)

        # Add actions to the menu
        delete_action = QAction('Delete', self)
        delete_action.triggered.connect(self.delete_selected_item)
        context_menu.addAction(delete_action)

        context_menu.exec_(self.list_widget.mapToGlobal(position))

    def delete_selected_item(self):
        # Get the selected item
        selected_item = self.list_widget.currentItem()
        if selected_item:
            file_path = os.path.join("./indices", selected_item.text())
            try:
                os.remove(file_path)  # Remove the file
                self.setup_index_list()  # Refresh the list
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file: {e}")      
    # Run loop for signal sending
    def loop_through_folder_and_download(self, folder_path="./indices"):
        
        try:
            files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        except FileNotFoundError:
            print(f"The folder '{folder_path}' does not exist.")
            return
        except Exception as e:
            print(f"Error accessing the folder '{folder_path}': {e}")
            return

        for file_name in files:
            symbol_name = file_name.strip()  # Get the file name
            if symbol_name:
                print(f"Downloading data for symbol: {symbol_name}")
                # Call your download function here
                # self.check_and_send_signal(symbol_name)
            else:
                print("File name is empty, skipping...")
            
    def save_canvas_as_temp_image(self, new_df):
    # Create a new figure and axis
        fig, ax = plt.subplots()
        
        # Plot on the axis
        self.canvas1.plot_vpin_cum_log_return(new_df, 'AAPL')

        # Save the figure to a file
        directory = 'data/pictures'
        os.makedirs(directory, exist_ok=True)  
        file_path = os.path.join(directory, 'temp_image.png')

        # Save the current figure
        plt.savefig(file_path, format='png')

        # Close the plot to avoid overlapping issues
        plt.close(fig)

        return file_path

    def save_canvas_as_temp_image(self, new_df):
        canvas_widget = self.canvas1  
        
        pixmap = QPixmap(canvas_widget.size())
        canvas_widget.render(pixmap)

        qimage = pixmap.toImage()

        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        qimage.save(buffer, 'PNG')
        buffer.close()
        
        directory = 'data/pictures'
        os.makedirs(directory, exist_ok=True)  
        file_path = os.path.join(directory, 'temp_image.png')
        
        # Convert QByteArray to BytesIO
        byte_array_data = byte_array.data()
        byte_stream = io.BytesIO(byte_array_data)

        # Convert BytesIO to Pillow Image
        pil_image = Image.open(byte_stream)

        # Save the image
        pil_image.save(file_path)  # Save using the full file path
        print("Image saved to:", file_path)
        
        return file_path
        
    def check_vpin_and_send_alert(self, df, symbol):
        
        try:

            if df['vpin'].iloc[-1] > 0.1:
                print("VPIN is greater than 0.8, sending alert...")
                temp_image = self.save_canvas_as_temp_image(df)
                # If the condition is met, call the async function to send a telegram message
                asyncio.run(send_telegram_message(symbol, temp_image))
            else:
                print("VPIN is not greater than 0.8, no alert sent.")
        
        except Exception as e:
            print(f"An error occurred while checking VPIN or sending alert: {e}")
    
    def on_item_double_clicked(self, item):
        
        item_name = item.text()
        #print(item_name)

        global selected_ticker
        selected_ticker = item_name
        print(selected_ticker, selected_ticker, selected_ticker)
        self.download_and_plot()
       # self.start_countdown()
        
    def download_and_plot(self):
        
        if not selected_ticker:
            symbol = "ES" 
        else:
            symbol = selected_ticker
        
        print(symbol, selected_ticker, symbol)
                       
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        df = get_futures_data(symbol)
        try: 
            new_df = self.prepare_data(df)

            self.canvas2.plot_candlestick(new_df, 'AAPL')        
            self.canvas1.plot_vpin_cum_log_return(new_df, 'AAPL')
            self.check_vpin_and_send_alert(new_df, symbol)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Information)
            error_msg.setInformativeText(f"An error occurred: {e}")
            error_msg.setText("Given tickers contract not found in Interactive brokers")
            error_msg.setWindowTitle("Error fetching historical data")
            error_msg.setWindowIcon(QIcon('favicon.ico'))
            error_msg.exec_()
        
    def on_data_ready(self, filename):
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Data Downloaded", f"Data saved to {filename}")
        
    # def start_countdown(self):
    #     self.remaining_time = 60
    #     self.timer.start(1000)  # 1000 ms = 1 second
        
    def update_countdown(self):
        self.remaining_time -= 1
        if self.remaining_time <= 0:
            try:
                
                # self.download_and_plot()
                self.remaining_time = 60
                self.timer.start(1000)
                if self.send_signals:
                    self.loop_through_folder_and_download()

            except Exception as e:
                print("Failed to update chart", e)
                
        else:
            self.countdown_label.setText(f"Time: {self.remaining_time}s")
    
        
    def prepare_data(self, df):
        
        SIGMA_WINDOW  = self.sigma_box.value()
        DOF           = self.dof_box.value()
        VOLUME_WINDOW = self.volume_box.value()
        VPIN_WINDOW   = self.VPIN_box.value()
        VPIN_SMOOTH   = 5


        df['cum_log_return'] = (df['Close']/df['Close'].iloc[0]).apply(np.log)
        df['return'        ] = df['cum_log_return'].diff().fillna(0.0)
        df['sigma'         ] = df['return'].rolling(SIGMA_WINDOW).std().fillna(0.0)

        def label(r, sigma):
            if sigma>0.0:
                cum = t.cdf(r/sigma, df=DOF)
                return 2*cum-1.0
            else:
                return 0.0

        df['label'       ] = df.apply(lambda x: label(x['return'], x['sigma']), axis=1)
        df['volume_sign' ] = df['label'].apply(np.sign)
        df['volume_label'] = df['Volume']*df['volume_sign']


        def sum_positives(arr):
            arr = np.array(arr)
            return np.sum(arr[arr>=0])
        def sum_negatives(arr):
            arr = np.array(arr)
            return np.abs(np.sum(arr[arr<0]))

        df["buy_volume" ] = df['volume_label'].rolling(VOLUME_WINDOW).apply(lambda w: sum_positives(w.values))
        df['sell_volume'] = df['volume_label'].rolling(VOLUME_WINDOW).apply(lambda w: sum_negatives(w.values))

        def calculate_vpin(buy_volume, sell_volume, window_size):
            vpin  = buy_volume.sub(sell_volume).abs().rolling(window_size).mean()
            vpin /= (buy_volume+sell_volume)
            return vpin

        df['vpin'           ] = calculate_vpin(df['buy_volume'], df['sell_volume'], VPIN_WINDOW)
        df['cdf_vpin'       ] = df['vpin'    ].rank(method='average', pct=True)
        df['cdf_vpin_smooth'] = df['cdf_vpin'].ewm(span=VPIN_SMOOTH,min_periods=0,adjust=False,ignore_na=False).mean()

        # symbol = "ES"
        # self.check_vpin_and_send_alert(df, symbol)

        return df

        
if __name__ == "__main__":

    print("Loading stock data...")
    start_time = time.perf_counter()
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())