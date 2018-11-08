#!/usr/bin/env python3
import sys, os, csv, glob, datetime, re
from math import log10
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QFileSystemModel, QTreeView, QMessageBox,
    QPushButton, QVBoxLayout, QDesktopWidget, qApp, QAction, QStatusBar, QAbstractItemView, QShortcut,
    QFileDialog, QLabel, QLineEdit, QGridLayout, QProgressBar, QRadioButton, QHBoxLayout, 
    QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QMenu, QToolBar, QTabWidget, QSplitter)
from PyQt5 import QtCore, Qt
from PyQt5.QtCore import pyqtSlot, QBasicTimer, QModelIndex
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.Qt import QApplication, QClipboard
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
import time
import visa


# File paths
app_fp = Path(os.path.dirname(os.path.abspath(__file__)))

FP_CSV = app_fp / Path('CSV Files')
FP_AF = app_fp / Path('Correction Factors') / Path('Antenna')
FP_CABLEF = app_fp / Path('Correction Factors') / Path('Cable')
FP_PREAMPF = app_fp / Path('Correction Factors') / Path('Preamp')
FP_ATTF = app_fp / Path('Correction Factors') / Path('Attenuator')
FP_SP = app_fp / Path('Scan Profiles')
FP_CF = app_fp / Path('Correction Factors')
FP_EQ = app_fp / FP_CF / Path('Equipment Profiles')
FP_MASK = app_fp / Path('Frequency Masks')


def create_sub_directories():

  dir_list = [FP_CF, 
              FP_CSV, 
              FP_AF, 
              FP_CABLEF, 
              FP_PREAMPF, 
              FP_EQ, 
              FP_SP, 
              FP_ATTF,
              FP_MASK,
              ]

  for folder in dir_list:
    folder = app_fp / folder
    if not folder.exists():
      os.makedirs(folder) 

class FileSystemModel(QFileSystemModel):
  def __init__(self, *args, **kwargs):
    super(FileSystemModel, self).__init__(*args, **kwargs)
    self.condition = False

  def setCondition(self, condition, legend):
    self.condition = condition
    self.legend = legend
    for i in range(0, len(self.legend), 1):
      if ' - Vertical' in self.legend[i]:
        self.legend[i] = self.legend[i].replace(' - Vertical', '')
      if ' - Horizontal' in self.legend[i]:
        self.legend[i] = self.legend[i].replace(' - Horizontal', '')
      
    self.dataChanged.emit(QModelIndex(), QModelIndex())

  def data(self, index, role=QtCore.Qt.DisplayRole):
    if self.condition and role == QtCore.Qt.TextColorRole:
      text = index.data(QtCore.Qt.DisplayRole)
      text = text.replace('.csv', '')
      text = text.replace('.DAT', '')
      if self.condition and text in self.legend:
        return QColor('#58cd1c')
    return super(FileSystemModel, self).data(index, role)

class correctionFactorPopup(QWidget):
  def __init__(self, parent):
    super().__init__()
    self.parent = parent
    self.initUI()

  def initUI(self):
    # Labels
    save_label = QLabel('Save profile as:')
    save_label.setAlignment(QtCore.Qt.AlignRight)
    eq_profile_label = QLabel('Select Equipment Profile')
    eq_profile_label.setAlignment(QtCore.Qt.AlignRight)
    af_label = QLabel('Antenna Factor')
    af_label.setAlignment(QtCore.Qt.AlignRight)
    preamp_label = QLabel('Preamp Factor')
    preamp_label.setAlignment(QtCore.Qt.AlignRight)
    c_label = QLabel('Cable Factor')
    c_label.setAlignment(QtCore.Qt.AlignRight)
    atten1_label = QLabel('Attenuator Factor #1')
    atten1_label.setAlignment(QtCore.Qt.AlignRight)
    atten2_label = QLabel('Attenuator Factor #2')
    atten2_label.setAlignment(QtCore.Qt.AlignRight)
    atten3_label = QLabel('Attenuator Factor #3')
    atten3_label.setAlignment(QtCore.Qt.AlignRight)
    distance_from_label = QLabel('Distance Correct From (m)')
    distance_from_label.setAlignment(QtCore.Qt.AlignRight)
    distance_to_label = QLabel('Distance Correct To (m)')
    distance_to_label.setAlignment(QtCore.Qt.AlignRight)

    # Entries
    self.save_entry = QLineEdit()
    self.distance_from_entry = QLineEdit()
    self.distance_to_entry = QLineEdit()

    # Comboboxes
    self.eq_combo = QComboBox()
    self.eq_combo.currentIndexChanged.connect(self.load_eq_prof)
    self.af_combo = QComboBox()
    self.preamp_combo = QComboBox()
    self.c_combo = QComboBox()
    self.atten1_combo = QComboBox()
    self.atten2_combo = QComboBox()
    self.atten3_combo = QComboBox()

    # Get correction factor files
    eq_list = ['None']
    eq_list.extend(self.parent.format_filepath(
        FP_EQ.glob('*.csv')))
    af_list = ['None']
    af_list.extend(self.parent.format_filepath(
        FP_AF.glob('*.csv')))
    preamp_list = ['None']
    preamp_list.extend(self.parent.format_filepath(
        FP_PREAMPF.glob('*.csv')))
    cable_list = ['None']
    cable_list.extend(self.parent.format_filepath(
        FP_CABLEF.glob('*.csv')))
    atten_list = ['None']
    atten_list.extend(self.parent.format_filepath(
        FP_ATTF.glob('*.csv')))

    # Populate combox with correction factor files
    self.eq_combo.addItems(eq_list)
    self.af_combo.addItems(af_list)
    self.preamp_combo.addItems(preamp_list)
    self.c_combo.addItems(cable_list)
    self.atten1_combo.addItems(atten_list)
    self.atten2_combo.addItems(atten_list)
    self.atten3_combo.addItems(atten_list)

    # Buttons
    okay_btn = QPushButton('Okay')
    okay_btn.setMaximumWidth(115)
    okay_btn.clicked.connect(self.generate_factors)
    cancel_btn = QPushButton('Cancel')
    cancel_btn.clicked.connect(self.close)

    # Layout (row, column, rowspan, columnspan)
    grid = QGridLayout()
    self.setLayout(grid)
    grid.addWidget(save_label, 0, 0, 1, 1)
    grid.addWidget(self.save_entry, 0, 1, 1, 2)
    grid.addWidget(eq_profile_label, 1, 0, 1, 1)
    grid.addWidget(self.eq_combo, 1, 1, 1, 2)
    grid.addWidget(af_label, 2, 0, 1, 1)
    grid.addWidget(self.af_combo, 2, 1, 1, 2)
    grid.addWidget(preamp_label, 3, 0, 1, 1)
    grid.addWidget(self.preamp_combo, 3, 1, 1, 2)
    grid.addWidget(c_label, 4, 0, 1, 1)
    grid.addWidget(self.c_combo, 4, 1, 1, 2)
    grid.addWidget(atten1_label, 5, 0, 1, 1)
    grid.addWidget(self.atten1_combo, 5, 1, 1, 2)
    grid.addWidget(atten2_label, 6, 0, 1, 1)
    grid.addWidget(self.atten2_combo, 6, 1, 1, 2)
    grid.addWidget(atten3_label, 7, 0, 1, 1)
    grid.addWidget(self.atten3_combo, 7, 1, 1, 2)
    grid.addWidget(distance_from_label, 8, 0, 1, 1)
    grid.addWidget(self.distance_from_entry, 8, 1, 1, 2)
    grid.addWidget(distance_to_label, 9, 0, 1, 1)
    grid.addWidget(self.distance_to_entry, 9, 1, 1, 2)
    grid.addWidget(okay_btn, 10, 0, 1, 1)
    grid.addWidget(cancel_btn, 10, 2, 1, 1)

  def save_eq_prof(self):
    # Method to save the current combobox values
    if self.save_entry.text():
      cf_list = []
      cf_list.append(self.af_combo.currentText())
      cf_list.append(self.preamp_combo.currentText())
      cf_list.append(self.c_combo.currentText())
      cf_list.append(self.atten1_combo.currentText())
      cf_list.append(self.atten2_combo.currentText())
      cf_list.append(self.atten3_combo.currentText())
      try:
        cf_list.append(self.distance_from_entry.text())
        cf_list.append(self.distance_to_entry.text())
      except ValueError:
        cf_list.append('')
      finally:
        filename = self.save_entry.text()+'.csv'
        with open(FP_EQ / filename, 'w') as eq_file:
          eq_writer = csv.writer(eq_file, delimiter=',')
          for cf in cf_list:
            eq_writer.writerow([cf])

  def load_eq_prof(self):
    # Method to load a saved set of combobox values
    if self.eq_combo.currentText() == 'None':
      self.af_combo.setCurrentText('None')
      self.preamp_combo.setCurrentText('None')
      self.c_combo.setCurrentText('None')
      self.atten1_combo.setCurrentText('None')
      self.atten2_combo.setCurrentText('None')
      self.atten3_combo.setCurrentText('None')
      self.distance_from_entry.setText('')
      self.distance_to_entry.setText('')
    elif self.eq_combo.currentText() != 'None':
      eq_list = []
      filename = self.eq_combo.currentText()+'.csv'
      with open(FP_EQ / filename, 'r') as eq_file:
        eq_reader = csv.reader(eq_file)
        eq_list = list(eq_reader)
      self.af_combo.setCurrentText(eq_list[0][0])
      self.preamp_combo.setCurrentText(eq_list[1][0])
      self.c_combo.setCurrentText(eq_list[2][0])
      self.atten1_combo.setCurrentText(eq_list[3][0])
      self.atten2_combo.setCurrentText(eq_list[4][0])
      self.atten3_combo.setCurrentText(eq_list[5][0])
      try:
        self.distance_from_entry.setText(eq_list[6][0])
        self.distance_to_entry.setText(eq_list[7][0])
      except IndexError:
        self.distance_from_entry.setText('')
    
  def generate_factors(self):
    # Method to generate a correction factor dataframe
    self.save_eq_prof()

    # Clear the dataframe before merging data
    self.parent.cfdata = pd.DataFrame(columns=['Frequency (MHz)'])

    # Read in data and merge to cfdata frame
    if self.af_combo.currentText() != 'None':
      filename = self.af_combo.currentText()+'.csv'
      antenna_factors = pd.read_csv(FP_AF / filename)
      antenna_factors.columns = ['Frequency (MHz)', self.af_combo.currentText()]
      self.parent.cfdata = self.parent.cfdata.merge(antenna_factors,
                                      on='Frequency (MHz)', how='outer')
    if self.preamp_combo.currentText() != 'None':
      filename = self.preamp_combo.currentText()+'.csv'
      preamp_factors = pd.read_csv(FP_PREAMPF / filename)
      preamp_factors.iloc[:, 1] *= -1
      preamp_factors.columns = ['Frequency (MHz)', self.preamp_combo.currentText()]
      self.parent.cfdata = self.parent.cfdata.merge(preamp_factors,
                                      on='Frequency (MHz)', how='outer')
    if self.c_combo.currentText() != 'None':
      filename = self.c_combo.currentText()+'.csv'
      cable_factors = pd.read_csv(FP_CABLEF / filename)
      cable_factors.columns = ['Frequency (MHz)', self.c_combo.currentText()]
      self.parent.cfdata = self.parent.cfdata.merge(cable_factors,
                                      on='Frequency (MHz)', how='outer')
    if self.atten1_combo.currentText() != 'None':
      filename = self.atten1_combo.currentText()+'.csv'
      attenuator1_factors = pd.read_csv(FP_ATTF / filename)
      attenuator1_factors.iloc[:, 1] *= -1
      attenuator1_factors.columns = ['Frequency (MHz)', self.atten1_combo.currentText()]
      self.parent.cfdata = self.parent.cfdata.merge(attenuator1_factors,
                                      on='Frequency (MHz)', how='outer')
    if self.atten2_combo.currentText() != 'None':
      filename = self.atten2_combo.currentText()+'.csv'
      attenuator2_factors = pd.read_csv(FP_ATTF / filename)
      attenuator2_factors.iloc[:, 1] *= -1
      attenuator2_factors.columns = ['Frequency (MHz)', self.atten2_combo.currentText()]
      self.parent.cfdata = self.parent.cfdata.merge(attenuator2_factors,
                                      on='Frequency (MHz)', how='outer')
    if self.atten3_combo.currentText() != 'None':
      filename = self.atten3_combo.currentText()+'.csv'
      attenuator3_factors = pd.read_csv(FP_ATTF / filename)
      attenuator3_factors.iloc[:, 1] *= -1
      attenuator3_factors.columns = ['Frequency (MHz)', self.atten3_combo.currentText()]
      self.parent.cfdata = self.parent.cfdata.merge(attenuator3_factors,
                                      on='Frequency (MHz)', how='outer')

    # Distance correction factor
    d_from = self.distance_from_entry.text()
    d_to = self.distance_to_entry.text()
    if d_from and d_to:
      distance_cf = 20 * log10(float(d_from) / float(d_to))
    if self.parent.cfdata.empty:
      self.parent.cfdata['Frequency (MHz)'] = np.linspace(30, 40000, 30001)
    self.parent.cfdata['DCF'] = distance_cf

    # Sort and interpolate missing values for each column
    self.parent.cfdata = self.parent.cfdata.sort_values(by=['Frequency (MHz)'])
    self.parent.cfdata = self.parent.cfdata.set_index('Frequency (MHz)', drop=False)
    self.parent.cfdata = self.parent.interpolate_cf(self.parent.cfdata)

    # Close menu
    self.hide()

  def close(self):
    self.parent.cf_checkbox.setChecked(False)
    self.hide()

class settingsPopup(QWidget):
  def __init__(self, parent):
    super().__init__()
    self.parent = parent
    self.initUI()

  def initUI(self):
    # Timer edit
    self.timer_edit = QLineEdit()
    self.timer_edit.setText(str(self.parent.timer))

    # Peaks edit
    self.peaks_edit = QLineEdit()
    self.peaks_edit.setText(str(self.parent.num_of_peaks))

    # Label
    self.timer_label = QLabel('Timer (s)')
    self.peaks_label = QLabel('Peaks (#)')

    # Buttons
    ok_btn = QPushButton('Okay')
    ok_btn.clicked.connect(self.okay)
    cancel_btn = QPushButton('Cancel')
    cancel_btn.clicked.connect(self.hide)

    # Layout (row, column, rowspan, columnspan)
    grid = QGridLayout()
    self.setLayout(grid)
    grid.addWidget(self.timer_label, 0, 0, 1, 2)
    grid.addWidget(self.timer_edit, 0, 1, 1, 2)
    grid.addWidget(self.peaks_label, 1, 0, 1, 2)
    grid.addWidget(self.peaks_edit, 1, 1, 1, 2)
    grid.addWidget(ok_btn, 2, 0, 1, 1)
    grid.addWidget(cancel_btn, 2, 2, 1, 1)

  def okay(self):
    self.parent.timer = int(self.timer_edit.text())
    self.parent.num_of_peaks = int(self.peaks_edit.text())
    self.hide()
    
class scanPopup(QWidget):
  def __init__(self, parent):
    super().__init__()
    self.parent = parent
    self.time = self.parent.timer
    self.completed = 0
    self.saved = False
    self.initUI()
    
    # Connect and configure SA
    self.parent.connect_to_sa()
    if self.parent.scan_combo.currentText() != 'Custom':
      params = self.get_scan_parameters()
      self.configure_sa(params)

    # On valid filename and connection start scan
    if self.verify_filename():
      self.start_progress()
    else:
      self.status_label.setText('Enter Filename')
      self.save_btn.setText('Start Scan')

  def initUI(self):
    # Label
    self.status_label = QLabel('Scanning')

    # Progressbar
    self.progress = QProgressBar(self)
    self.progress.setTextVisible(True)
    self.progress.setMinimum(self.completed)
    self.progress.setMaximum(self.time)
    self.progress.setFormat('%m')

    # Timer
    self.timer = QBasicTimer()

    # Buttons
    self.save_btn = QPushButton('Save Scan')
    self.save_btn.clicked.connect(self.save_trace)
    cancel_btn = QPushButton('Cancel')
    cancel_btn.clicked.connect(self.cancel)

    # Layout (row, column, rowspan, columnspan)
    grid = QGridLayout()
    self.setLayout(grid)
    grid.addWidget(self.status_label, 0, 0, 1, 3)
    grid.addWidget(self.progress, 1, 0, 1, 3)
    grid.addWidget(self.save_btn, 2, 0, 1, 1)
    grid.addWidget(cancel_btn, 2, 2, 1, 1)

  def verify_filename(self):
    name = self.parent.scan_name_edit.text()
    if name:
      # Format the file string to remove unwanted chars
      if '.' in name:
        name = name.replace('.', '_')
        self.parent.scan_name_edit.setText(name)
      if ' ' in name:
        name = name.replace(' ', '_')
        self.parent.scan_name_edit.setText(name)
      
      # Prevent duplicate files by adding a number to the end of the filename
      filename = self.parent.scan_name_edit.text()
      f = filename + '.csv'
      if os.path.exists(self.parent.workspace / f):
        i = 1
        f = f + str(i) + '.csv'
        while os.path.exists(self.parent.workspace / f):
          i += 1
          f = f = f + str(i) + '.csv'
        self.parent.scan_name_edit.setText(name + str(i))
      
      # Finally return True once a valid filename has been generated
      return True
    else:
      return False
  
  def get_scan_parameters(self):
    scan = self.parent.scan_combo.currentText() + '.csv'
    scan_params = []

    with open(FP_SP + scan, 'r') as settings:
      r_settings = csv.reader(settings)
      for row in r_settings:
        scan_params.append(row[0])

    #print(scan_params)
    return scan_params

  def configure_sa(self, params):
    # Takes a list of SCPI commands and writes them to the spectrum analyzer
    sweep = True

    # Keep display on
    self.parent.sa.write('INIT:CONT ON')

    for parameter in params:
      # Convert Rhode commands to Agilent commands
      if 'Agilent' in self.parent.instr:
        if 'MODE' in parameter:
          parameter = parameter.strip('DISP:')
          parameter = parameter.replace('MODE', 'TYPE')
        if 'DISP:TRAC' and 'ON' in parameter:
          parameter = parameter.strip('DISP:')
          parameter = parameter.split(' ')
          parameter = parameter[0] + ':DISP ' + parameter[1]
        if 'INP:ATT' in parameter:
          parameter = parameter.replace('INP', 'LIST')
        if 'INP:GAIN:STAT' in parameter:
          parameter = parameter.replace('INP', 'POW')
      
      # Check if sweep points parameter has been given
      if 'SWE:POIN' in parameter:
        sweep = False
      self.parent.sa.write(parameter)

    if sweep:
      self.set_sweep_points()

  def set_sweep_points(self):
    span = float(self.parent.sa.query('FREQ:SPAN?'))
    rbw = float(self.parent.sa.query('BAND?'))
    sweep_points = str(2 * (span / rbw) + 1)
    self.parent.sa.write('SWE:POIN ' + sweep_points)
    self.check_sweep_points(sweep_points)

  def check_sweep_points(self, swp_pts):
    sa_swp_pts = self.parent.sa.query('SWE:POIN?')
    if swp_pts == sa_swp_pts:
      return True
    else:
      self.sweep_pts_warning(sa_swp_pts)
    
  def sweep_pts_warning(self, swp_pts):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText('Sweep points not set correctly.')
    msg.setInformativeText('Continue scan with {0} sweep points?'.format(swp_pts))
    msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    msg.buttonClicked.connect(self.start_progress)
    msg.exec_()

  def save_trace(self):
  # Spectrum analyzer will save a csv file and then transfer that file to the PC
    self.parent.connect_to_sa()
    sa_file = self.parent.scan_name_edit.text()
    sa_filepath = sa_file + '.csv'
    filepath = self.parent.workspace / sa_filepath

    if 'Rohde' in self.parent.instr:  # SCPI commands valid only for R&S
      self.parent.sa.write('MMEM:STOR:TRAC 1, "C:\\Temp\\{0}.csv"'.format(sa_file))
      self.parent.sa.write('MMEM:DATA? "C:\\Temp\\{0}.csv"'.format(sa_file))
      trace_data = self.parent.sa.read_raw()
      # Write file to pc
      with open(filepath, 'wb') as f: #, newline='') as f:
        f.write(trace_data)
    elif 'Agilent' in self.parent.instr:
      self.parent.sa.write(':MMEM:STOR:TRAC:DATA TRACE1, "C:\\Temp\\{0}.csv"'
                    .format(sa_file))
      trace_data = self.parent.sa.query('MMEM:DATA? "C:\\Temp\\{0}.csv"'
                                  .format(sa_file))
      trace_data = trace_data.replace('\r', ',')
      with open(filepath, 'w', newline='') as f:
        f.write(trace_data)
    
    # Delete file from analyzer memory
    self.parent.sa.write('MMEM:DEL "C:\\Temp\\{0}.csv"'.format(sa_file))
    
    # Load and plot new trace
    self.parent.load_file(filepath, sa_file)
    self.parent.plot_trace(sa_file)

    # Update user on success
    self.saved = True
    self.parent.statusBar().showMessage('File Saved')

    self.hide()

  def start_progress(self):
    if self.timer.isActive():
      self.timer.stop()
      self.progress.reset()
    else:
      self.timer.start(100, self)

  def timerEvent(self, event):
    # Function updates the status bar and the progress bar with remaining time.
    if self.completed >= self.time and not self.saved:
      self.timer.stop()
      self.save_trace()
      return
    remaining = self.time - self.completed
    remaining = round(remaining, 2)
    self.parent.statusBar().showMessage('{0}s Remaining'.format(remaining))
    self.completed += 0.1
    self.progress.setValue(self.completed)

  def cancel(self):
    self.timer.stop()
    self.parent.statusBar().showMessage('Scan Canceled')
    self.hide()

class scanProfilePopup(QWidget):
  def __init__(self, parent):
    super().__init__()
    self.parent = parent
    self.initUI()

  def initUI(self):
    # Labels
    sp_label = QLabel('Scan Profile Name:')
    sp_label.setAlignment(QtCore.Qt.AlignRight)
    start_freq_label = QLabel('Start Frequency (Hz)')
    start_freq_label.setAlignment(QtCore.Qt.AlignRight)
    stop_freq_label = QLabel('Stop Frequency (Hz)')
    stop_freq_label.setAlignment(QtCore.Qt.AlignRight)
    rbw_label = QLabel('Resolution Bandwidth (Hz)')
    rbw_label.setAlignment(QtCore.Qt.AlignRight)
    vbw_label = QLabel('Video Bandwidth (Hz)')
    vbw_label.setAlignment(QtCore.Qt.AlignRight)
    atten_label = QLabel('Internal Attenuation (dB)')
    atten_label.setAlignment(QtCore.Qt.AlignRight)
    preamp_label = QLabel('Internal Preamp (On/Off)')
    preamp_label.setAlignment(QtCore.Qt.AlignRight)
    sweep_pts_label = QLabel('Sweep Points (#)')
    sweep_pts_label.setAlignment(QtCore.Qt.AlignRight)
    ref_label = QLabel('Reference Level (dBm)')
    ref_label.setAlignment(QtCore.Qt.AlignRight)

    # Entries
    self.sp_entry = QLineEdit()
    self.start_f_entry = QLineEdit()
    self.stop_f_entry = QLineEdit()
    self.rbw_entry = QLineEdit()
    self.vbw_entry = QLineEdit()
    self.atten_entry = QLineEdit()
    self.preamp_entry = QLineEdit()
    self.sweep_pts_entry = QLineEdit()
    self.ref_entry = QLineEdit()

    # Buttons
    create_btn = QPushButton('Create Profile')
    create_btn.setMaximumWidth(120)
    create_btn.clicked.connect(self.create_sp)
    cancel_btn = QPushButton('Cancel')
    cancel_btn.clicked.connect(self.close)

    # Layout (row, column, rowspan, columnspan)
    grid = QGridLayout()
    self.setLayout(grid)
    grid.addWidget(sp_label, 0, 0, 1, 1)
    grid.addWidget(self.sp_entry, 0, 1, 1, 2)
    grid.addWidget(start_freq_label, 1, 0, 1, 1)
    grid.addWidget(self.start_f_entry, 1, 1, 1, 2)
    grid.addWidget(stop_freq_label, 2, 0, 1, 1)
    grid.addWidget(self.stop_f_entry, 2, 1, 1, 2)
    grid.addWidget(rbw_label, 3, 0, 1, 1)
    grid.addWidget(self.rbw_entry, 3, 1, 1, 2)
    grid.addWidget(vbw_label, 4, 0, 1, 1)
    grid.addWidget(self.vbw_entry, 4, 1, 1, 2)
    grid.addWidget(atten_label, 5, 0, 1, 1)
    grid.addWidget(self.atten_entry, 5, 1, 1, 2)
    grid.addWidget(preamp_label, 6, 0, 1, 1)
    grid.addWidget(self.preamp_entry, 6, 1, 1, 2)
    grid.addWidget(sweep_pts_label, 7, 0, 1, 1)
    grid.addWidget(self.sweep_pts_entry, 7, 1, 1, 2)
    grid.addWidget(ref_label, 8, 0, 1, 1)
    grid.addWidget(self.ref_entry, 8, 1, 1, 2)
    grid.addWidget(create_btn, 9, 0, 1, 1)
    grid.addWidget(cancel_btn, 9, 2, 1, 1)

  def create_sp(self):
    filename = self.sp_entry.text()
    parameters = ['*RST', 'DISP:TRAC1:MODE MAXH', 'DISP:TRAC2 ON', 'DISP:TRAC2:MODE WRIT']
    if filename:
      if self.start_f_entry.text():
        parameters.append('FREQ:STAR '+self.start_f_entry.text()+'Hz')
      if self.stop_f_entry.text():
        parameters.append('FREQ:STOP '+self.stop_f_entry.text()+'Hz')
      if self.rbw_entry.text():
        parameters.append('BAND '+self.rbw_entry.text()+'Hz')
      if self.vbw_entry.text():
        parameters.append('BAND:VID '+self.vbw_entry.text()+'Hz')
      if self.atten_entry.text():
        parameters.append('INP:ATT '+self.atten_entry.text()+'dB')
      if self.preamp_entry.text():
        on_off = self.preamp_entry.text()
        on_off = on_off.upper()
        parameters.append('INP:GAIN:STAT '+on_off)
      if self.sweep_pts_entry.text():
        parameters.append('SWE:POIN '+self.sweep_pts_entry.text())
      if self.ref_entry.text():
        parameters.append('DISP:TRAC:Y:RLEV '+self.ref_entry.text())
      filename = filename + '.csv'
      with open(FP_SP / filename, 'w') as sp_file:
        sp_writer = csv.writer(sp_file, delimiter=',')
        for param in parameters:
          sp_writer.writerow([param])
    self.parent.update_scan_combo()
    self.hide()

  def close(self):
    self.hide()

class connectionPopup(QWidget):
  def __init__(self, parent):
    super().__init__()
    self.parent = parent
    self.initUI()

  def initUI(self):
    # Entry
    self.tcpip_entry = QLineEdit()
    self.tcpip_entry.setFixedWidth(150)
    self.tcpip_entry.setText(self.parent.resource_ip)
    self.gpib_entry = QLineEdit()
    self.gpib_entry.setFixedWidth(150)
    self.gpib_entry.setText(self.parent.resource_gpib)

    # Radiobuttons
    self.tcpip_radio = QRadioButton('TCP/IP')
    self.tcpip_radio.setChecked(True)
    self.gpib_radio = QRadioButton('GPIB')

    # Buttons
    okay_btn = QPushButton('Connect')
    okay_btn.clicked.connect(self.test_connection)
    cancel_btn = QPushButton('Close')
    cancel_btn.clicked.connect(self.close)

    # Layout (row, column, rowspan, columnspan)
    grid = QGridLayout()
    self.setLayout(grid)
    grid.addWidget(self.tcpip_radio, 0, 0, 1, 1)
    grid.addWidget(self.tcpip_entry, 0, 1, 1, 2)
    grid.addWidget(self.gpib_radio, 1, 0, 1, 1)
    grid.addWidget(self.gpib_entry, 1, 1, 1, 2)
    grid.addWidget(okay_btn, 2, 0, 1, 1)
    grid.addWidget(cancel_btn, 2, 2, 1, 1)

  def test_connection(self):
    # Set resource string
    if self.tcpip_radio.isChecked():
      self.parent.resource_var = 'TCPIP::' + self.tcpip_entry.text() + '::INSTR'
    elif self.gpib_radio.isChecked():
      self.parent.resource_var = 'GPIB::' + self.gpib_entry.text() + '::INSTR'

    # Connect to resource and update user on status of connection
    if self.parent.connect_to_sa():
      self.parent.statusBar().showMessage('Connected to ' + self.parent.instr)

  def close(self):
    self.hide()

class findMaxPopup(QWidget):
  def __init__(self, parent, active_tab):
    super().__init__()
    self.parent = parent
    self.active_tab = active_tab
    self.initUI()

  def initUI(self):
    max_label = QLabel('Filename:')
    self.max_entry = QLineEdit()
    save_btn = QPushButton('Save')
    save_btn.setMaximumWidth(100)
    save_btn.clicked.connect(self.save_max)
    cancel_btn = QPushButton('Cancel')
    cancel_btn.clicked.connect(self.close)

    # Layout (row, column, rowspan, columnspan)
    grid = QGridLayout()
    self.setLayout(grid)
    grid.addWidget(max_label, 0, 0, 1, 1)
    grid.addWidget(self.max_entry, 0, 1, 1, 2)
    grid.addWidget(save_btn, 1, 0, 1, 1)
    grid.addWidget(cancel_btn, 1, 2, 1, 1)    

  def calc_max(self, frames):
    max_df = pd.DataFrame(columns=['Frequency (MHz)'])
    df = []

    for i in frames:
      if 'Position' in self.parent.data[i].columns.tolist():    
        df = self.parent.data[i].iloc[:, [0,1]]
      else:
        df = self.parent.data[i].drop('Mask', axis=1)
        df = df.iloc[:, [0,-1]]

      max_df = pd.merge(max_df, df, on='Frequency (MHz)', how='outer')

    cols = max_df.columns.tolist()
    cols = cols[-1].split('(')
    cols = cols[-1].split(')')
    units = cols[0]
    max_units = 'Max ('+units+')'
    max_df[max_units] = max_df.iloc[:, 1:].max(axis=1)

    return max_df[['Frequency (MHz)', max_units]]

  def save_max(self):
    filename = self.max_entry.text()+'.csv'
    if self.active_tab == 0:
      plots = self.parent.main_plot.get_legend_handles_labels()
      maximum = self.calc_max(plots[1])
      maximum.to_csv(path_or_buf=self.parent.workspace / filename,
                      sep=',', na_rep='NaN', index=False)
      self.parent.main_plot.plot(maximum['Frequency (MHz)'],
                                  maximum.iloc[:,-1], label=self.max_entry.text())
    elif self.active_tab == 1:
      plots = self.parent.vert_plot.get_legend_handles_labels()
      maximum = self.calc_max(plots[1])
      maximum.to_csv(path_or_buf=self.parent.workspace / filename,
                      sep=',', na_rep='NaN', index=False)
      self.parent.vert_plot.plot(maximum['Frequency (MHz)'], maximum.iloc[:,-1], label=self.max_entry.text())
    elif self.active_tab == 2:
      plots = self.parent.horiz_plot.get_legend_handles_labels()
      maximum = self.calc_max(plots[1])
      maximum.to_csv(path_or_buf=self.parent.workspace / filename,
                      sep=',', na_rep='NaN', index=False)
      self.parent.horiz_plot.plot(maximum['Frequency (MHz)'], maximum.iloc[:,-1], label=self.max_entry.text())

    self.parent.redraw_legend([0, 1, 2])
    self.parent.redraw_plots()
    self.hide()

  def close(self):
    self.hide()

class frequencyMaskPopup(QWidget):
  def __init__(self, parent):
    super().__init__()
    self.parent = parent
    self.initUI()

    if self.parent.mask != 'None':
      self.maskCombo.setCurrentText(self.parent.mask)

  def initUI(self):
    # UI Labels
    saveLabel = QLabel('Save Mask As')
    loadLabel = QLabel('Load Mask')

    # Lineedit for user to give filename
    self.saveEdit = QLineEdit()

    # Setup ComboBox
    self.maskCombo = QComboBox(self)
    mask_list = ['None']
    mask_list.extend(self.parent.format_filepath(
        FP_MASK.glob('*.csv')))
    self.maskCombo.addItems(mask_list)
    self.maskCombo.currentIndexChanged.connect(self.load_mask)

    # Initialize table with 1 row, 2 columns
    self.table = QTableWidget(1, 2, self)
    self.table.setHorizontalHeaderLabels(['Center Frequency (MHz)', 'Span (MHz)'])
    self.table.setColumnWidth(0, 170)
    self.table.setColumnWidth(1, 170)
    self.table.cellChanged.connect(self.table_changed)

    # Buttons
    saveBtn = QPushButton('Save')
    saveBtn.setMaximumWidth(100)
    saveBtn.clicked.connect(self.save_mask)
    cancelBtn = QPushButton('Cancel')
    cancelBtn.setMaximumWidth(100)
    cancelBtn.clicked.connect(self.hide)

    # Layout (row, column, rowspan, columnspan)
    grid = QGridLayout()
    self.setLayout(grid)
    grid.addWidget(saveLabel, 0, 0, 1, 1)
    grid.addWidget(self.saveEdit, 0, 1, 1, 2)
    grid.addWidget(loadLabel, 1, 0, 1, 1)
    grid.addWidget(self.maskCombo, 1, 1, 1, 2)
    grid.addWidget(self.table, 2, 0, 1, 3)
    grid.addWidget(saveBtn, 3, 0, 1, 1)
    grid.addWidget(cancelBtn, 3, 2, 1, 1)

  def table_changed(self, row, column):
    # Called everytime a cell is updated to continue to add rows
    row = row + 1
    if row == self.table.rowCount():
      self.table.insertRow(row)

  def load_mask(self):
    # Clear/load mask files
    if self.maskCombo.currentText() == 'None':
      self.table.clear()
      self.table.setColumnCount(2)
      self.table.setRowCount(1)
      self.table.setHorizontalHeaderLabels(['Center Frequency (MHz)', 'Span (MHz)'])
    else:
      filename = self.maskCombo.currentText()+'.csv'
      df = pd.read_csv(FP_MASK / filename)
      for i in range(len(df.index)):
        for j in range(len(df.columns)):
          self.table.setItem(i, j, QTableWidgetItem(str(df.iloc[i, j])))

  def generate_mask(self, df):
    # Generate a boolean frequency list that can be merged with any dataframe
    frequencies = pd.Series()
    tmp_df = pd.DataFrame()

    for i in range(len(df.index)):
      if df.iloc[i, 0]:
        center_f = float(df.iloc[i, 0])
        lower_f = center_f - (float(df.iloc[i, 1]) / 2)
        upper_f = center_f + (float(df.iloc[i, 1]) / 2)
        f_list = pd.Series(np.linspace(lower_f, upper_f, (upper_f - lower_f)))
        frequencies = frequencies.append(f_list)
    
    tmp_df['Frequency (MHz)'] = frequencies.values
    tmp_df['Mask'] = True

    return tmp_df
      
  def save_mask(self):
    df_table = self.parent.df_from_table(self.table)

    # Remove empty values
    df_table.replace('', np.nan, inplace=True)
    df_table = df_table.dropna(axis=0, how='any')
    
    # Sort table
    cols = df_table.columns.tolist()
    df_table = df_table.sort_values(by=cols[0])
    
    # Save masks for easy reuse
    if self.saveEdit.text():
      filename = self.saveEdit.text()+'.csv'
      df_table.to_csv(path_or_buf=FP_MASK / filename, 
                sep=',', index=False)
      self.parent.mask = self.saveEdit.text()
    elif self.maskCombo.currentText() != 'None':
      filename = self.maskCombo.currentText()+'.csv'
      df_table.to_csv(path_or_buf=FP_MASK / filename, 
                sep=',', index=False)
      self.parent.mask = self.maskCombo.currentText()
    elif not df_table.empty:
      now = datetime.datetime.now()
      now = now.strftime('%Y-%m-%d %H_%M_%S')
      filename = now+'.csv'
      df_table.to_csv(path_or_buf=FP_MASK / now, 
                sep=',', index=False)
      self.parent.mask = now
    elif self.maskCombo.currentText() and df_table.empty == 'None':
      self.parent.mask = 'None'

    # Convert to Hz for merge_asof
    df = self.generate_mask(df_table)
    df['Hz'] = df['Frequency (MHz)'] * 1000000
    df = df.drop(['Frequency (MHz)'], axis=1)
    df = df.reindex(columns=['Hz', 'Mask'])
    self.parent.frequency_mask_df = df
    self.hide()

class deltaPopup(QWidget):
  def __init__(self, parent):
    super().__init__()
    self.parent = parent
    self.initUI()
    self.initCombos()

  def initUI(self):
    self.x_combo = QComboBox()
    self.y_combo = QComboBox()

    self.name = QLineEdit()

    name_label = QLabel('Filename')

    minus_label = QLabel('-')
    minus_label.setAlignment(QtCore.Qt.AlignCenter)

    # Buttons
    okayBtn = QPushButton('Okay')
    okayBtn.setMaximumWidth(100)
    okayBtn.clicked.connect(self.plot_delta)
    cancelBtn = QPushButton('Cancel')
    cancelBtn.setMaximumWidth(100)
    cancelBtn.clicked.connect(self.hide)

    # Layout (row, column, rowspan, columnspan)
    grid = QGridLayout()
    self.setLayout(grid)
    grid.addWidget(name_label, 0, 0, 1, 1)
    grid.addWidget(self.name, 0, 1, 1, 2)
    grid.addWidget(self.x_combo, 1, 0, 1, 1)
    grid.addWidget(minus_label, 1, 1, 1, 1)
    grid.addWidget(self.y_combo, 1, 2, 1, 1)
    grid.addWidget(okayBtn, 2, 0, 1, 1)
    grid.addWidget(cancelBtn, 2, 2, 1, 1)

  def initCombos(self):
    traces = self.parent.data.keys()
    self.x_combo.addItems(traces)
    self.y_combo.addItems(traces)

  def plot_delta(self):
    df1 = self.parent.data[self.x_combo.currentText()]
    df2 = self.parent.data[self.y_combo.currentText()]
    
    df1 = df1.drop(columns='Mask')
    df2 = df2.drop(columns='Mask')

    df1['Int'] = df1.iloc[:, 0].astype(int)
    df2['Int'] = df2.iloc[:, 0].astype(int)

    df1 = df1.set_index('Int')
    df2 = df2.set_index('Int')

    df1 = pd.merge_asof(df1, df2.iloc[:,1:], left_index=True, right_index=True, direction='nearest', tolerance=1)
    df1['Delta'] = df1.iloc[:, 1] - df1.iloc[:, 2]

    if self.name.text():
      delta_label = self.name.text()
      filename = delta_label + '.csv'
      df1[['Frequency (MHz)', 'Delta']].to_csv(self.parent.workspace / filename)
    else:
      delta_label = self.x_combo.currentText() + ' - ' + self.y_combo.currentText()

    self.parent.main_plot.plot(df1.iloc[:, 0], df1['Delta'], label=delta_label)

    self.parent.redraw_legend([0])
    self.parent.redraw_plots()
    self.hide()

class sePopup(QWidget):
  def __init__(self, parent):
    super().__init__()
    self.parent = parent
    self.initUI()
    self.initCombos()

  def initUI(self):
    self.x_combo = QComboBox()
    self.y_combo = QComboBox()

    self.name = QLineEdit()

    name_label = QLabel('Filename')

    minus_label = QLabel('-')
    minus_label.setAlignment(QtCore.Qt.AlignCenter)

    # Buttons
    okayBtn = QPushButton('Okay')
    okayBtn.setMaximumWidth(100)
    okayBtn.clicked.connect(self.calculate_se)
    cancelBtn = QPushButton('Cancel')
    cancelBtn.setMaximumWidth(100)
    cancelBtn.clicked.connect(self.hide)

    # Layout (row, column, rowspan, columnspan)
    grid = QGridLayout()
    self.setLayout(grid)
    grid.addWidget(name_label, 0, 0, 1, 1)
    grid.addWidget(self.name, 0, 1, 1, 2)
    grid.addWidget(self.x_combo, 1, 0, 1, 1)
    grid.addWidget(minus_label, 1, 1, 1, 1)
    grid.addWidget(self.y_combo, 1, 2, 1, 1)
    grid.addWidget(okayBtn, 2, 0, 1, 1)
    grid.addWidget(cancelBtn, 2, 2, 1, 1)

  def initCombos(self):
    traces = self.parent.data.keys()
    self.x_combo.addItems(traces)
    self.y_combo.addItems(traces)

  def calculate_se(self):
    x = self.x_combo.currentText()
    y = self.y_combo.currentText()
    df1 = self.parent.data[x]
    df2 = self.parent.data[y]
    
    df1 = df1.drop(columns='Mask')
    df2 = df2.drop(columns='Mask')

    df1['Int'] = df1.iloc[:, 0].astype(int)
    df2['Int'] = df2.iloc[:, 0].astype(int)

    df1 = df1.set_index('Int')
    df2 = df2.set_index('Int')

    df1 = pd.merge_asof(df1, df2.iloc[:,1:], left_index=True, right_index=True, 
                        suffixes=(x, y), direction='nearest', tolerance=1)

    df1['Delta'] = df1.iloc[:, 1] - df1.iloc[:, 2]
    df1['Attenuation (dB)'] = savgol_filter(df1['Delta'], 1001, 3)

    if self.name.text():
      delta_label = self.name.text()
      filename = delta_label + '.csv'
      df1[['Frequency (MHz)', 'Attenuation (dB)']].to_csv(self.parent.workspace / filename, index=False)
    else:
      delta_label = self.x_combo.currentText() + ' - ' + self.y_combo.currentText()

    self.parent.main_plot.plot(df1.iloc[:, 0], df1['Delta'])
    self.parent.main_plot.plot(df1.iloc[:, 0], df1['Attenuation (dB)'], label=delta_label)
    
    self.parent.redraw_legend([0])
    self.parent.redraw_plots()
    self.hide()

class EasyEmi(QMainWindow):

  def __init__(self):
    super().__init__()

    # Center window
    self.center()

    # Initialize Global Variables
    self.data = {}
    self.cfdata = []
    self.tracekey = []
    self.num_of_peaks = 6
    self.timer = 15
    self.resource_ip = '192.168.1.2'
    self.resource_gpib = '20'
    self.resource_var = 'TCPIP::192.168.1.2::INSTR'
    self.workspace = FP_CSV
    self.mask = 'None'
    self.frequency_mask_df = pd.DataFrame(columns=['Hz', 'Mask'])
    self.clip = QApplication.clipboard()
    self.shielding_effectiveness = False

    # Spectrum analyzer resource manager
    self.rm = visa.ResourceManager('@py')
    self.rm.timeout = 1000

    # Matplotlib figures/subplots
    self.main_fig = Figure()
    self.main_plot = self.main_fig.add_subplot(111)
    self.main_plot.grid()
    self.vert_fig = Figure()
    self.vert_plot = self.vert_fig.add_subplot(111)
    self.vert_plot.grid()
    self.horiz_fig = Figure()
    self.horiz_plot = self.horiz_fig.add_subplot(111)
    self.horiz_plot.grid()

    # Initialize Menubar
    self.initMenu()

    # Initialize Toolbar
    self.initToolbar()

    # Initialize UI
    self.initUI()

    # Status Bar
    self.statusBar().showMessage('Version 2.3')

    # Load scan profiles
    self.update_scan_combo()

    self.show()

  def initUI(self):
    self.setWindowTitle('EasyEMI v2')
    self.setGeometry(10, 10, 1400, 740)

    # Labels
    scan_name_label = QLabel('Scan name')
    scan_name_label.setMaximumWidth(75)
    select_scan_label = QLabel('Select scan')
    select_scan_label.setMaximumWidth(75)
    trace_files_label = QLabel('Trace Files')
    trace_files_label.setMaximumWidth(75)

    # Entry Forms
    self.scan_name_edit = QLineEdit()

    # Buttons
    scan_button = QPushButton('Scan')
    scan_button.setMaximumWidth(100)
    scan_button.clicked.connect(self.show_scan_popup)

    # Combobox
    self.scan_combo = QComboBox()
    self.scan_combo.addItem('Custom')

    # Check Box
    self.cf_checkbox = QCheckBox('Correction Factors')
    self.cf_checkbox.setChecked(False)
    self.cf_checkbox.stateChanged.connect(self.show_cf_popup)

    # File system model
    self.file_model = FileSystemModel(self)
    self.file_model.setRootPath(str(Path.home()))
    self.file_model.setReadOnly(False)

    # Treeview
    self.treeview = QTreeView()
    self.treeview.setEditTriggers(QAbstractItemView.EditKeyPressed)
    self.treeview.setSelectionMode(QAbstractItemView.ExtendedSelection)
    self.treeview.setDragDropMode(QAbstractItemView.InternalMove)
    self.treeview.setModel(self.file_model)
    self.treeview.setRootIndex(self.file_model.index(str(Path.home())))
    self.treeview.setColumnWidth(0, 325)
    self.treeview.setDragEnabled(True)
    self.treeview.doubleClicked.connect(self.dbl_clk_tree)
    self.treeview.setContextMenuPolicy(3)
    self.treeview.customContextMenuRequested.connect(self.openContextMenu)

    # Rename Shortcut
    r = QShortcut(QKeySequence('CTRL+r'), self)
    r.activated.connect(self.editActivated)

    # Copy Shortcut
    c = QShortcut(QKeySequence('CTRL+c'), self)
    c.activated.connect(self.copyActivated)

    # Tabs
    self.tabs = QTabWidget()
    maintab = QWidget()
    vtab = QWidget()
    htab = QWidget()
    self.tabs.addTab(maintab, 'Main Plot')
    self.tabs.addTab(vtab, 'Vertical')
    self.tabs.addTab(htab, 'Horizontal')
    mainlayout = QVBoxLayout()
    vertlayout = QVBoxLayout()
    horizlayout = QVBoxLayout()

    # Matplotlib Graph
    self.main_canvas = FigureCanvas(self.main_fig)
    main_toolbar = NavigationToolbar(self.main_canvas, self)
    mainlayout.addWidget(self.main_canvas)
    mainlayout.addWidget(main_toolbar)
    maintab.setLayout(mainlayout)

    self.vert_canvas = FigureCanvas(self.vert_fig)
    vert_toolbar = NavigationToolbar(self.vert_canvas, self)
    vertlayout.addWidget(self.vert_canvas)
    vertlayout.addWidget(vert_toolbar)
    vtab.setLayout(vertlayout)

    self.horiz_canvas = FigureCanvas(self.horiz_fig)
    horiz_toolbar = NavigationToolbar(self.horiz_canvas, self)
    horizlayout.addWidget(self.horiz_canvas)
    horizlayout.addWidget(horiz_toolbar)
    htab.setLayout(horizlayout)

    self.redraw_plots()

    # Table view for peak list and notes
    self.peak_table = QTableWidget()
    self.peak_table.setMinimumHeight(45)
    self.peak_table.horizontalHeader().sectionClicked.connect(self.sort_table)
    self.peak_table.horizontalHeader().setSortIndicatorShown(True)

    # Configure central widget
    central = QWidget(self)
    self.setCentralWidget(central)
    grid = QGridLayout()
    central.setLayout(grid)
    grid.setSpacing(5)

    # splitter widget
    split_vert = QSplitter()
    split_vert.setOrientation(QtCore.Qt.Vertical)
    split_vert.addWidget(self.tabs)
    split_vert.addWidget(self.peak_table)
    split_vert.setSizes([1000, 120])

    split_horiz = QSplitter()
    split_horiz.setOrientation(QtCore.Qt.Horizontal)
    topwidget = QWidget()
    split_horiz.addWidget(topwidget)
    split_horiz.addWidget(split_vert)
    split_horiz.setSizes([120, 1000])

    # Place widgets (row, column, rowspan, columnspan)
    left_layout = QGridLayout()
    left_layout.addWidget(scan_name_label, 0, 0, 1, 0)
    left_layout.addWidget(self.scan_name_edit, 0, 1, 1, 2)
    left_layout.addWidget(select_scan_label, 1, 0, 1, 1)
    left_layout.addWidget(self.scan_combo, 1, 1, 1, 1)
    left_layout.addWidget(scan_button, 1, 2, 1, 1)
    left_layout.addWidget(self.cf_checkbox, 2, 1, 1, 2)
    left_layout.setAlignment(self.cf_checkbox, QtCore.Qt.AlignRight)
    left_layout.addWidget(trace_files_label, 2, 0, 1, 1)
    left_layout.addWidget(self.treeview, 3, 0, 1, 3)
      
    topwidget.setLayout(left_layout)
    grid.addWidget(split_horiz)

    # Double click zoom out workaround
    self.main_fig.canvas.mpl_connect('button_press_event', self.handle_button_event)
    self.vert_fig.canvas.mpl_connect('button_press_event', self.handle_button_event)
    self.horiz_fig.canvas.mpl_connect('button_press_event', self.handle_button_event)

  def initMenu(self):
    # Menu Bar
    menubar = self.menuBar()
    menubar.setNativeMenuBar(False)

    # File Menu
    fileMenu = menubar.addMenu('&File')

    # File Menu -> Settings
    settingAct = QAction('Settings', self)
    settingAct.setStatusTip('Timer and peak settings')
    settingAct.triggered.connect(self.show_settings_popup)
    fileMenu.addAction(settingAct)

    # File Menu -> Export Peak Data
    exportPact = QAction('Export Peaks', self)
    exportPact.setStatusTip('Export the peak table to csv')
    exportPact.triggered.connect(self.export_peak_table)
    fileMenu.addAction(exportPact)

    # File Menu  -> Exit
    exitAct = QAction('&Exit', self)        
    exitAct.setStatusTip('Exit application')
    exitAct.triggered.connect(qApp.quit)
    fileMenu.addAction(exitAct)

    # Limits Menu
    limitMenu = menubar.addMenu('&Limits')

    # Limits Menu -> CISPR/FCC
    cisprMenu = QMenu('CISPR', self)
    limitMenu.addMenu(cisprMenu)
    fccMenu = QMenu('FCC', self)
    limitMenu.addMenu(fccMenu)

    # Limits Menu -> CISPR -> Class A/B
    classAAct = QAction('Class A', self)
    cisprMenu.addAction(classAAct)
    classAAct.triggered.connect(lambda: self.cispr_limits('A'))
    classBAct = QAction('Class B', self)
    cisprMenu.addAction(classBAct)
    classBAct.triggered.connect(lambda: self.cispr_limits('B'))

    # Limits Menu -> FCC -> Class A/B
    fccAAct = QAction('Class A', self)
    fccMenu.addAction(fccAAct)
    fccAAct.triggered.connect(lambda: self.fcc_limits('A'))
    fccBAct = QAction('Class B', self)
    fccMenu.addAction(fccBAct)
    fccBAct.triggered.connect(lambda: self.fcc_limits('B'))

    # Instrument Menu
    instrMenu = menubar.addMenu('&Instrument')

    # Instrument Menu -> Connection
    connectAct = QAction('Connection', self)
    connectAct.setStatusTip('Debug connection issues')
    connectAct.triggered.connect(self.show_connection_popup)
    instrMenu.addAction(connectAct)

    # Instrument Menu -> Scan Profiles
    spAct = QAction('Scan Profiles', self)
    instrMenu.addAction(spAct)
    spAct.triggered.connect(self.show_sp_popup)

    # Help Menu
    helpMenu = menubar.addMenu('&Help')

    # Help Menu -> About
    aboutAct = QAction('About', self)
    helpMenu.addAction(aboutAct)

  def initToolbar(self):
    toolbar = QToolBar('self')
    self.addToolBar(QtCore.Qt.RightToolBarArea, toolbar)

    clearAct = QAction('Clear', self)
    clearAct.setStatusTip('Clear all')
    clearAct.triggered.connect(self.clear_plots)
    toolbar.addAction(clearAct)

    maxAct = QAction('Max', self)
    maxAct.setStatusTip('Calculate/save maximum of all plots')
    toolbar.addAction(maxAct)
    maxAct.triggered.connect(self.show_find_max_popup)

    wifiAct = QAction('WiFi', self)
    wifiAct.setStatusTip('Set X-axis to 5-6GHz, to return to full view double click the graph')
    toolbar.addAction(wifiAct)
    wifiAct.triggered.connect(self.wifi_five)

    fmaskAct = QAction('Mask', self)
    fmaskAct.setStatusTip('Mask frequencies to hide them from the graph')
    toolbar.addAction(fmaskAct)
    fmaskAct.triggered.connect(self.show_fmask_popup)

    deltaAct = QAction('Delta', self)
    deltaAct.setStatusTip('Select two traces and show (x - y)')
    toolbar.addAction(deltaAct)
    deltaAct.triggered.connect(self.show_delta_popup)

    seAct = QAction('SE', self)
    seAct.setStatusTip('Shielding Effectiveness')
    toolbar.addAction(seAct)
    seAct.triggered.connect(self.show_se_popup)

  def df_from_table(self, table):
    cols = []
    for h in range(table.columnCount()):
      cols.append(table.horizontalHeaderItem(h).text())

    tmp_df = pd.DataFrame(columns=cols, index=range(table.rowCount()-1))

    for i in range(table.rowCount()-1):
      for j in range(table.columnCount()):
        if table.item(i, j):
          tmp_df.iloc[i, j] = table.item(i, j).data(0)

    return tmp_df

  def sort_table(self, header):
    order = self.peak_table.horizontalHeader().sortIndicatorOrder()
    if order == 0:
      self.peak_table.sortItems(header, 0)
      self.peak_table.horizontalHeader().setSortIndicator(header, 0)
    elif order == 1:
      self.peak_table.sortItems(header, 1)
      self.peak_table.horizontalHeader().setSortIndicator(header, 1)
    else:
      pass

  def copyActivated(self):
    selected = self.peak_table.selectedRanges()
    s = ""
    for r in range(selected[0].topRow(), selected[0].bottomRow()+1):
      for c in range(selected[0].leftColumn(), selected[0].rightColumn()+1):
        try:
          s += str(self.peak_table.item(r,c).text()) + "\t"
        except AttributeError:
          s += "\t"
      s = s[:-1] + "\n" #eliminate last '\t'
    self.clip.setText(s)

  @pyqtSlot()
  def editActivated(self):
    self.treeview.edit(self.treeview.currentIndex())

  @pyqtSlot()
  def setWorkspace(self, item):
    folder_fp = Path(self.file_model.filePath(item))
    self.workspace = folder_fp
    self.statusBar().showMessage('Traces will be saved to {0}'.format(folder_fp))

  @pyqtSlot()
  def deleteMsg(self, item, filetype):
    item = item
    filetype = filetype
    
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText('Confirm delete')
    msg.setInformativeText('This action cannot be undone')
    msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    msg.buttonClicked.connect(lambda: self.deleteFile(item, filetype))

    msg.exec_()

  @pyqtSlot()
  def deleteFile(self, item, filetype):
    if filetype == 'Folder':
      self.file_model.rmdir(item)
    else:
      self.file_model.remove(item)

  @pyqtSlot()
  def createFolder(self, item):
    if item == None:
      item = self.file_model.index(FP_CSV)
      folder = self.file_model.mkdir(item, 'New Folder')
    else:
      folder = self.file_model.mkdir(item.parent(), 'New Folder')
    self.treeview.edit(folder)

  def openContextMenu(self, position):
    item = None
    try:
      item = self.treeview.selectedIndexes()[0]
    except IndexError:
      pass
    finally:
      menu = QMenu()
      createAct = QAction('Create Folder', self)
      menu.addAction(createAct)
      createAct.triggered.connect(lambda: self.createFolder(item))
      renameAct = QAction('Rename', self)
      menu.addAction(renameAct)
      renameAct.triggered.connect(self.editActivated)

    if item:
      filetype = self.file_model.type(item)
      deleteAct = QAction('Delete', self)
      menu.addAction(deleteAct)
      deleteAct.triggered.connect(lambda: self.deleteMsg(item, filetype))

    # Check file type for correct 
      if filetype == 'Folder':
        workAct = QAction('Set Workspace', self)
        menu.addAction(workAct)
        workAct.triggered.connect(lambda: self.setWorkspace(item))

    menu.exec_(self.treeview.viewport().mapToGlobal(position))

  def update_scan_combo(self):
    # Get current list of items in combo and in /Scan Profile/
    combo_list = [self.scan_combo.itemText(i) for i in range(self.scan_combo.count())]
    scan_list = self.format_filepath(FP_SP.glob('*csv'))

    # Add items not found in combo list
    for scan in scan_list:
      if scan not in combo_list:
        self.scan_combo.addItem(scan)

  def center(self):
    qr = self.frameGeometry()
    cp = QDesktopWidget().availableGeometry().center()
    qr.moveCenter(cp)
    self.move(qr.topLeft())

  def connect_to_sa(self):
    # Method to attempt connection with spectrum analyzer.
    # Returns True/False on success/failure
    try:
      self.sa = self.rm.open_resource(self.resource_var)
      self.instr = self.sa.query('*IDN?')
      if 'Agilent' in self.instr:
        self.sa.write('DISP:ENAB ON')
      elif 'Rhode' in self.instr:
        self.sa.write('SYST:DISP:UPD')
      return True
    except (visa.VisaIOError, OSError):
      self.statusBar().showMessage('Connection Failed')
      return False

  @pyqtSlot()
  def show_fmask_popup(self):
    self.fmask_popup = frequencyMaskPopup(self)
    self.fmask_popup.setGeometry(400, 100, 400, 350)
    self.fmask_popup.show()

  @pyqtSlot()
  def show_delta_popup(self):
    self.delta_popup = deltaPopup(self)
    self.delta_popup.setGeometry(400, 100, 250, 150)
    self.delta_popup.show()

  @pyqtSlot()
  def show_se_popup(self):
    self.se_popup = sePopup(self)
    self.se_popup.setGeometry(400, 100, 250, 150)
    self.se_popup.show()
        
  @pyqtSlot()
  def show_cf_popup(self):
    if self.cf_checkbox.isChecked():
      self.cf = correctionFactorPopup(self)
      self.cf.setGeometry(400, 100, 400, 350)
      self.cf.show()
    else:
      pass      

  @pyqtSlot()
  def show_settings_popup(self):
    self.settings = settingsPopup(self)
    self.settings.setGeometry(400, 100, 100, 100)
    self.settings.show()

  @pyqtSlot()
  def show_scan_popup(self):
    self.scan = scanPopup(self)
    self.scan.setGeometry(400, 100, 100, 100)
    self.scan.show()

  @pyqtSlot()
  def show_sp_popup(self):
    self.sp = scanProfilePopup(self)
    self.sp.setGeometry(400, 100, 200, 200)
    self.sp.show()      

  @pyqtSlot()
  def show_find_max_popup(self):
    self.max = findMaxPopup(self, self.tabs.currentIndex())
    self.max.setGeometry(400, 100, 100, 100)
    self.max.show()

  @pyqtSlot()
  def show_connection_popup(self):
    self.connect = connectionPopup(self)
    self.connect.setGeometry(400, 100, 100, 100)
    self.connect.show()  

  @pyqtSlot()
  def show_connection_popup(self):
    self.seUI = sePopup(self)
    self.seUI.setGeometry(400, 100, 100, 100)
    self.seUI.show()

  @pyqtSlot()
  def load_file(self, filepath, trace):
    with open(filepath, 'r', encoding='latin-1') as csvfile:
      # Sniffer will detect if the first line are column names resolves
      # to True in ITS data
      firstline = csvfile.readline()
      firstline = firstline.split(',')
      csvfile.seek(0)
      its_data = csv.Sniffer().has_header(csvfile.read(2048))
      csvfile.seek(0)
      if its_data and len(firstline) >= 2:
        self.data[trace] = pd.read_csv(filepath, sep=',', encoding='latin1')
      else:
        dialect = csv.Sniffer().sniff(csvfile.read(), delimiters=';,')
        csvfile.seek(0)
        # Algorithm for reading spectrum analyzer csv files
        reader = csv.reader(csvfile, dialect)
        start = ''
        try:
          for row in reader:
            if 'Start' in row[0]:
              start = row[1]
              if '.' in start:
                start = start.split('.')
                start = start[0]
              elif ',' in start:
                start = start.split(',')
                start = start[0]
            if 'unit' in row[0].lower():
              if 'hz' in row[1].lower():
                x_axis = 'Frequency (' + row[1] + ')'
              else:
                y_axis = 'Meas. Peak (' + row[1] + ')'
            if start == row[0]:
              n = int(reader.line_num - 1)
              col_names = [x_axis, y_axis]
              self.data[trace] = pd.read_csv(filepath, names=col_names,
                                             usecols=[0,1],
                                             delimiter=dialect.delimiter,
                                             converters={x_axis: lambda x: float(x.replace(',','.')),
                                                         y_axis: lambda x: float(x.replace(',','.'))},
                                             skiprows=n,
                                             keep_default_na=False,
                                             index_col=False,
                                             skip_blank_lines=True)
              self.convert_to_MHz(trace)
              break
        except IndexError:
          print('File format may not be supported.  Please contact jchinn@google with file.')

  def _check_legend_empty(self):
    if not self.main_plot.get_legend_handles_labels()[1]:
      self.clear_plots()
      return True
    else:
      return False

  def remove_plot(self, trace):
    legend = self.main_plot.get_legend_handles_labels()[1]
    vlegend = self.vert_plot.get_legend_handles_labels()[1]
    hlegend = self.horiz_plot.get_legend_handles_labels()[1]
    its_val = [trace + ' - Vertical', trace + ' - Horizontal']
    lines = self.lines
    
    if trace in legend:
      self.main_plot.lines.pop(legend.index(trace))
      if not self._check_legend_empty():
        self.redraw_legend([0])
        self.redraw_plots()
    if its_val[0] in legend and its_val[1] in legend: 
      self.vert_plot.lines.pop(vlegend.index(its_val[0]))
      self.horiz_plot.lines.pop(hlegend.index(its_val[1]))
      self.main_plot.lines.pop(legend.index(its_val[0]))
      legend = self.main_plot.get_legend_handles_labels()[1]
      self.main_plot.lines.pop(legend.index(its_val[1]))
      if not self._check_legend_empty():
        self.redraw_legend([0, 1, 2])
        self.redraw_plots()
    elif its_val[0] in legend:
      self.main_plot.lines.pop(legend.index(its_val[0]))
      self.vert_plot.lines.pop(vlegend.index(its_val[0]))
      if not self._check_legend_empty():
        self.redraw_legend([0, 1])
        self.redraw_plots()
    elif its_val[1] in legend:
      self.main_plot.lines.pop(legend.index(its_val[1]))
      self.horiz_plot.lines.pop(hlegend.index(its_val[1]))
      if not self._check_legend_empty():
        self.redraw_legend([0, 2])
        self.redraw_plots()

  def dbl_clk_tree(self, index):
    item = self.treeview.selectedIndexes()[0]
    filetype = item.model().type(index)

    # Check file type for correct 
    if filetype == 'csv File' or filetype == 'DAT File':
      fp = item.model().filePath(index)
      trace = item.model().fileName(index).replace('.csv', '')
      trace = trace.replace('.DAT', '')

      # Load trace data if not loaded already
      if trace not in self.tracekey:
        self.load_file(fp, trace)
        self.tracekey.append(trace)

      # Get list of currently plotted lines
      legend = self.main_plot.get_legend_handles_labels()[1]
      its_val = [trace + ' - Vertical', trace + ' - Horizontal']

      if trace not in legend and its_val[0] not in legend and its_val[1] not in legend:
        self.plot_trace(trace)
        legend = self.main_plot.get_legend_handles_labels()[1]
        self.file_model.setCondition(True, legend)
      else:
        self.remove_plot(trace)
        self.remove_peaks(trace)
        self.file_model.setCondition(False, legend)
    elif filetype == 'Folder':
      return
    else:
      self.statusBar().showMessage('File type unsupported')

  def convert_to_MHz(self, trace):
    # Convert Hz to MHz and remove the Hz column
    cols = self.data[trace].columns.tolist()
    freq = cols[0]
    MHz = 'Frequency (MHz)'
    if '(Hz)' in freq:
      self.data[trace][MHz] = self.data[trace][freq]/1000000
      self.data[trace] = self.data[trace].drop([freq], axis=1)
      cols = self.data[trace].columns.tolist()
      cols.insert(0, cols.pop(cols.index(MHz)))
      self.data[trace] = self.data[trace].reindex(columns=cols)

  def merge_cf(self, trace):
    # Merge on data with correction factors
    corrected = 'Corrected Amp. (dBuV/m)'
    x = 'Frequency (MHz)'

    # Erase previous correction factor data
    if corrected in list(self.data[trace]):
      cols = self.data[trace].columns.tolist()
      self.data[trace] = self.data[trace].drop(cols[2:], axis=1)

    # Merge_asof can only be performed on integers
    self.data[trace]['Int'] = self.data[trace][x].astype(int)
    self.cfdata['Int'] = self.cfdata[x].astype(int)         
    self.data[trace] = pd.merge_asof(self.data[trace], self.cfdata.iloc[:,1:], 
                                     on='Int', direction='nearest',
                                     tolerance=1)
    self.data[trace] = self.data[trace].drop(['Int'], 1)

    # Merge upper and lower correction factor bounds
    last_freq = self.data[trace][x].iloc[-1]
    first_freq = self.data[trace][x].iloc[0]

    cf_frequencies = list(self.cfdata.index.values)
    for freq in cf_frequencies:
      if first_freq > freq:
        first_cf = freq
      elif first_freq < freq:
        break
    for freq in cf_frequencies:
      if last_freq < freq:
        last_cf = freq
        break
    
    # Organize data for interpolation
    cols = self.data[trace].columns.tolist()
    try:
      self.data[trace] = self.data[trace].append(self.cfdata.loc[[first_cf]])
    except UnboundLocalError:
      pass
    try:
      self.data[trace] = self.data[trace].append(self.cfdata.loc[[last_cf]])
    except UnboundLocalError:
      pass

    self.data[trace] = self.data[trace].sort_index()
    self.data[trace] = self.data[trace][cols]
    self.data[trace] = self.interpolate_cf(self.data[trace])

    # Drop the extra correction factor rows
    try:
      self.data[trace] = self.data[trace].drop(last_cf)
    except UnboundLocalError:
      pass
    try:
      self.data[trace] = self.data[trace].drop(first_cf)
    except UnboundLocalError:
      pass

    # Only needed if correction factors are NaN for frequency range
    self.data[trace] = self.data[trace].fillna(0)

    # Sum correction factors
    self.data[trace]['Total Correction Factor'] = self.data[trace].iloc[:,2:].sum(axis=1)

    # Calculate corrected values
    self.data[trace][corrected] = (self.data[trace].iloc[:,1]
                              + self.data[trace]['Total Correction Factor'] + 107)

  def interpolate_cf(self, df):
    columns = df.columns.tolist()
    for col in columns:
      first = df[col].first_valid_index()
      last = df[col].last_valid_index()
      df.loc[first:last, col] = df.loc[first:last, col].interpolate(method='index')
    return df

  def plot_trace(self, trace_name):
    # Method takes trace name and extrapolates the corresponding data
    column_headers = self.data[trace_name].columns.tolist()
    x = column_headers[0]
    y = column_headers[1]
    
    # Set ITS bool, position column contains polarity data
    if 'Position' in column_headers:
      itsdata = True

      # Add vertical/horizontal to label used for legend
      label_v = trace_name + ' - Vertical'
      label_h = trace_name + ' - Horizontal'

      # split_vert dataframe on vertical/horizontal
      if label_v not in self.data:
        self.data[label_v] = self.data[trace_name].loc[self.data[trace_name]['Position'] == 'Vertical']
      if label_h not in self.data:
        self.data[label_h] = self.data[trace_name].loc[self.data[trace_name]['Position'] == 'Horizontal']

      # Some data may be empty if only one polarity is scanned
      if not self.data[label_v].empty:
        self.lines = self.main_plot.plot(self.data[label_v][x], 
                                         self.data[label_v][y], 
                                         label=label_v)
        self.lines = self.vert_plot.plot(self.data[label_v][x], 
                                         self.data[label_v][y], 
                                         label=label_v)
        self.redraw_legend([0, 1])
      if not self.data[label_h].empty:
        self.lines = self.main_plot.plot(self.data[label_h][x], 
                                         self.data[label_h][y], 
                                         label=label_h)
        self.lines = self.horiz_plot.plot(self.data[label_h][x], 
                                         self.data[label_h][y], 
                                         label=label_h)
        self.redraw_legend([0, 2])
    
    # If not its data, plot first and last column on the main plot
    else:
      itsdata = False

      # Remove erroneous correction factor data
      self.data[trace_name] = self.data[trace_name].iloc[:,:2]

      # Merge frequency mask
      if self.mask == 'None':
        self.data[trace_name]['Mask'] = False
      else:
        self.data[trace_name]['Hz'] = self.data[trace_name]['Frequency (MHz)'] * 1000000
        self.data[trace_name]['Hz'] = self.data[trace_name]['Hz'].astype(int)
        self.frequency_mask_df['Hz'] = self.frequency_mask_df['Hz'].astype(int)        
        self.data[trace_name] = pd.merge_asof(self.data[trace_name], self.frequency_mask_df, 
                                        on='Hz', direction='nearest',
                                        tolerance=5000000)
        self.data[trace_name] = self.data[trace_name].drop(['Hz'], 1)
        self.data[trace_name] = self.data[trace_name].fillna(value=False, axis=1)
        
      # Merge correction factor data
      if self.cf_checkbox.isChecked():
        self.merge_cf(trace_name)
        column_headers = self.data[trace_name].columns.tolist()
        y = column_headers[-1]

      # Remove masked frequencies
      unmasked = self.data[trace_name].loc[self.data[trace_name]['Mask'] == False]

      # Plot on the main plot
      self.lines = self.main_plot.plot(unmasked[x],
                                       unmasked[y],
                                       label=trace_name)

      self.redraw_legend([0])

    # Store x/y limits
    self.original_xmin, self.original_xmax = self.main_plot.get_xlim()
    self.original_ymin, self.original_ymax = self.main_plot.get_ylim()

    # Update labels
    self.set_axis_labels(x, y)

    # Calculate peaks and update peak table
    self.get_peak_list(self.data[trace_name], trace_name, itsdata)

    # Redraw plots must be called or the added line will not show
    self.redraw_plots()

  def export_peak_table(self):
    df = pd.DataFrame()

    for i in range(0, self.peak_table.columnCount() - 1, 1):
      data = []
      for j in range(0, self.peak_table.rowCount(), 1):
        data.append(self.peak_table.item(j, i).data(0))
      df[self.peak_table.horizontalHeaderItem(i).data(0)] = data

    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = Path('Peaks_' + now + '.csv')
    df.to_csv(path_or_buf=self.workspace / filename, index=False)

  def get_peak_list(self, df, name, its):
    # Function to get list of highest peaks
    # First calculate step size of dataframe
    step = df['Frequency (MHz)'].iloc[1] - df['Frequency (MHz)'].iloc[0]

    # Calculate 5MHz upper and lower band
    band = 1
    while (step * band) < 2.5:
      band += 1
    
    # Generate peak list by grabbing the highest value in the 
    # last column of the dataframe.  Store that value in the peak list
    # and remove that band so the column can be searched again.
    self.peak_list = pd.DataFrame()
    i = 0
    while i < self.num_of_peaks:
      try:
        if its:
          peak_index = df.iloc[:,1].idxmax(axis=1)
          peak = df.loc[[peak_index]]
          numerical_index = peak_index
        else:
          cols = list(df)
          if cols[-1] == 'Mask':
            amplitude_col = 1
          else:
            amplitude_col = -1
          peak_index = df.iloc[:,amplitude_col].idxmax(axis=1)
          peak = df.loc[[peak_index]]
          numerical_index = list(df.index.values).index(peak_index)

        # If the band extends beyond the column, remove up to the end/beginning
        # of the column
        self.peak_list = self.peak_list.append(peak)
        if numerical_index-band <= 0:
          df = df.drop(df.index[:numerical_index+band])
          df = df.reset_index(drop=True)  
        elif numerical_index+band >= len(df):
          df = df.drop(df.index[numerical_index-band:])
          df = df.reset_index(drop=True)
        else:
          df = df.drop(df.index[numerical_index-band:numerical_index+band])
          df = df.reset_index(drop=True)
        self.peak_table.insertRow(0)
        i += 1
      except ValueError:
        break

    # Round significant figures to 3
    self.peak_list = self.peak_list.round(3)

    # Setup peak table
    self.peak_table.setColumnCount(len(df.columns) + 2)
    
    #self.peak_table.setRowCount(self.peak_table.rowCount() + self.num_of_peaks)
    cols = self.peak_list.columns.tolist()
    cols.extend(['Trace', 'Notes'])
    self.peak_table.setHorizontalHeaderLabels(cols)
    
    # Add items to table
    for i in range(len(self.peak_list.index)):
      for j in range(len(self.peak_list.columns)):
        self.peak_table.setItem(i, j, QTableWidgetItem(str(self.peak_list.iat[i, j])))
      self.peak_table.setItem(i, len(self.peak_list.columns), QTableWidgetItem(name))

    # Adjust table column size
    self.peak_table.resizeColumnsToContents()
    self.peak_table.resizeRowsToContents()

  def remove_peaks(self, name):
    items = self.peak_table.findItems(name, QtCore.Qt.MatchRecursive)
    items_index = []
    
    for item in items:
      items_index.insert(0, self.peak_table.indexFromItem(item))

    for item in items_index:
      self.peak_table.removeRow(item.row())

  def redraw_plots(self):
    # Update canvas required to see any new changes
    self.main_canvas.draw()
    self.vert_canvas.draw()
    self.horiz_canvas.draw()

  def set_axis_labels(self, x, y):
    self.main_plot.set_xlabel(x)
    self.main_plot.set_ylabel(y)
    self.vert_plot.set_xlabel(x)
    self.vert_plot.set_ylabel(y)
    self.horiz_plot.set_xlabel(x)
    self.horiz_plot.set_ylabel(y)

  def redraw_legend(self, graph):
    # Function takes list 0-2 and will redraw legend
    for x in graph:
      if x == 0:
        self.main_plot.legend(loc=0, framealpha=0.5, fontsize='small')
      if x == 1:
        self.vert_plot.legend(loc=0, framealpha=0.5, fontsize='small')
      if x == 2:
        self.horiz_plot.legend(loc=0, framealpha=0.5, fontsize='small')

  @pyqtSlot()
  def clear_plots(self):
    # Erase all traces from all plots
    self.main_plot.clear()
    self.vert_plot.clear()
    self.horiz_plot.clear()
    self.main_plot.grid()
    self.vert_plot.grid()
    self.horiz_plot.grid()
    self.set_all_autoscale()
    self.redraw_plots()

    # Clear background listbox
    self.file_model.setCondition(False, [])
    
    # Clear peak list 
    for i in range(self.peak_table.rowCount(), -1, -1):
      self.peak_table.removeRow(i)

  @pyqtSlot()
  def wifi_five(self):
    # Set the plot to the 5GHz WiFi band
    self.main_plot.set_xlim([5000, 6000])
    self.vert_plot.set_xlim([5000, 6000])
    self.horiz_plot.set_xlim([5000, 6000])
    self.main_plot.autoscale(axis='y', tight=True)
    self.vert_plot.autoscale(axis='y', tight=True)
    self.horiz_plot.autoscale(axis='y', tight=True)
    self.redraw_plots()

  @pyqtSlot(str)
  def cispr_limits(self, classlimit):
    if classlimit == 'A':
      x = [30, 230, 230, 1000, 1000, 3000, 3000, 6000]
      y = [40, 40, 47, 47, 60, 60, 64, 64]
    elif classlimit == 'B':
      x = [30, 230, 230, 1000, 1000, 3000, 3000, 6000]
      y = [30, 30, 37, 37, 50, 50, 54, 54]
    limit = 'CISPR Limit - ' + classlimit
    self.main_plot.plot(x, y, label=limit)
    self.vert_plot.plot(x, y, label=limit)
    self.horiz_plot.plot(x, y, label=limit)

    self.redraw_legend([0, 1, 2])

    self.redraw_plots()

  @pyqtSlot(str)
  def fcc_limits(self, classlimit):
    if classlimit == 'A':
      x = [30, 88, 88, 216, 216, 960, 960, 1000, 1000, 40000]
      y = [39.1, 39.1, 43.5, 43.5, 46.4, 46.4, 49.5, 49.5, 60, 60]
    elif classlimit == 'B':
      x = [30, 88, 88, 216, 216, 960, 960, 1000, 1000, 40000]
      y = [29.5, 29.5, 33, 33, 35.5, 35.5, 43.5, 43.5, 50, 50]
    limit = 'FCC Limit - ' + classlimit
    self.main_plot.plot(x, y, label=limit)
    self.vert_plot.plot(x, y, label=limit)
    self.horiz_plot.plot(x, y, label=limit)

    self.redraw_legend([0, 1, 2])

    self.redraw_plots()

  def set_all_autoscale(self):
    self.main_plot.set_autoscalex_on(True)
    self.main_plot.set_autoscaley_on(True)
    self.vert_plot.set_autoscalex_on(True)
    self.vert_plot.set_autoscaley_on(True)
    self.horiz_plot.set_autoscalex_on(True)
    self.horiz_plot.set_autoscaley_on(True)

  def format_filepath(self, files):
    # Strip filepaths/file extensions for easier readability
    formatted_files = []
    for ffile in files:
      _ , tmp_file = os.path.split(ffile)
      tmp_file, _ = os.path.splitext(tmp_file)
      formatted_files.append(tmp_file)
    return formatted_files

  def handle_button_event(self, event):
    # Reset x-axis on double click on plot if 5-6GHz button is pushed
    if event.dblclick and event.inaxes:
      self.main_plot.set_xlim([self.original_xmin, self.original_xmax])
      self.vert_plot.set_xlim([self.original_xmin, self.original_xmax])
      self.horiz_plot.set_xlim([self.original_xmin, self.original_xmax])
      self.main_plot.set_ylim([self.original_ymin, self.original_ymax])
      self.vert_plot.set_ylim([self.original_ymin, self.original_ymax])
      self.horiz_plot.set_ylim([self.original_ymin, self.original_ymax])
      self.set_all_autoscale()
      self.redraw_plots()

if __name__ == '__main__':
  if 'setup' in str(sys.argv):
    print('Setting up...')
    create_sub_directories()
    print('Setup complete!')
  else:
    app = QApplication(sys.argv)
    ex = EasyEmi()
    sys.exit(app.exec_())