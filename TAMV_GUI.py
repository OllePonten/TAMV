#!/usr/bin/env python3

# TAMV version 2.0RC1
# Python Script to align multiple tools on Jubilee printer with Duet3d Controller
# Using images from USB camera and finding circles in those images
#
# TAMV originally Copyright (C) 2020 Danal Estes all rights reserved.
# TAMV 2.0 Copyright (C) 2021 Haytham Bennani all rights reserved.
# Released under The MIT License. Full text available via https://opensource.org/licenses/MIT
#
# Requires OpenCV to be installed on Pi
# Requires running via the OpenCV installed python (that is why no shebang)
# Requires network connection to Duet based printer running Duet/RepRap V2 or V3
#

# GUI imports
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QCheckBox,
    QComboBox,
    QDesktopWidget,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QIcon
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread, QMutex, QPoint, QSize

# Core imports
import os
import sys
import cv2
import numpy as np
import math
import DuetWebAPI as DWA
from time import sleep, time
import datetime
import json
import time


# graphing imports
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.patches as patches
from matplotlib.ticker import FormatStrFormatter

default_minCircularity = 0.7
default_minArea = 300
# styles
global style_green, style_red, style_disabled, style_orange
style_green = 'background-color: green; color: white;'
style_red = 'background-color: red; color: white;'
style_disabled = 'background-color: #cccccc; color: #999999; border-style: solid;'
style_orange = 'background-color: dark-grey; color: orange;'

class CPDialog(QDialog):
    def __init__(self,
                parent=None,
                title='Set Controlled Point',
                summary='<b>Instructions:</b><br>Jog until controlled point is centered in the window.<br>Click OK to save and return to main window.',
                disabled = False):
        super(CPDialog,self).__init__(parent=parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle(title)
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QGridLayout()
        self.layout.setSpacing(3)
        # add information panel
        self.cp_info = QLabel(summary)
        # add jogging grid
        self.buttons={}
        buttons_layout = QGridLayout()

        # X
        self.button_x1 = QPushButton('-1')
        self.button_x2 = QPushButton('-0.1')
        self.button_x3 = QPushButton('-0.01')
        self.button_x4 = QPushButton('+0.01')
        self.button_x5 = QPushButton('+0.1')
        self.button_x6 = QPushButton('+1')
        # set X sizes
        self.button_x1.setFixedSize(60,60) 
        self.button_x2.setFixedSize(60,60)
        self.button_x3.setFixedSize(60,60)
        self.button_x4.setFixedSize(60,60)
        self.button_x5.setFixedSize(60,60)
        self.button_x6.setFixedSize(60,60)
        # attach actions
        self.button_x1.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X-1 G90'))
        self.button_x2.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X-0.1 G90'))
        self.button_x3.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X-0.01 G90'))
        self.button_x4.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X0.01 G90'))
        self.button_x5.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X0.1 G90'))
        self.button_x6.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 X1 G90'))
        # add buttons to window
        x_label = QLabel('X')
        buttons_layout.addWidget(x_label,0,0)
        buttons_layout.addWidget(self.button_x1,0,1)
        buttons_layout.addWidget(self.button_x2,0,2)
        buttons_layout.addWidget(self.button_x3,0,3)
        buttons_layout.addWidget(self.button_x4,0,4)
        buttons_layout.addWidget(self.button_x5,0,5)
        buttons_layout.addWidget(self.button_x6,0,6)

        # Y
        self.button_y1 = QPushButton('-1')
        self.button_y2 = QPushButton('-0.1')
        self.button_y3 = QPushButton('-0.01')
        self.button_y4 = QPushButton('+0.01')
        self.button_y5 = QPushButton('+0.1')
        self.button_y6 = QPushButton('+1')
        # set X sizes
        self.button_y1.setFixedSize(60,60)
        self.button_y2.setFixedSize(60,60)
        self.button_y3.setFixedSize(60,60)
        self.button_y4.setFixedSize(60,60)
        self.button_y5.setFixedSize(60,60)
        self.button_y6.setFixedSize(60,60)
        # attach actions
        self.button_y1.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y-1 G90'))
        self.button_y2.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y-0.1 G90'))
        self.button_y3.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y-0.01 G90'))
        self.button_y4.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y0.01 G90'))
        self.button_y5.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y0.1 G90'))
        self.button_y6.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Y1 G90'))
        # add buttons to window
        y_label = QLabel('Y')
        buttons_layout.addWidget(y_label,1,0)
        buttons_layout.addWidget(self.button_y1,1,1)
        buttons_layout.addWidget(self.button_y2,1,2)
        buttons_layout.addWidget(self.button_y3,1,3)
        buttons_layout.addWidget(self.button_y4,1,4)
        buttons_layout.addWidget(self.button_y5,1,5)
        buttons_layout.addWidget(self.button_y6,1,6)

        # Z
        self.button_z1 = QPushButton('-1')
        self.button_z2 = QPushButton('-0.1')
        self.button_z3 = QPushButton('-0.01')
        self.button_z4 = QPushButton('+0.01')
        self.button_z5 = QPushButton('+0.1')
        self.button_z6 = QPushButton('+1')
        # set X sizes
        self.button_z1.setFixedSize(60,60) 
        self.button_z2.setFixedSize(60,60)
        self.button_z3.setFixedSize(60,60)
        self.button_z4.setFixedSize(60,60)
        self.button_z5.setFixedSize(60,60)
        self.button_z6.setFixedSize(60,60)
        # attach actions
        self.button_z1.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z-1 G90'))
        self.button_z2.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z-0.1 G90'))
        self.button_z3.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z-0.01 G90'))
        self.button_z4.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z0.01 G90'))
        self.button_z5.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z0.1 G90'))
        self.button_z6.clicked.connect(lambda: self.parent().printer.gCode('G91 G1 Z1 G90'))
        # add buttons to window
        z_label = QLabel('Z')
        buttons_layout.addWidget(z_label,2,0)
        buttons_layout.addWidget(self.button_z1,2,1)
        buttons_layout.addWidget(self.button_z2,2,2)
        buttons_layout.addWidget(self.button_z3,2,3)
        buttons_layout.addWidget(self.button_z4,2,4)
        buttons_layout.addWidget(self.button_z5,2,5)
        buttons_layout.addWidget(self.button_z6,2,6)

        #self.macro_field = QLineEdit()
        #self.button_macro = QPushButton('Run macro')
        #buttons_layout.addWidget(self.button_macro,3,1,2,1)
        #buttons_layout.addWidget(self.macro_field,3,2,1,-1)


        # Set up items on dialog grid
        self.layout.addWidget(self.cp_info,0,0,1,-1)
        self.layout.addLayout(buttons_layout,1,0,3,7)
        # OK/Cancel buttons
        self.layout.addWidget(self.buttonBox)
                
        # apply layout
        self.setLayout(self.layout)

    def setSummaryText(self, message):
        self.cp_info.setText(message)

class DebugDialog(QDialog):
    def __init__(self,parent=None, message=''):
        super(DebugDialog,self).__init__(parent=parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle('Debug Information')
        # Set layout details
        self.layout = QGridLayout()
        self.layout.setSpacing(3)
        
        # text area
        self.textarea = QTextEdit()
        self.textarea.setAcceptRichText(False)
        self.textarea.setReadOnly(True)
        self.layout.addWidget(self.textarea,0,0)
        # apply layout
        self.setLayout(self.layout)
        temp_text = ''
        try:
            if self.parent().video_thread.isRunning():
                temp_text += 'Video thread running\n'
        except Exception as e1:
            None
        if len(message) > 0:
            temp_text += '\nCalibration Debug Messages:\n' + message
        self.textarea.setText(temp_text)

class CameraSettingsDialog(QDialog):
    def __init__(self,parent=None, message=''):
        super(CameraSettingsDialog,self).__init__(parent=parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle('Camera Settings')
        
        #QBtn = QDialogButtonBox.Close
        #self.buttonBox = QDialogButtonBox(QBtn)
        #self.buttonBox.accepted.connect(self.accept)
        #self.buttonBox.rejected.connect(self.reject)

        # Get camera settings from video thread
        try:
            (brightness_input, contrast_input, saturation_input, hue_input) = self.parent().video_thread.getProperties()
        except Exception as set1:
            self.updateStatusbar('Error fetching camera parameters.')
            print('ERROR: Camera Settings: ' + str(set1))
        
        # Set layout details
        self.layout = QVBoxLayout()
        self.layout.setSpacing(3)
        # apply layout
        self.setLayout(self.layout)

        # Camera Combobox
        self.camera_combo = QComboBox()
        camera_description = str(video_src) + ': ' \
            + str(self.parent().video_thread.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) \
            + 'x' + str(self.parent().video_thread.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) + ' @ ' \
            + str(self.parent().video_thread.cap.get(cv2.CAP_PROP_FPS)) + 'fps'
        self.camera_combo.addItem(camera_description)
        #self.camera_combo.currentIndexChanged.connect(self.parent().video_thread.changeVideoSrc)
        # Get cameras button
        self.camera_button = QPushButton('Get cameras')
        self.camera_button.clicked.connect(self.getCameras)
        if self.parent().video_thread.alignment:
            self.camera_button.setDisabled(True)
        else: self.camera_button.setDisabled(False)
        #self.getCameras()
        # Brightness slider
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setMinimum(0)
        self.brightness_slider.setMaximum(255)
        self.brightness_slider.setValue(int(brightness_input))
        self.brightness_slider.valueChanged.connect(self.changeBrightness)
        self.brightness_slider.setTickPosition(QSlider.TicksBelow)
        self.brightness_slider.setTickInterval(1)
        self.brightness_label = QLabel(str(int(brightness_input)))
        # Contrast slider
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setMinimum(0)
        self.contrast_slider.setMaximum(255)
        self.contrast_slider.setValue(int(contrast_input))
        self.contrast_slider.valueChanged.connect(self.changeContrast)
        self.contrast_slider.setTickPosition(QSlider.TicksBelow)
        self.contrast_slider.setTickInterval(1)
        self.contrast_label = QLabel(str(int(contrast_input)))
        # Saturation slider
        self.saturation_slider = QSlider(Qt.Horizontal)
        self.saturation_slider.setMinimum(0)
        self.saturation_slider.setMaximum(255)
        self.saturation_slider.setValue(int(saturation_input))
        self.saturation_slider.valueChanged.connect(self.changeSaturation)
        self.saturation_slider.setTickPosition(QSlider.TicksBelow)
        self.saturation_slider.setTickInterval(1)
        self.saturation_label = QLabel(str(int(saturation_input)))
        # Hue slider
        self.hue_slider = QSlider(Qt.Horizontal)
        self.hue_slider.setMinimum(0)
        self.hue_slider.setMaximum(8)
        self.hue_slider.setValue(int(hue_input))
        self.hue_slider.valueChanged.connect(self.changeHue)
        self.hue_slider.setTickPosition(QSlider.TicksBelow)
        self.hue_slider.setTickInterval(1)
        self.hue_label = QLabel(str(int(hue_input)))
        # Reset button
        self.reset_button = QPushButton("Reset to defaults")
        self.reset_button.setToolTip('Reset camera settings to defaults.')
        self.reset_button.clicked.connect(self.resetDefaults)

        # Save button
        self.save_button = QPushButton('Save and Close')
        self.save_button.setToolTip('Save current parameters to settings.json file')
        self.save_button.clicked.connect(self.sendUserParameters)
        self.save_button.setObjectName('active')
        
        # Close button
        self.close_button = QPushButton('Cancel and close')
        self.close_button.setToolTip('Cancel changes and return to main program.')
        self.close_button.clicked.connect(self.closeCPWindow)
        self.close_button.setObjectName('terminate')

        # Layout objects
        # Camera drop-down
        self.camera_box = QGroupBox('Camera')
        self.layout.addWidget(self.camera_box)
        cmbox = QHBoxLayout()
        self.camera_box.setLayout(cmbox)
        cmbox.addWidget(self.camera_combo)
        cmbox.addWidget(self.camera_button)

        # Brightness
        self.brightness_box =QGroupBox('Brightness')
        self.layout.addWidget(self.brightness_box)
        bvbox = QHBoxLayout()
        self.brightness_box.setLayout(bvbox)
        bvbox.addWidget(self.brightness_slider)
        bvbox.addWidget(self.brightness_label)
        # Contrast
        self.contrast_box =QGroupBox('Contrast')
        self.layout.addWidget(self.contrast_box)
        cvbox = QHBoxLayout()
        self.contrast_box.setLayout(cvbox)
        cvbox.addWidget(self.contrast_slider)
        cvbox.addWidget(self.contrast_label)
        # Saturation
        self.saturation_box =QGroupBox('Saturation')
        self.layout.addWidget(self.saturation_box)
        svbox = QHBoxLayout()
        self.saturation_box.setLayout(svbox)
        svbox.addWidget(self.saturation_slider)
        svbox.addWidget(self.saturation_label)
        # Hue
        self.hue_box =QGroupBox('Hue')
        self.layout.addWidget(self.hue_box)
        hvbox = QHBoxLayout()
        self.hue_box.setLayout(hvbox)
        hvbox.addWidget(self.hue_slider)
        hvbox.addWidget(self.hue_label)
        # Threshold
        #self.th_box = QGroupBox('Threshold')
        # Reset button
        self.layout.addWidget(self.reset_button)
        self.layout.addWidget(self.save_button)
        self.layout.addWidget(self.close_button)

        # OK Cancel buttons
        #self.layout.addWidget(self.buttonBox)

    def resetDefaults(self):
        self.parent().video_thread.resetProperties()
        (brightness_input, contrast_input, saturation_input, hue_input) = self.parent().video_thread.getProperties()
        
        brightness_input = int(brightness_input)
        contrast_input = int(contrast_input)
        saturation_input = int(saturation_input)
        hue_input = int(hue_input)
        self.brightness_slider.setValue(brightness_input)
        self.brightness_label.setText(str(brightness_input))
        self.contrast_slider.setValue(contrast_input)
        self.contrast_label.setText(str(contrast_input))
        self.saturation_slider.setValue(saturation_input)
        self.saturation_label.setText(str(saturation_input))
        self.hue_slider.setValue(hue_input)
        self.hue_label.setText(str(hue_input))

    def changeBrightness(self):
        parameter = int(self.brightness_slider.value())
        try:
            self.parent().video_thread.setProperty(brightness=parameter)
        except:
            None
        self.brightness_label.setText(str(parameter))

    def changeContrast(self):
        parameter = int(self.contrast_slider.value())
        try:
            self.parent().video_thread.setProperty(contrast=parameter)
        except:
            None
        self.contrast_label.setText(str(parameter))

    def changeSaturation(self):
        parameter = int(self.saturation_slider.value())
        try:
            self.parent().video_thread.setProperty(saturation=parameter)
        except:
            None
        self.saturation_label.setText(str(parameter))

    def changeHue(self):
        parameter = int(self.hue_slider.value())
        try:
            self.parent().video_thread.setProperty(hue=parameter)
        except:
            None
        self.hue_label.setText(str(parameter))

    def getCameras(self):
        # checks the first 6 indexes.
        i = 6
        index = 0
        self.camera_combo.clear()
        _cameras = []
        original_camera_description = str(video_src) + ': ' \
            + str(self.parent().video_thread.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) \
            + 'x' + str(self.parent().video_thread.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) + ' @ ' \
            + str(self.parent().video_thread.cap.get(cv2.CAP_PROP_FPS)) + 'fps'
        _cameras.append(original_camera_description)
        while i > 0:
            if index != video_src:
                tempCap = cv2.VideoCapture(index)
                if tempCap.read()[0]:
                    api = tempCap.getBackendName()
                    camera_description = str(index) + ': ' \
                        + str(tempCap.get(cv2.CAP_PROP_FRAME_WIDTH)) \
                        + 'x' + str(tempCap.get(cv2.CAP_PROP_FRAME_HEIGHT)) + ' @ ' \
                        + str(tempCap.get(cv2.CAP_PROP_FPS)) + 'fps'
                    _cameras.append(camera_description)
                    tempCap.release()
            index += 1
            i -= 1
        #cameras = [line for line in allOutputs if float(line['propmode']) > -1 ]
        _cameras.sort()
        for camera in _cameras:
            self.camera_combo.addItem(camera)
        self.camera_combo.setCurrentText(original_camera_description)

    def sendUserParameters(self):
        _tempSrc = self.camera_combo.currentText()
        _tempSrc = _tempSrc[:_tempSrc.find(':')]
        self.parent().saveUserParameters(cameraSrc=_tempSrc)
        self.close()

    def closeCPWindow(self):
        self.parent().updateStatusbar('Camera changes discarded.')
        self.close()

class OverlayLabel(QLabel):
    def __init__(self):
        super(OverlayLabel, self).__init__()
        self.display_text = 'Welcome to TAMV. Enter your printer address and click \"Connect..\" to start.'

    def paintEvent(self, event):
        super(OverlayLabel, self).paintEvent(event)
        pos = QPoint(10, 470)
        painter = QPainter(self)
        painter.setBrush(QColor(204,204,204,230))
        painter.setPen(QColor(255, 255, 255,0))
        painter.drawRect(0,450,640,50)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(pos, self.display_text)
    
    def setText(self, textToDisplay):
        self.display_text = textToDisplay

class CalibrateNozzles(QThread):
    # Signals
    status_update = pyqtSignal(str)
    message_update = pyqtSignal(str)
    change_pixmap_signal = pyqtSignal(np.ndarray)
    calibration_complete = pyqtSignal()
    detection_error = pyqtSignal(str)
    result_update = pyqtSignal(object)

    alignment = False
    _running = False
    display_crosshair = False
    detection_on = False

    def __init__(self, parent=None, th1=1, th2=50, thstep=1, minArea=default_minArea, minCircularity=default_minCircularity,numTools=0,cycles=1, align=False):
        super(QThread,self).__init__(parent=parent)
        # transformation matrix
        self.transform_matrix = []
        self.xray = False
        self.loose = False
        self.invert = False
        self.detector_changed = False
        self.detect_th1 = th1
        self.detect_th2 = th2
        self.detect_thstep = thstep
        self.detect_minArea = minArea
        self.detect_minCircularity = minCircularity
        self.numTools = numTools
        self.cycles = cycles
        self.alignment = align
        self.message_update.emit('Detector created, waiting for tool..')

        # start with detection off
        self.display_crosshair = False
        self.detection_on = False

        # Video Parameters
        self.brightness_default = 0
        self.contrast_default = 0
        self.saturation_default = 0
        self.hue_default = 0
        self.brightness = -1
        self.contrast = -1
        self.saturation = -1
        self.hue = -1

        # Start Video feed
        self.cap = cv2.VideoCapture(video_src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
        #self.cap.set(cv2.CAP_PROP_FPS,25)
        self.brightness_default = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
        self.contrast_default = self.cap.get(cv2.CAP_PROP_CONTRAST)
        self.saturation_default = self.cap.get(cv2.CAP_PROP_SATURATION)
        self.hue_default = self.cap.get(cv2.CAP_PROP_HUE)

        self.ret, self.cv_img = self.cap.read()
        if self.ret:
            local_img = self.cv_img
            self.change_pixmap_signal.emit(local_img)
        else:
            self.cap.open(video_src)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
            #self.cap.set(cv2.CAP_PROP_FPS,25)
            self.ret, self.cv_img = self.cap.read()
            local_img = self.cv_img
            self.change_pixmap_signal.emit(local_img)

    def toggleXray(self):
        if self.xray:
            self.xray = False
        else: self.xray = True

    def toggleLoose(self):
        self.detector_changed = True
        if self.loose:
            self.loose = False
        else: self.loose = True
        
    def toggleInvert(self):
        if self.invert:
            self.invert = False
        else: self.invert = True
        
    def setProperty(self,brightness=-1, contrast=-1, saturation=-1, hue=-1):
        try:
            if int(brightness) >= 0:
                self.brightness = brightness
                self.cap.set(cv2.CAP_PROP_BRIGHTNESS,self.brightness)
        except Exception as b1: 
            print('Brightness exception: ', b1 )
        try:
            if int(contrast) >= 0:
                self.contrast = contrast
                self.cap.set(cv2.CAP_PROP_CONTRAST,self.contrast)
        except Exception as c1:
            print('Contrast exception: ', c1 )
        try:
            if int(saturation) >= 0:
                self.saturation = saturation
                self.cap.set(cv2.CAP_PROP_SATURATION,self.saturation)
        except Exception as s1:
            print('Saturation exception: ', s1 )
        try:
            if int(hue) >= 0:
                self.hue = hue
                self.cap.set(cv2.CAP_PROP_HUE,self.hue)
        except Exception as h1:
            print('Hue exception: ', h1 )

    def getProperties(self):
        return (self.brightness_default, self.contrast_default, self.saturation_default,self.hue_default)

    def resetProperties(self):
        self.setProperty(brightness=self.brightness_default, contrast = self.contrast_default, saturation=self.saturation_default, hue=self.hue_default)

    def run(self):
        self.createDetector()
        while True:
            if self.detection_on:
                if self.alignment:
                    try:
                        if self.loose:
                            self.detect_minCircularity = 0.6
                        else: self.detect_minCircularity = default_minCircularity
                        if self.detector_changed:
                            self.createDetector()
                            self.detector_changed = False
                        self._running = True
                        while self._running:
                            self.cycles = self.parent().cycles
                            for rep in range(self.cycles):
                                for tool in range(self.parent().num_tools):
                                    # process GUI events
                                    app.processEvents()
                                    # Update status bar
                                    self.status_update.emit('Calibrating T' + str(tool) + ', cycle: ' + str(rep+1) + '/' + str(self.cycles))
                                    # Load next tool for calibration
                                    self.parent().printer.gCode('T'+str(tool))
                                    # Move tool to CP coordinates
                                    self.parent().printer.gCode('G1 X' + str(self.parent().cp_coords['X']))
                                    self.parent().printer.gCode('G1 Y' + str(self.parent().cp_coords['Y']))
                                    self.parent().printer.gCode('G1 Z' + str(self.parent().cp_coords['Z']))
                                    # Wait for moves to complete
                                    while self.parent().printer.getStatus() not in 'idle':
                                        # process GUI events
                                        app.processEvents()
                                        self.ret, self.cv_img = self.cap.read()
                                        if self.ret:
                                            local_img = self.cv_img
                                            self.change_pixmap_signal.emit(local_img)
                                        else:
                                            self.cap.open(video_src)
                                            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
                                            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
                                            self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
                                            #self.cap.set(cv2.CAP_PROP_FPS,25)
                                            self.ret, self.cv_img = self.cap.read()
                                            local_img = self.cv_img
                                            self.change_pixmap_signal.emit(local_img)
                                            continue
                                    # Update message bar
                                    self.message_update.emit('Searching for nozzle..')
                                    # Process runtime algorithm changes
                                    if self.loose:
                                        self.detect_minCircularity = 0.6
                                    else: self.detect_minCircularity = default_minCircularity
                                    if self.detector_changed:
                                        self.createDetector()
                                        self.detector_changed = False
                                    # Analyze frame for blobs
                                    (c, transform, mpp) = self.calibrateTool(tool, rep)
                                    # process GUI events
                                    app.processEvents()
                                    # apply offsets to machine
                                    self.parent().printer.gCode( 'G10 P' + str(tool) + ' X' + str(c['X']) + ' Y' + str(c['Y']) )
                            # signal end of execution
                            self._running = False
                        # Update status bar
                        self.status_update.emit('Calibration complete: Resetting machine.')
                        # HBHBHB
                        # Update debug window with results
                        # self.parent().debugString += '\nCalibration output:\n'
                        self.parent().printer.gCode('T-1')
                        self.parent().printer.gCode('G1 X' + str(self.parent().cp_coords['X']))
                        self.parent().printer.gCode('G1 Y' + str(self.parent().cp_coords['Y']))
                        self.parent().printer.gCode('G1 Z' + str(self.parent().cp_coords['Z']))
                        self.status_update.emit('Calibration complete: Done.')
                        self.alignment = False
                        self.detection_on = False
                        self.display_crosshair = False
                        self._running = False
                        self.calibration_complete.emit()
                    except Exception as mn1:
                        self.alignment = False
                        self.detection_on = False
                        self.display_crosshair = False
                        self._running = False
                        self.detection_error.emit(str(mn1))
                        self.cap.release()
                else:
                    # don't run alignment - fetch frames and detect only
                    try:
                        if self.loose:
                            self.detect_minCircularity = 0.6
                        else: self.detect_minCircularity = default_minCircularity
                        self._running = True
                        # transformation matrix
                        #self.transform_matrix = []
                        while self._running and self.detection_on:
                            # Update status bar
                            #self.status_update.emit('Detection mode: ON')
                            # Process runtime algorithm changes
                            if self.loose:
                                self.detect_minCircularity = 0.6
                            else: self.detect_minCircularity = default_minCircularity
                            if self.detector_changed:
                                self.createDetector()
                                self.detector_changed = False
                            # Run detection and update output
                            self.analyzeFrame()
                            # process GUI events
                            app.processEvents()
                    except Exception as mn1:
                        self._running = False
                        self.detection_error.emit(str(mn1))
                        self.cap.release()
            else:
                while not self.detection_on:
                    try:
                        self.ret, self.cv_img = self.cap.read()
                        if self.ret:
                            local_img = self.cv_img
                            self.change_pixmap_signal.emit(local_img)
                        else:
                            # reset capture
                            self.cap.open(video_src)
                            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
                            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
                            self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
                            #self.cap.set(cv2.CAP_PROP_FPS,25)
                            self.ret, self.cv_img = self.cap.read()
                            if self.ret:
                                local_img = self.cv_img
                                self.change_pixmap_signal.emit(local_img)
                            continue
                        app.processEvents()
                    except Exception as mn2:
                        self.status_update( 'Error: ' + str(mn2) )
                        print('Error: ' + str(mn2))
                        self.cap.release()
                        self.detection_on = False
                        self._running = False
                        exit()
                    app.processEvents()
                app.processEvents()
                continue
        self.cap.release()

    def analyzeFrame(self):
        # Placeholder coordinates
        xy = [0,0]
        # Counter of frames with no circle.
        nocircle = 0
        # Random time offset
        rd = int(round(time.time()*1000))
        # reset capture
        #self.cap.open(video_src)
        #self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
        #self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
        #self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
        #self.cap.set(cv2.CAP_PROP_FPS,25)

        while True and self.detection_on:
            app.processEvents()
            self.ret, self.frame = self.cap.read()
            if not self.ret:
                # reset capture
                self.cap.open(video_src)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
                #self.cap.set(cv2.CAP_PROP_FPS,25)
                continue
            if self.alignment:
                try:
                    # capture tool location in machine space before processing
                    toolCoordinates = self.parent().printer.getCoords()
                except Exception as c1:
                    toolCoordinates = None
            # capture first clean frame for display
            cleanFrame = self.frame
            # apply nozzle detection algorithm
            # Detection algorithm 1:
            #    gamma correction -> use Y channel from YUV -> GaussianBlur (7,7),6 -> adaptive threshold
            gammaInput = 1.2
            self.frame = self.adjust_gamma(image=self.frame, gamma=gammaInput)
            yuv = cv2.cvtColor(self.frame, cv2.COLOR_BGR2YUV)
            yuvPlanes = cv2.split(yuv)
            yuvPlanes[0] = cv2.GaussianBlur(yuvPlanes[0],(7,7),6)
            yuvPlanes[0] = cv2.adaptiveThreshold(yuvPlanes[0],255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,35,1)
            self.frame = cv2.cvtColor(yuvPlanes[0],cv2.COLOR_GRAY2BGR)

            target = [int(np.around(self.frame.shape[1]/2)),int(np.around(self.frame.shape[0]/2))]
            # Process runtime algorithm changes
            if self.loose:
                self.detect_minCircularity = 0.6
            else: self.detect_minCircularity = default_minCircularity
            if self.detector_changed:
                self.createDetector()
                self.detector_changed = False
            # draw the timestamp on the frame AFTER the circle detector! Otherwise it finds the circles in the numbers.
            if self.xray:
                cleanFrame = self.frame
            # run nozzle detection for keypoints
            if self.invert:
                cleanFrame = cv2.bitwise_not(self.frame)
                self.frame = cv2.bitwise_not(self.frame)
                keypoints = self.detector.detect(cleanFrame)
            else:
                keypoints = self.detector.detect(self.frame)
            # check if we are displaying a crosshair
            if self.display_crosshair:
                self.frame = cv2.line(cleanFrame, (target[0],    target[1]-25), (target[0],    target[1]+25), (0, 255, 0), 1)
                self.frame = cv2.line(self.frame, (target[0]-25, target[1]   ), (target[0]+25, target[1]   ), (0, 255, 0), 1)
            else: self.frame = cleanFrame
            # update image
            local_img = self.frame
            self.change_pixmap_signal.emit(local_img)
            if(nocircle> 25):
                self.message_update.emit( 'Error in detecting nozzle.' )
                nocircle = 0
                continue
            num_keypoints=len(keypoints)
            if (num_keypoints == 0):
                if (25 < (int(round(time.time() * 1000)) - rd)):
                    nocircle += 1
                    self.frame = self.putText(self.frame,'No circles found',offsety=3)
                    self.message_update.emit( 'No circles found.' )
                    local_img = self.frame
                    self.change_pixmap_signal.emit(local_img)
                continue
            if (num_keypoints > 1):
                if (25 < (int(round(time.time() * 1000)) - rd)):
                    self.message_update.emit( 'Too many circles found. Please stop and clean the nozzle.' )
                    self.frame = self.putText(self.frame,'Too many circles found '+str(num_keypoints),offsety=3, color=(255,255,255))
                    self.frame = cv2.drawKeypoints(self.frame, keypoints, np.array([]), (255,255,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
                    local_img = self.frame
                    self.change_pixmap_signal.emit(local_img)
                continue
            # Found one and only one circle.  Put it on the frame.
            nocircle = 0 
            xy = np.around(keypoints[0].pt)
            r = np.around(keypoints[0].size/2)
            # draw the blobs that look circular
            self.frame = cv2.drawKeypoints(self.frame, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
            # Note its radius and position
            ts =  'U{0:3.0f} V{1:3.0f} R{2:2.0f}'.format(xy[0],xy[1],r)
            xy = np.uint16(xy)
            #self.frame = self.putText(self.frame, ts, offsety=2, color=(0, 255, 0), stroke=2)
            self.message_update.emit(ts)
            # show the frame
            local_img = self.frame
            self.change_pixmap_signal.emit(local_img)
            rd = int(round(time.time() * 1000))
            #end the loop
            break
        # and tell our parent.
        if self.detection_on:
            return (xy, target, toolCoordinates, r)
        else:
            return

    def calibrateTool(self, tool, rep):
        # timestamp for caluclating tool calibration runtime
        self.startTime = time.time()
        # average location of keypoints in frame
        self.average_location=[0,0]
        # current location
        self.current_location = {'X':0,'Y':0}
        # guess position used for camera calibration
        self.guess_position  = [1,1]
        # current keypoint location
        self.xy = [0,0]
        # previous keypoint location
        self.oldxy  = self.xy
        # Tracker flag to set which state algorithm is running in
        self.state = 0
        # detected blob counter
        self.detect_count = 0
        # Save CP coordinates to local class
        self.cp_coordinates = self.parent().cp_coords
        # number of average position loops
        self.position_iterations = 5
        # calibration move set (0.5mm radius circle over 10 moves)
        self.calibrationCoordinates = [ [0,-0.5], [0.294,-0.405], [0.476,-0.155], [0.476,0.155], [0.294,0.405], [0,0.5], [-0.294,0.405], [-0.476,0.155], [-0.476,-0.155], [-0.294,-0.405] ]

        # Check if camera calibration matrix is already defined
        if len(self.transform_matrix) > 1:
            # set state flag to Step 2: nozzle alignment stage
            self.state = 200
            self.parent().debugString += '\nCalibrating T'+str(tool)+':C'+str(rep)+': '
        
        # Space coordinates
        self.space_coordinates = []
        self.camera_coordinates = []
        self.calibration_moves = 0

        while True:
            (self.xy, self.target, self.tool_coordinates, self.radius) = self.analyzeFrame()
            # analyzeFrame has returned our target coordinates, average its location and process according to state
            self.average_location[0] += self.xy[0]
            self.average_location[1] += self.xy[1]
            
            self.detect_count += 1

            # check if we've reached our number of detections for average positioning
            if self.detect_count >= self.position_iterations:
                # calculate average X Y position from detection
                self.average_location[0] /= self.detect_count
                self.average_location[1] /= self.detect_count
                # round to 3 decimal places
                self.average_location = np.around(self.average_location,3)
                # get another detection validated
                (self.xy, self.target, self.tool_coordinates, self.radius) = self.analyzeFrame()
                
                #### Step 1: camera calibration and transformation matrix calculation
                if self.state == 0:
                    self.parent().debugString += 'Calibrating camera...\n'
                    # Update GUI thread with current status and percentage complete
                    self.status_update.emit('Calibrating camera..')
                    self.message_update.emit('Calibrating rotation.. (10%)')
                    # Save position as previous location
                    self.oldxy = self.xy
                    # Reset space and camera coordinates
                    self.space_coordinates = []
                    self.camera_coordinates = []
                    # save machine coordinates for detected nozzle
                    self.space_coordinates.append( (self.tool_coordinates['X'], self.tool_coordinates['Y']) )
                    # save camera coordinates
                    self.camera_coordinates.append( (self.xy[0],self.xy[1]) )
                    # move carriage for calibration
                    self.offsetX = self.calibrationCoordinates[0][0]
                    self.offsetY = self.calibrationCoordinates[0][1]
                    self.parent().printer.gCode('G91 G1 X' + str(self.offsetX) + ' Y' + str(self.offsetY) +' F3000 G90 ')
                    # Update state tracker to second nozzle calibration move
                    self.state = 1
                    continue
                # Check if camera is still being calibrated
                elif self.state >= 1 and self.state < len(self.calibrationCoordinates):
                    # Update GUI thread with current status and percentage complete
                    self.status_update.emit('Calibrating camera..')
                    self.message_update.emit('Calibrating rotation.. (' + str(self.state*10) + '%)')
                    # check if we've already moved, and calculate mpp value
                    if self.state == 1:
                        self.mpp = np.around(0.5/self.getDistance(self.oldxy[0],self.oldxy[1],self.xy[0],self.xy[1]),4)
                    # save position as previous position
                    self.oldxy = self.xy
                    # save machine coordinates for detected nozzle
                    self.space_coordinates.append( (self.tool_coordinates['X'], self.tool_coordinates['Y']) )
                    # save camera coordinates
                    self.camera_coordinates.append( (self.xy[0],self.xy[1]) )
                    # return carriage to relative center of movement
                    self.offsetX = -1*self.offsetX
                    self.offsetY = -1*self.offsetY
                    self.parent().printer.gCode('G91 G1 X' + str(self.offsetX) + ' Y' + str(self.offsetY) +' F3000 G90 ')
                    # move carriage a random amount in X&Y to collect datapoints for transform matrix
                    self.offsetX = self.calibrationCoordinates[self.state][0]
                    self.offsetY = self.calibrationCoordinates[self.state][1]
                    self.parent().printer.gCode('G91 G1 X' + str(self.offsetX) + ' Y' + str(self.offsetY) +' F3000 G90 ')
                    # increment state tracker to next calibration move
                    self.state += 1
                    continue
                # check if final calibration move has been completed
                elif self.state == len(self.calibrationCoordinates):
                    calibration_time = np.around(time.time() - self.startTime,1)
                    self.parent().debugString += 'Camera calibration completed in ' + str(calibration_time) + ' seconds.\n'
                    self.parent().debugString += 'Millimeters per pixel: ' + str(self.mpp) + '\n\n'
                    print('Millimeters per pixel: ' + str(self.mpp))
                    print('Camera calibration completed in ' + str(calibration_time) + ' seconds.')
                    # Update GUI thread with current status and percentage complete
                    self.message_update.emit('Calibrating rotation.. (100%) - MPP = ' + str(self.mpp))
                    self.status_update.emit('Calibrating T' + str(tool) + ', cycle: ' + str(rep+1) + '/' + str(self.cycles))
                    # save position as previous position
                    self.oldxy = self.xy
                    # save machine coordinates for detected nozzle
                    self.space_coordinates.append( (self.tool_coordinates['X'], self.tool_coordinates['Y']) )
                    # save camera coordinates
                    self.camera_coordinates.append( (self.xy[0],self.xy[1]) )
                    # calculate camera transformation matrix
                    self.transform_input = [(self.space_coordinates[i], self.normalize_coords(camera)) for i, camera in enumerate(self.camera_coordinates)]
                    self.transform_matrix, self.transform_residual = self.least_square_mapping(self.transform_input)
                    # define camera center in machine coordinate space
                    self.newCenter = self.transform_matrix.T @ np.array([0, 0, 0, 0, 0, 1])
                    self.guess_position[0]= np.around(self.newCenter[0],3)
                    self.guess_position[1]= np.around(self.newCenter[1],3)
                    self.parent().printer.gCode('G90 G1 X{0:-1.3f} Y{1:-1.3f} F1000 G90 '.format(self.guess_position[0],self.guess_position[1]))
                    # update state tracker to next phase
                    self.state = 200
                    # start tool calibration timer
                    self.startTime = time.time()
                    self.parent().debugString += '\nCalibrating T'+str(tool)+':C'+str(rep)+': '
                    continue
                #### Step 2: nozzle alignment stage
                elif self.state == 200:
                    # Update GUI thread with current status and percentage complete
                    self.message_update.emit('Tool calibration move #' + str(self.calibration_moves))
                    self.status_update.emit('Calibrating T' + str(tool) + ', cycle: ' + str(rep+1) + '/' + str(self.cycles))
                    # increment moves counter
                    self.calibration_moves += 1
                    # nozzle detected, frame rotation is set, start
                    self.cx,self.cy = self.normalize_coords(self.xy)
                    self.v = [self.cx**2, self.cy**2, self.cx*self.cy, self.cx, self.cy, 0]
                    self.offsets = -1*(0.55*self.transform_matrix.T @ self.v)
                    self.offsets[0] = np.around(self.offsets[0],3)
                    self.offsets[1] = np.around(self.offsets[1],3)
                    # Move it a bit
                    self.parent().printer.gCode( 'M564 S1' )
                    self.parent().printer.gCode( 'G91 G1 X{0:-1.3f} Y{1:-1.3f} F1000 G90 '.format(self.offsets[0],self.offsets[1]) )
                    # save position as previous position
                    self.oldxy = self.xy
                    if ( self.offsets[0] == 0.0 and self.offsets[1] == 0.0 ):
                        self.parent().debugString += str(self.calibration_moves) + ' moves.\n'
                        self.parent().printer.gCode( 'G1 F13200' )
                        # Update GUI with progress
                        # calculate final offsets and return results
                        self.tool_offsets = self.parent().printer.getG10ToolOffset(tool)
                        final_x = np.around( (self.cp_coordinates['X'] + self.tool_offsets['X']) - self.tool_coordinates['X'], 3 )
                        final_y = np.around( (self.cp_coordinates['Y'] + self.tool_offsets['Y']) - self.tool_coordinates['Y'], 3 )
                        string_final_x = "{:.3f}".format(final_x)
                        string_final_y = "{:.3f}".format(final_y)
                        # Save offset to output variable
                        # HBHBHBHB
                        _return = {}
                        _return['X'] = final_x
                        _return['Y'] = final_y
                        _return['MPP'] = self.mpp
                        _return['time'] = np.around(time.time() - self.startTime,1)
                        self.message_update.emit('Nozzle calibrated: offset coordinates X' + str(_return['X']) + ' Y' + str(_return['Y']) )
                        self.parent().debugString += 'T' + str(tool) + ', cycle ' + str(rep+1) + ' completed in ' + str(_return['time']) + ' seconds.\n'
                        print('T' + str(tool) + ', cycle ' + str(rep+1) + ' completed in ' + str(_return['time']) + ' seconds.')
                        self.message_update.emit('T' + str(tool) + ', cycle ' + str(rep+1) + ' completed in ' + str(_return['time']) + ' seconds.')
                        self.parent().printer.gCode( 'G1 F13200' )

                        self.parent().debugString += 'G10 P' + str(tool) + ' X' + string_final_x + ' Y' + string_final_y + '\n'
                        x_tableitem = QTableWidgetItem(string_final_x)
                        x_tableitem.setBackground(QColor(100,255,100,255))
                        y_tableitem = QTableWidgetItem(string_final_y)
                        y_tableitem.setBackground(QColor(100,255,100,255))
                        self.parent().offsets_table.setItem(tool,0,x_tableitem)
                        self.parent().offsets_table.setItem(tool,1,y_tableitem)
                        self.result_update.emit({
                            'tool': str(tool),
                            'cycle': str(rep),
                            'mpp': str(self.mpp),
                            'X': string_final_x,
                            'Y': string_final_y
                        })
                        return(_return, self.transform_matrix, self.mpp)
                    else:
                        self.state = 200
                        continue
                self.avg = [0,0]
                self.location = {'X':0,'Y':0}
                self.count = 0

    def normalize_coords(self,coords):
        xdim, ydim = camera_width, camera_height
        return (coords[0] / xdim - 0.5, coords[1] / ydim - 0.5)

    def least_square_mapping(self,calibration_points):
        # Compute a 2x2 map from displacement vectors in screen space to real space.
        n = len(calibration_points)
        real_coords, pixel_coords = np.empty((n,2)),np.empty((n,2))
        for i, (r,p) in enumerate(calibration_points):
            real_coords[i] = r
            pixel_coords[i] = p
        x,y = pixel_coords[:,0],pixel_coords[:,1]
        A = np.vstack([x**2,y**2,x * y, x,y,np.ones(n)]).T
        transform = np.linalg.lstsq(A, real_coords, rcond = None)
        return transform[0], transform[1].mean()

    def getDistance(self, x1, y1, x0, y0 ):
        x1_float = float(x1)
        x0_float = float(x0)
        y1_float = float(y1)
        y0_float = float(y0)
        x_dist = (x1_float - x0_float) ** 2
        y_dist = (y1_float - y0_float) ** 2
        retVal = np.sqrt((x_dist + y_dist))
        return np.around(retVal,3)

    def stop(self):
        self._running = False
        self.detection_on = False
        try:
            tempCoords = self.printer.getCoords()
            if self.printer.isIdle():
                self.parent().printer.gCode('T-1')
                self.parent().printer.gCode('G1 X' + str(tempCoords['X']) + ' Y' + str(tempCoords['Y']))
                while self.parent().printer.getStatus() not in 'idle':
                    time.sleep(1)
        except: None
        self.cap.release()
        self.exit()

    def createDetector(self):
        # Setup SimpleBlobDetector parameters.
        params = cv2.SimpleBlobDetector_Params()
        # Thresholds
        params.minThreshold = self.detect_th1
        params.maxThreshold = self.detect_th2
        params.thresholdStep = self.detect_thstep

        # Area
        params.filterByArea = True         # Filter by Area.
        params.minArea = self.detect_minArea

        # Circularity
        params.filterByCircularity = True  # Filter by Circularity
        params.minCircularity = self.detect_minCircularity
        params.maxCircularity= 1

        # Convexity
        params.filterByConvexity = True    # Filter by Convexity
        params.minConvexity = 0.3
        params.maxConvexity = 1

        # Inertia
        params.filterByInertia = True      # Filter by Inertia
        params.minInertiaRatio = 0.3

        # create detector
        self.detector = cv2.SimpleBlobDetector_create(params)

    def adjust_gamma(self, image, gamma=1.2):
        # build a lookup table mapping the pixel values [0, 255] to
        # their adjusted gamma values
        invGamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** invGamma) * 255
            for i in np.arange(0, 256)]).astype('uint8')
        # apply gamma correction using the lookup table
        return cv2.LUT(image, table)

    def putText(self, frame,text,color=(0, 0, 255),offsetx=0,offsety=0,stroke=1):  # Offsets are in character box size in pixels. 
        if (text == 'timestamp'): text = datetime.datetime.now().strftime('%m-%d-%Y %H:%M:%S')
        fontScale = 1
        if (frame.shape[1] > 640): fontScale = stroke = 2
        if (frame.shape[1] < 640):
            fontScale = 0.8
            stroke = 1
        offpix = cv2.getTextSize('A',   cv2.FONT_HERSHEY_SIMPLEX ,fontScale, stroke)
        textpix = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX ,fontScale, stroke)
        offsety=max(offsety, (-frame.shape[0]/2 + offpix[0][1])/offpix[0][1]) # Let offsety -99 be top row
        offsetx=max(offsetx, (-frame.shape[1]/2 + offpix[0][0])/offpix[0][0]) # Let offsetx -99 be left edge
        offsety=min(offsety,  (frame.shape[0]/2 - offpix[0][1])/offpix[0][1]) # Let offsety  99 be bottom row. 
        offsetx=min(offsetx,  (frame.shape[1]/2 - offpix[0][0])/offpix[0][0]) # Let offsetx  99 be right edge. 
        cv2.putText(frame, text, 
            (int(offsetx * offpix[0][0]) + int(frame.shape[1]/2) - int(textpix[0][0]/2)
            ,int(offsety * offpix[0][1]) + int(frame.shape[0]/2) + int(textpix[0][1]/2)),
            cv2.FONT_HERSHEY_SIMPLEX, fontScale, color, stroke)
        return(frame)

    def changeVideoSrc(self, newSrc=-1):
        self.cap.release()
        video_src = newSrc
        # Start Video feed
        self.cap.open(video_src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
        #self.cap.set(cv2.CAP_PROP_FPS,25)
        self.brightness_default = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
        self.contrast_default = self.cap.get(cv2.CAP_PROP_CONTRAST)
        self.saturation_default = self.cap.get(cv2.CAP_PROP_SATURATION)
        self.hue_default = self.cap.get(cv2.CAP_PROP_HUE)

        self.ret, self.cv_img = self.cap.read()
        if self.ret:
            local_img = self.cv_img
            self.change_pixmap_signal.emit(local_img)
        else:
            self.cap.open(video_src)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
            #self.cap.set(cv2.CAP_PROP_FPS,25)
            self.ret, self.cv_img = self.cap.read()
            local_img = self.cv_img
            self.change_pixmap_signal.emit(local_img)

class App(QMainWindow):
    cp_coords = {}
    numTools = 0
    current_frame = np.ndarray
    mutex = QMutex()
    debugString = ''
    calibrationResults = []

    def __init__(self, parent=None):
        super().__init__()
        self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
        self.setWindowTitle('TAMV')
        self.setWindowIcon(QIcon('jubilee.png'))
        self.detect_th1 = 5
        self.detect_th2 = 200
        global display_width, display_height
        screen = QDesktopWidget().availableGeometry()
        self.small_display = False
        # HANDLE DIFFERENT DISPLAY SIZES
        # 800x600 display - fullscreen app
        if int(screen.width()) >= 800 and int(screen.height()) >= 550 and int(screen.height() < 600):
            self.small_display = True
            print('800x600 desktop detected')
            display_width = 512
            display_height = 384
            self.setWindowFlag(Qt.FramelessWindowHint)
            self.showFullScreen()
            self.setGeometry(0,0,700,500)
            app_screen = self.frameGeometry()
        # 848x480 display - fullscreen app
        elif int(screen.width()) >= 800 and int(screen.height()) < 550:
            self.small_display = True
            print('848x480 desktop detected')
            display_width = 448
            display_height = 336
            self.setWindowFlag(Qt.FramelessWindowHint)
            self.showFullScreen()
            self.setGeometry(0,0,700,400)
            app_screen = self.frameGeometry()
        # larger displays - normal window
        else:
            self.small_display = False
            display_width = 640
            display_height = 480
            self.setGeometry(QStyle.alignedRect(Qt.LeftToRight,Qt.AlignHCenter,QSize(800,600),screen))
            app_screen = self.frameGeometry()
            app_screen.moveCenter(screen.center())
            self.move(app_screen.topLeft())
        # SET UP STYLESHEETS FOR GUI ELEMENTS
        self.setStyleSheet(
            '\
            QPushButton {\
                border: 1px solid #adadad;\
                border-style: outset;\
                border-radius: 4px;\
                font: 14px;\
                padding: 6px;\
            }\
            QPushButton:hover,QPushButton:enabled:hover,QPushButton:enabled:!checked:hover {\
                background-color: #27ae60;\
                border: 1px solid #aaaaaa;\
            }\
            QPushButton:pressed,QPushButton:enabled:pressed,QPushButton:enabled:checked {\
                background-color: #ae2776;\
                border: 1px solid #aaaaaa;\
            }\
            QPushButton:enabled {\
                background-color: green;\
                color: white;\
            }\
            QPushButton#debug,QMessageBox > #debug {\
                background-color: blue;\
                color: white;\
            }\
            QPushButton#debug:hover, QMessageBox > QAbstractButton#debug:hover {\
                background-color: green;\
                color: white;\
            }\
            QPushButton#debug:pressed, QMessageBox > QAbstractButton#debug:pressed {\
                background-color: #ae2776;\
                border-style: inset;\
                color: white;\
            }\
            QPushButton#active, QMessageBox > QAbstractButton#active {\
                background-color: green;\
                color: white;\
            }\
            QPushButton#active:pressed,QMessageBox > QAbstractButton#active:pressed {\
                background-color: #ae2776;\
            }\
            QPushButton#terminate {\
                background-color: red;\
                color: white;\
            }\
            QPushButton#terminate:pressed {\
                background-color: #c0392b;\
            }\
            QPushButton:disabled, QPushButton#terminate:disabled {\
                background-color: #cccccc;\
                color: #999999;\
            }\
            QInputDialog QDialogButtonBox > QPushButton:enabled, QDialog QPushButton:enabled,QPushButton[checkable="true"]:enabled {\
                background-color: none;\
                color: black;\
                border: 1px solid #adadad;\
                border-style: outset;\
                border-radius: 4px;\
                font: 14px;\
                padding: 6px;\
            }\
            QPushButton:enabled:checked {\
                background-color: #ae2776;\
                border: 1px solid #aaaaaa;\
            }\
            QInputDialog QDialogButtonBox > QPushButton:pressed, QDialog QPushButton:pressed {\
                background-color: #ae2776;\
            }\
            QInputDialog QDialogButtonBox > QPushButton:hover:!pressed, QDialog QPushButton:hover:!pressed {\
                background-color: #27ae60;\
            }\
            '
        )
        # LOAD USER SAVED PARAMETERS OR CREATE DEFAULTS
        self.loadUserParameters()
        # GUI ELEMENTS DEFINITION
        # Menubar
        #small_display requirement causes crash on 7 inch rpi displays
        #Due to missing self.analysisMenu
        #if not self.small_display:
        self._createActions()
        self._createMenuBar()
        self._connectActions()
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        # create the label that holds the image
        self.image_label = OverlayLabel()
        self.image_label.setFixedSize( display_width, display_height )
        pixmap = QPixmap( display_width, display_height )
        self.image_label.setPixmap(pixmap)
        # create a status bar
        self.statusBar = QStatusBar()
        self.statusBar.showMessage('Loading up video feed and libraries..',5000)
        self.setStatusBar( self.statusBar )
        # CP location on statusbar
        self.cp_label = QLabel('<b>CP:</b> <i>undef</i>')
        self.statusBar.addPermanentWidget(self.cp_label)
        self.cp_label.setStyleSheet(style_red)
        # Connection status on statusbar
        self.connection_status = QLabel('Disconnected')
        self.connection_status.setStyleSheet(style_red)
        self.statusBar.addPermanentWidget(self.connection_status)
        # BUTTONS
        # Connect
        self.connection_button = QPushButton('Connect..')
        self.connection_button.setToolTip('Connect to a Duet machine..')
        self.connection_button.clicked.connect(self.connectToPrinter)
        self.connection_button.setFixedWidth(170)
        # Disconnect
        self.disconnection_button = QPushButton('STOP / DISCONNECT')
        self.disconnection_button.setToolTip('End current operation,\nunload tools, and return carriage to CP\nthen disconnect.')
        self.disconnection_button.clicked.connect(self.disconnectFromPrinter)
        self.disconnection_button.setFixedWidth(170)
        self.disconnection_button.setObjectName('terminate')
        self.disconnection_button.setDisabled(True)
        # Controlled point
        self.cp_button = QPushButton('Set Controlled Point..')
        self.cp_button.setToolTip('Define your origin point\nto calculate all tool offsets from.')
        self.cp_button.clicked.connect(self.controlledPoint)
        self.cp_button.setFixedWidth(170)
        #self.cp_button.setStyleSheet(style_disabled)
        self.cp_button.setDisabled(True)
        #Threshold setter
        ###############################################
        # #Min Threshold slider
        self.min_thslider = QSlider(Qt.Horizontal)
        self.min_thslider.setMinimum(0)
        self.min_thslider.setValue(int(self.detect_th1))
        self.min_thslider.valueChanged.connect(self.changeThresholdSlider)
        self.min_thslider.setTickPosition(QSlider.TicksBelow)
        self.min_thslider.setTickInterval(5)
        self.min_thslider_label = QLabel(str(int(self.detect_th1)))
        self.min_thslider_label.setVisible(False)
        self.min_thslider.setVisible(False)

        # #Max Threshold slider
        self.max_thslider = QSlider(Qt.Horizontal)
        self.max_thslider.setMinimum(int(self.min_thslider.value()))
        self.max_thslider.setMaximum(255)
        self.max_thslider.setValue(int(self.detect_th2))
        self.max_thslider.valueChanged.connect(self.changeThresholdSlider)
        self.max_thslider.setTickPosition(QSlider.TicksBelow)
        self.max_thslider.setTickInterval(5)
        self.max_thslider_label = QLabel(str(int(self.detect_th2)))
        self.max_thslider_label.setVisible(False)
        self.max_thslider.setVisible(False)
        self.min_thslider.setMaximum(self.max_thslider.value())
        # Thresholdset button
        self.set_thres_button = QPushButton('Set Binary Threshold limit')
        self.set_thres_button.setToolTip('Define pixel brightness thesholds for finding circle borders')
        self.set_thres_button.clicked.connect(self.changeThreshold)
        ###############################################
        
        # Calibration
        self.calibration_button = QPushButton('Start Tool Alignment')
        self.calibration_button.setToolTip('Start alignment process.\nMAKE SURE YOUR CARRIAGE IS CLEAR TO MOVE ABOUT WITHOUT COLLISIONS!')
        self.calibration_button.clicked.connect(self.runCalibration)
        #self.calibration_button.setStyleSheet(style_disabled)
        self.calibration_button.setDisabled(True)
        self.calibration_button.setFixedWidth(170)
        # Jog Panel
        self.jogpanel_button = QPushButton('Jog Panel')
        self.jogpanel_button.setToolTip('Open a control panel to move carriage.')
        self.jogpanel_button.clicked.connect(self.displayJogPanel)
        self.jogpanel_button.setDisabled(True)
        self.jogpanel_button.setFixedWidth(170)
        # Debug Info
        self.debug_button = QPushButton('Debug Information')
        self.debug_button.setToolTip('Display current debug info for troubleshooting\nand to display final G10 commands')
        self.debug_button.clicked.connect(self.displayDebug)
        self.debug_button.setFixedWidth(170)
        self.debug_button.setObjectName('debug')
        # Exit
        self.exit_button = QPushButton('Quit')
        self.exit_button.setToolTip('Unload tools, disconnect, and quit TAMV.')
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setFixedWidth(170)
        
        # OTHER ELEMENTS
        # Repeat spinbox
        self.repeat_label = QLabel('Cycles: ')
        self.repeat_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.repeatSpinBox = QSpinBox()
        self.repeatSpinBox.setValue(1)
        self.repeatSpinBox.setMinimum(1)
        self.repeatSpinBox.setSingleStep(1)
        self.repeatSpinBox.setDisabled(True)
        # Offsets table
        self.offsets_box = QGroupBox("Tool Offsets")
        self.offsets_box.setMaximumWidth(170)
        self.offsets_table = QTableWidget()
        self.offsets_table.setColumnCount(2)
        self.offsets_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.offsets_table.setColumnWidth(0,50)
        self.offsets_table.setColumnWidth(1,50)
        self.offsets_table.setHorizontalHeaderItem(0, QTableWidgetItem("X"))
        self.offsets_table.setHorizontalHeaderItem(1, QTableWidgetItem("Y"))
        self.offsets_table.resizeRowsToContents()
        vbox = QVBoxLayout()
        vbox.setSpacing(1)
        self.offsets_box.setLayout(vbox)
        vbox.addWidget(self.offsets_table)
        self.offsets_box.setVisible(False)
        # Tool buttons table
        self.toolBoxLayout = QHBoxLayout()
        self.toolBoxLayout.setSpacing(1)
        self.toolBox = QGroupBox()
        self.toolBoxLayout.setContentsMargins(0,0,0,0)
        self.toolBox.setLayout(self.toolBoxLayout)
        self.toolBox.setVisible(False)
        self.toolButtons = []
        # Xray checkbox
        self.xray_box = QCheckBox('X-ray')
        self.xray_box.setChecked(False)
        self.xray_box.stateChanged.connect(self.toggle_xray)
        self.xray_box.setDisabled(True)
        self.xray_box.setVisible(False)
        # Loose checkbox
        self.loose_box = QCheckBox('Loose detection')
        self.loose_box.setChecked(False)
        self.loose_box.stateChanged.connect(self.toggle_loose)
        self.loose_box.setDisabled(True)
        self.loose_box.setVisible(False)
        # Invert checkbox
        self.invert_box = QCheckBox('Invert intensities')
        self.invert_box.setChecked(False)
        self.invert_box.stateChanged.connect(self.toggle_invert)
        self.invert_box.setDisabled(True)
        self.invert_box.setVisible(False)
        # Detection checkbox
        self.detect_box = QCheckBox('Detect ON')
        self.detect_box.setChecked(False)
        self.detect_box.stateChanged.connect(self.toggle_detect)
        # create a grid box layout
        grid = QGridLayout()
        grid.setSpacing(3)
        # add elements to grid
        # FIRST ROW
        grid.addWidget(self.connection_button,1,1,Qt.AlignLeft)
        grid.addWidget(self.detect_box,1,2,1,1)
        grid.addWidget(self.xray_box,1,3,1,1)
        grid.addWidget(self.loose_box,1,4,1,1)
        grid.addWidget(self.invert_box,1,5,1,1)
        grid.addWidget(self.toolBox,1,6,1,1)
        grid.addWidget(self.disconnection_button,1,7,1,-1,Qt.AlignLeft)
        # SECOND ROW
        grid.addWidget(self.min_thslider,2,1,1,2)
        grid.addWidget(self.min_thslider_label,2,3,1,1)
        grid.addWidget(self.max_thslider,2,4,1,2)
        grid.addWidget(self.max_thslider_label,2,6,1,1)
        grid.addWidget(self.set_thres_button,2,7,1,1)
        ####
        # THIRD ROW
        # main image viewer
        grid.addWidget(self.image_label,3,1,4,6)
        grid.addWidget(self.jogpanel_button,3,7,1,1)
        grid.addWidget(self.offsets_box,4,7,1,1)
        if self.small_display:
            grid.addWidget(self.exit_button,5,7,1,1)
        grid.addWidget(self.debug_button,6,7,1,1)
        # FOURTH ROW
        grid.addWidget(self.cp_button,7,1,1,1)
        grid.addWidget(self.calibration_button,7,2,1,1)
        grid.addWidget(self.repeat_label,7,3,1,1)
        grid.addWidget(self.repeatSpinBox,7,4,1,1)
        # set the grid layout as the widgets layout
        self.centralWidget.setLayout(grid)
        # start video feed
        self.startVideo()
        # flag to draw circle
        self.crosshair = False


    def changeThresholdSlider(self):
        self.min_thslider_label.setText(str(int(self.min_thslider.value())))
        self.max_thslider_label.setText(str(int(self.max_thslider.value())))

                                                
    def changeThreshold(self):
        if(self.detect_th1 != int(self.min_thslider.value()) or self.detect_th2 != int(self.max_thslider.value())):
            self.detect_th1 = int(self.min_thslider.value())
            self.detect_th2 = int(self.max_thslider.value())
            self.min_thslider.setMaximum(int(self.max_thslider.value()))
            self.max_thslider.setMinimum(int(self.min_thslider.value()))
            self.statusBar.showMessage(f"Binary thresholds change to: {self.detect_th1}, {self.detect_th2}.")
            self.detector_changed = True
        
    def toggle_detect(self):
        self.video_thread.display_crosshair = not self.video_thread.display_crosshair
        self.video_thread.detection_on = not self.video_thread.detection_on
        if self.video_thread.detection_on:
            self.xray_box.setDisabled(False)
            self.xray_box.setVisible(True)
            self.loose_box.setDisabled(False)
            self.loose_box.setVisible(True)
            self.invert_box.setDisabled(False)
            self.invert_box.setVisible(True)
            self.set_thres_button.setDisabled(False)
            self.set_thres_button.setVisible(True)
            self.min_thslider.setVisible(True)
            self.max_thslider.setVisible(True)
            self.min_thslider_label.setVisible(True)
            self.max_thslider_label.setVisible(True)
        else:
            self.xray_box.setDisabled(True)
            self.xray_box.setVisible(False)
            self.loose_box.setDisabled(True)
            self.loose_box.setVisible(False)
            self.invert_box.setDisabled(False)
            self.invert_box.setVisible(True)
            self.set_thres_button.setDisabled(True)
            self.set_thres_button.setVisible(False)
            self.min_thslider.setVisible(False)
            self.max_thslider.setVisible(False)
            self.min_thslider_label.setVisible(False)
            self.max_thslider_label.setVisible(False)
            self.updateStatusbar('Detection: OFF')

    def cleanPrinterURL(self, inputString='http://localhost'):
        _errCode = 0
        _errMsg = ''
        _printerURL = 'http://localhost'
        from urllib.parse import urlparse
        u = urlparse(inputString)
        scheme = u[0]
        netlocation = u[1]
        if len(scheme) < 4 or scheme.lower() not in ['http']:
            _errCode = 1
            _errMsg = 'Invalid scheme. Please only use http connections.'
        elif len(netlocation) < 1:
            _errCode = 2
            _errMsg = 'Invalid IP/network address.'
        elif scheme.lower() in ['https']:
            _errCode = 3
            _errMsg = 'Cannot use https connections for Duet controllers'
        else:
            _printerURL = scheme + '://' + netlocation
        return( _errCode, _errMsg, _printerURL )

    def loadUserParameters(self):
        global camera_width, camera_height, video_src
        try:
            with open('settings.json','r') as inputfile:
                options = json.load(inputfile)
            camera_settings = options['camera'][0]
            camera_height = int( camera_settings['display_height'] )
            camera_width = int( camera_settings['display_width'] )
            video_src = camera_settings['video_src']
            if len(str(video_src)) == 1: video_src = int(video_src)
            printer_settings = options['printer'][0]
            tempURL = printer_settings['address']
            ( _errCode, _errMsg, self.printerURL ) = self.cleanPrinterURL(tempURL)
            if _errCode > 0:
                # invalid input
                print('Invalid printer URL detected in settings.json!')
                print('Defaulting to \"http://localhost\"...')
                self.printerURL = 'http://localhost'
        except FileNotFoundError:
            # create parameter file with standard parameters
            options = {}
            options['camera'] = []
            options['camera'].append( {
                'video_src': 0,
                'display_width': '640',
                'display_height': '480'
            } )
            options['printer'] = []
            options['printer'].append( {
                'address': 'http://localhost',
                'name': 'Hermoine'
            } )
            try:
                camera_width = 640
                camera_height = 480
                video_src = 1
                with open('settings.json','w') as outputfile:
                    json.dump(options, outputfile)
            except Exception as e1:
                print('Error writing user settings file.')
                print(e1)

    def saveUserParameters(self, cameraSrc=-2):
        global camera_width, camera_height, video_src
        cameraSrc = int(cameraSrc)
        try:
            if cameraSrc > -2:
                video_src = cameraSrc
            options = {}
            options['camera'] = []
            options['camera'].append( {
                'video_src': video_src,
                'display_width': camera_width,
                'display_height': camera_height
            } )
            options['printer'] = []
            options['printer'].append( {
                'address': self.printerURL,
                'name': 'Default printer'
            } )
            with open('settings.json','w') as outputfile:
                json.dump(options, outputfile)
        except Exception as e1:
            print('Error saving user settings file.')
            print(e1)
        if int(video_src) != cameraSrc:
            self.video_thread.changeVideoSrc(newSrc=cameraSrc)
        self.updateStatusbar('Current profile saved to settings.json')

    def _createMenuBar(self):
        menuBar = self.menuBar()
        # Creating menus using a QMenu object
        fileMenu = QMenu('&File', self)
        menuBar.addMenu(fileMenu)
        fileMenu.addAction(self.debugAction)
        fileMenu.addAction(self.cameraAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.saveAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.quitAction)

        self.analysisMenu = QMenu('&Analyze',self)
        menuBar.addMenu(self.analysisMenu)
        self.analysisMenu.addAction(self.graphAction)
        self.analysisMenu.addAction(self.exportAction)
        self.analysisMenu.setDisabled(True)

    def _createActions(self):
        # Creating action using the first constructor
        self.debugAction = QAction(self)
        self.debugAction.setText('&Debug info')
        self.cameraAction = QAction(self)
        self.cameraAction.setText('&Camera settings')
        self.quitAction = QAction(self)
        self.quitAction.setText('&Quit')
        self.saveAction = QAction(self)
        self.saveAction.setText('&Save current settings')
        self.graphAction = QAction(self)
        self.graphAction.setText('&Graph calibration data..')
        self.exportAction = QAction(self)
        self.exportAction.setText('&Export to output.json')

    def _connectActions(self):
        # Connect File actions
        self.debugAction.triggered.connect(self.displayDebug)
        self.cameraAction.triggered.connect(self.displayCameraSettings)
        self.quitAction.triggered.connect(self.close)
        self.saveAction.triggered.connect(self.saveUserParameters)

        self.graphAction.triggered.connect(lambda: self.analyzeResults(graph=True))
        self.exportAction.triggered.connect(lambda: self.analyzeResults(export=True))

    def displayCameraSettings(self):
        self.camera_dialog = CameraSettingsDialog(parent=self)
        self.camera_dialog.exec_()

    def displayDebug(self):
        dbg = DebugDialog(parent=self,message=self.debugString)
        if dbg.exec_():
            None

    def displayJogPanel(self):
        try:
            local_status = self.printer.getStatus()
            if local_status == 'idle':
                jogPanel = CPDialog(parent=self,summary='Control printer movement using this panel.',title='Jog Control')
                if jogPanel.exec_():
                    None
        except Exception as e1: self.statusBar.showMessage('Printer is not available or is busy. ')

    def startVideo(self):
        # create the video capture thread
        self.video_thread = CalibrateNozzles(parent=self,numTools=0, cycles=1,minArea=default_minArea, align=False)
        # connect its signal to the update_image slot
        # connect its signal to the update_image slot
        self.video_thread.detection_error.connect(self.updateStatusbar)
        self.video_thread.status_update.connect(self.updateStatusbar)
        self.video_thread.message_update.connect(self.updateMessagebar)
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.calibration_complete.connect(self.applyCalibration)
        self.video_thread.result_update.connect(self.addCalibrationResult)

        # start the thread
        self.video_thread.start()

    def stopVideo(self):
        try:
            if self.video_thread.isRunning():
                self.video_thread.stop()
        except Exception as vs2:
            self.updateStatusbar('ERROR: cannot stop video')
            print('ERROR: cannot stop video')
            print(vs2)

    def closeEvent(self, event):
        try:
            if self.printer.isIdle():
                tempCoords = self.printer.getCoords()
                self.printer.gCode('T-1')
                self.printer.gCode('G1 X' + str(tempCoords['X']) + ' Y' + str(tempCoords['Y']))
        except Exception as ce1: None # no printer connected usually.
        print()
        print('Thank you for using TAMV!')
        print('Check out www.jubilee3d.com')
        event.accept()

    def connectToPrinter(self):
        # temporarily suspend GUI and display status message
        self.image_label.setText('Waiting to connect..')
        self.updateStatusbar('Please enter machine IP address or name prefixed with http(s)://')
        self.connection_button.setDisabled(True)
        self.disconnection_button.setDisabled(True)
        self.calibration_button.setDisabled(True)
        self.cp_button.setDisabled(True)
        self.jogpanel_button.setDisabled(True)
        self.offsets_box.setVisible(False)
        self.connection_status.setText('Connecting..')
        self.connection_status.setStyleSheet(style_orange)
        self.cp_label.setText('<b>CP:</b> <i>undef</i>')
        self.cp_label.setStyleSheet(style_orange)
        self.repeatSpinBox.setDisabled(True)
        self.xray_box.setDisabled(True)
        self.xray_box.setChecked(False)
        self.xray_box.setVisible(False)
        self.loose_box.setDisabled(True)
        self.loose_box.setChecked(False)
        self.loose_box.setVisible(False)
        self.invert_box.setDisabled(True)
        self.invert_box.setChecked(False)
        self.invert_box.setVisible(False)
        self.repaint()
        try:
            # check if printerURL has already been defined (user reconnecting)
            if len(self.printerURL) > 0:
                None
        except Exception:
            # printerURL initalization to defaults
            self.printerURL = 'http://localhost'
        # Prompt user for machine connection address
        text, ok = QInputDialog.getText(self, 'Machine URL','Machine IP address or hostname: ', QLineEdit.Normal, self.printerURL)
        # Handle clicking OK/Connect
        if ok and text != '' and len(text) > 5:
            ( _errCode, _errMsg, tempURL ) = self.cleanPrinterURL(text)
            while _errCode != 0:
                # Invalid URL detected, pop-up window to correct this
                text, ok = QInputDialog.getText(self, 'Machine URL', _errMsg + '\nMachine IP address or hostname: ', QLineEdit.Normal, text)
                if ok:
                    ( _errCode, _errMsg, tempURL ) = self.cleanPrinterURL(text)
                else:
                    self.updateStatusbar('Connection request cancelled.')
                    self.resetConnectInterface()
                    return
            # input has been parsed and is clean, proceed
            self.printerURL = tempURL
        # Handle clicking cancel
        elif not ok:
            self.updateStatusbar('Connection request cancelled.')
            self.resetConnectInterface()
            return
        # Handle invalid input
        elif len(text) < 6 or text[:4] not in ['http']:
            self.updateStatusbar('Invalid IP address or hostname: \"' + text +'\". Add http(s):// to try again.')
            self.resetConnectInterface()
            return
        # Update user with new state
        self.statusBar.showMessage('Attempting to connect to: ' + self.printerURL )
        # Attempt connecting to the Duet controller
        try:
            self.printer = DWA.DuetWebAPI(self.printerURL)
            if not self.printer.printerType():
                # connection failed for some reason
                self.updateStatusbar('Device at '+self.printerURL+' either did not respond or is not a Duet V2 or V3 printer.')
                self.resetConnectInterface()
                return
            else:
                # connection succeeded, update objects accordingly
                self._connected_flag = True
                self.num_tools = self.printer.getNumTools()
                self.video_thread.numTools = self.num_tools
                # UPDATE OFFSET INFORMATION
                self.offsets_box.setVisible(True)
                self.offsets_table.setRowCount(self.num_tools)
                for i in range(self.num_tools):
                    current_tool = self.printer.getG10ToolOffset(i)
                    offset_x = "{:.3f}".format(current_tool['X'])
                    offset_y = "{:.3f}".format(current_tool['Y'])
                    x_tableitem = QTableWidgetItem(offset_x)
                    y_tableitem = QTableWidgetItem(offset_y)
                    x_tableitem.setBackground(QColor(255,255,255,255))
                    y_tableitem.setBackground(QColor(255,255,255,255))
                    self.offsets_table.setVerticalHeaderItem(i,QTableWidgetItem('T'+str(i)))
                    self.offsets_table.setItem(i,0,x_tableitem)
                    self.offsets_table.setItem(i,1,y_tableitem)
                    # add tool buttons
                    toolButton = QPushButton('T'+str(i))
                    toolButton.setToolTip('Fetch T' + str(i) + ' to current machine position.')
                    self.toolButtons.append(toolButton)
        except Exception as conn1:
            self.updateStatusbar('Cannot connect to: ' + self.printerURL )
            print('Duet Connection exception: ', conn1)
            self.resetConnectInterface()
            return
        # Get active tool
        _active = self.printer.getCurrentTool()
        # Display toolbox
        for i,button in enumerate(self.toolButtons):
            button.setCheckable(True)
            if int(_active) == i:
                button.setChecked(True)
            else: 
                button.setChecked(False)
            button.clicked.connect(self.callTool)
            self.toolBoxLayout.addWidget(button)
        self.toolBox.setVisible(True)
        # Connection succeeded, update GUI first
        self.updateStatusbar('Connected to a Duet V'+str(self.printer.printerType()))
        self.connection_button.setText('Online: ' + self.printerURL[self.printerURL.rfind('/')+1:])
        self.statusBar.showMessage('Connected to printer at ' + self.printerURL, 5000)
        self.connection_status.setText('Connected.')
        self.image_label.setText('Set your Controlled Point to continue.')
        # enable/disable buttons
        self.connection_button.setDisabled(True)
        self.calibration_button.setDisabled(True)
        self.disconnection_button.setDisabled(False)
        self.cp_button.setDisabled(False)
        self.jogpanel_button.setDisabled(False)
        self.analysisMenu.setDisabled(True)
        self.min_thslider_label.setVisible(True)
        self.min_thslider.setVisible(True)
        self.max_thslider_label.setVisible(True)
        self.max_thslider.setVisible(True)
        self.set_thres_button.setVisible(True)
        # update connection status indicator to green
        self.connection_status.setStyleSheet(style_green)
        self.cp_label.setStyleSheet(style_red)

    def callTool(self):
        # handle scenario where machine is busy and user tries to select a tool.
        if not self.printer.isIdle():
            self.updateStatusbar('Machine is not idle, cannot select tool.')
            return

        # get current active tool
        _active = self.printer.getCurrentTool()
        
        # get requested tool number
        sender = self.sender()

        # update buttons to new status
        for button in self.toolButtons:
            button.setChecked(False)
        self.toolButtons[int(self.sender().text()[1:])].setChecked(True)

        # handle tool already active on printer
        if int(_active) == int(sender.text()[1:]):
            msg = QMessageBox()
            status = msg.question( self, 'Unload ' + sender.text(), 'Unload ' + sender.text() + ' and return carriage to the current position?',QMessageBox.Yes | QMessageBox.No  )
            if status == QMessageBox.Yes:
                self.toolButtons[int(self.sender().text()[1:])].setChecked(False)
                if len(self.cp_coords) > 0:
                    self.printer.gCode('T-1')
                    self.printer.gCode('G1 X' + str(self.cp_coords['X']))
                    self.printer.gCode('G1 Y' + str(self.cp_coords['Y']))
                    self.printer.gCode('G1 Z' + str(self.cp_coords['Z']))
                else:
                    tempCoords = self.printer.getCoords()
                    self.printer.gCode('T-1')
                    self.printer.gCode('G1 X' + str(tempCoords['X']))
                    self.printer.gCode('G1 Y' + str(tempCoords['Y']))
                    self.printer.gCode('G1 Z' + str(tempCoords['Z']))
                # End video threads and restart default thread
                self.video_thread.alignment = False

                # Update GUI for unloading carriage
                self.calibration_button.setDisabled(False)
                self.cp_button.setDisabled(False)
                self.updateMessagebar('Ready.')
                self.updateStatusbar('Ready.')
            else:
                # User cancelled, do nothing
                return
        else:
            # Requested tool is different from active tool
            msg = QMessageBox()
            status = msg.question( self, 'Confirm loading ' + sender.text(), 'Load ' + sender.text() + ' and move to current position?',QMessageBox.Yes | QMessageBox.No  )
            
            if status == QMessageBox.Yes:
                # return carriage to controlled point position
                if len(self.cp_coords) > 0:
                    self.printer.gCode('T-1')
                    self.printer.gCode(sender.text())
                    self.printer.gCode('G1 X' + str(self.cp_coords['X']))
                    self.printer.gCode('G1 Y' + str(self.cp_coords['Y']))
                    self.printer.gCode('G1 Z' + str(self.cp_coords['Z']))
                else:
                    tempCoords = self.printer.getCoords()
                    self.printer.gCode('T-1')
                    self.printer.gCode(self.sender().text())
                    self.printer.gCode('G1 X' + str(tempCoords['X']))
                    self.printer.gCode('G1 Y' + str(tempCoords['Y']))
                    self.printer.gCode('G1 Z' + str(tempCoords['Z']))
                # START DETECTION THREAD HANDLING
                # close camera settings dialog so it doesn't crash
                try:
                    if self.camera_dialog.isVisible():
                        self.camera_dialog.reject()
                except: None
                # update GUI
                self.cp_button.setDisabled(True)
                self.jogpanel_button.setDisabled(False)
                self.calibration_button.setDisabled(True)
                self.repeatSpinBox.setDisabled(True)

            else:
                self.toolButtons[int(self.sender().text()[1:])].setChecked(False)

    def resetConnectInterface(self):
        self.connection_button.setDisabled(False)
        self.disconnection_button.setDisabled(True)
        self.calibration_button.setDisabled(True)
        self.cp_button.setDisabled(True)
        self.jogpanel_button.setDisabled(True)
        self.offsets_box.setVisible(False)
        self.connection_status.setText('Disconnected')
        self.connection_status.setStyleSheet(style_red)
        self.cp_label.setText('<b>CP:</b> <i>undef</i>')
        self.cp_label.setStyleSheet(style_red)
        self.repeatSpinBox.setDisabled(True)
        self.analysisMenu.setDisabled(True)
        self.detect_box.setChecked(False)
        self.detect_box.setDisabled(False)
        self.xray_box.setDisabled(True)
        self.xray_box.setChecked(False)
        self.xray_box.setVisible(False)
        self.loose_box.setDisabled(True)
        self.loose_box.setChecked(False)
        self.loose_box.setVisible(False)
        self.video_thread.detection_on = False
        self.video_thread.loose = False
        self.video_thread.xray = False
        self.video_thread.alignment = False

        index = self.toolBoxLayout.count()-1
        while index >= 0:
            curWidget = self.toolBoxLayout.itemAt(index).widget()
            curWidget.setParent(None)
            index -= 1
        self.toolBox.setVisible(False)
        self.toolButtons = []
        self.repaint()

    def controlledPoint(self):
        # handle scenario where machine is busy and user tries to select a tool.
        if not self.printer.isIdle():
            self.updateStatusbar('Machine is not idle, cannot select tool.')
            return
        # display crosshair on video feed at center of image
        self.crosshair = True
        self.calibration_button.setDisabled(True)

        if len(self.cp_coords) > 0:
            self.printer.gCode('T-1')
            self.printer.gCode('G90 G1 X'+ str(self.cp_coords['X']) + ' Y' + str(self.cp_coords['Y']) + ' Z' + str(self.cp_coords['Z']) )
        dlg = CPDialog(parent=self)
        if dlg.exec_():
            self.cp_coords = self.printer.getCoords()
            self.cp_string = '(' + str(self.cp_coords['X']) + ', ' + str(self.cp_coords['Y']) + ')'
            self.readyToCalibrate()
        else:
            self.statusBar.showMessage('CP Setup cancelled.')
        self.crosshair = False

    def readyToCalibrate(self):
        self.statusBar.showMessage('Controlled Point coordinates saved.',3000)
        self.image_label.setText('Controlled Point set. Click \"Start Tool Alignment\" to calibrate..')
        self.cp_button.setText('Reset CP ')
        self.cp_label.setText('<b>CP:</b> ' + self.cp_string)
        self.cp_label.setStyleSheet(style_green)
        self.detect_box.setChecked(False)
        self.detect_box.setDisabled(False)
        self.detect_box.setVisible(True)
        self.xray_box.setDisabled(True)
        self.xray_box.setChecked(False)
        self.xray_box.setVisible(False)
        self.loose_box.setDisabled(True)
        self.loose_box.setChecked(False)
        self.loose_box.setVisible(False)
        self.invert_box.setDisabled(True)
        self.invert_box.setChecked(False)
        self.invert_box.setVisible(False)
        self.video_thread.detection_on = False
        self.video_thread.loose = False
        self.video_thread.xray = False
        self.video_thread.alignment = False
        self.calibration_button.setDisabled(False)
        self.cp_button.setDisabled(False)
        self.min_thslider_label.setVisible(True)
        self.min_thslider.setVisible(True)
        self.max_thslider_label.setVisible(True)
        self.max_thslider.setVisible(True)
        self.set_thres_button.setVisible(True)


        self.toolBox.setVisible(True)
        self.repeatSpinBox.setDisabled(False)

        if len(self.calibrationResults) > 1:
            self.analysisMenu.setDisabled(False)
        else:
            self.analysisMenu.setDisabled(True)

    def applyCalibration(self):
        # update GUI
        self.readyToCalibrate()
        # close camera settings dialog so it doesn't crash
        try:
            if self.camera_dialog.isVisible():
                self.camera_dialog.reject()
        except: None
        # prompt for user to apply results
        msgBox = QMessageBox(parent=self)
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText('Do you want to save the new offsets to your machine?')
        msgBox.setWindowTitle('Calibration Results')
        yes_button = msgBox.addButton('Apply offsets and save (M500)',QMessageBox.ApplyRole)
        yes_button.setStyleSheet(style_green)
        cancel_button = msgBox.addButton('Apply offsets',QMessageBox.NoRole)
        
        # Update debug string
        self.debugString += '\nCalibration results:\n'
        for result in self.calibrationResults:
            calibrationCode = 'G10 P' + str(result['tool']) + ' X' + str(result['X']) + ' Y' + str(result['Y'])
            self.debugString += calibrationCode + '\n'

        # Prompt user
        returnValue = msgBox.exec()
        if msgBox.clickedButton() == yes_button:
            for result in self.calibrationResults:
                calibrationCode = 'G10 P' + str(result['tool']) + ' X' + str(result['X']) + ' Y' + str(result['Y'])
                self.printer.gCode(calibrationCode)
                self.printer.gCode('M500 P10') # because of Rene.
            self.statusBar.showMessage('Offsets applied and stored using M500.')
            print('Offsets applied and stored using M500.')
        else:
            self.statusBar.showMessage('Temporary offsets applied. You must manually save these offsets.')
        # Clean up threads and detection
        self.video_thread.alignment = False
        self.video_thread.detect_on = False
        self.video_thread.display_crosshair = False
        # run stats
        self.analyzeResults()

    def analyzeResults(self, graph=False, export=False):
        if len(self.calibrationResults) < 1:
            self.updateStatusbar('No calibration data found.')
            return
        if graph or export:
            # get data as 3 dimensional array [tool][axis][datapoints] normalized around mean of each axis
            (numTools, totalRuns, toolData) = self.parseData(self.calibrationResults)
        else:
            # display stats to terminal
            self.stats()
        if graph:
            matplotlib.use('Qt5Agg',force=True)
            # set up color and colormap arrays
            colorMap = ["Greens","Oranges","Blues", "Reds"] #["Blues", "Reds","Greens","Oranges"]
            colors = ['blue','red','green','orange']
            # initiate graph data - 1 tool per column
            # Row 0: scatter plot with standard deviation box
            # Row 1: histogram of X axis data
            # Row 2: histogram of Y axis data
            
            # Set backend (if needed)
            #plt.switch_backend('Qt4Agg')

            fig, axes = plt.subplots(ncols=3,nrows=numTools,constrained_layout=False)

            for i, data in enumerate(toolData):
                # create a color array the length of the number of tools in the data
                color = np.arange(len(data[0]))

                # Axis formatting
                # Major ticks
                axes[i][0].xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
                axes[i][0].yaxis.set_major_formatter(FormatStrFormatter('%.3f'))
                # Minor ticks
                axes[i][0].xaxis.set_minor_formatter(FormatStrFormatter('%.3f'))
                axes[i][0].yaxis.set_minor_formatter(FormatStrFormatter('%.3f'))
                # Draw 0,0 lines
                axes[i][0].axhline()
                axes[i][0].axvline()
                # x&y std deviation box
                x_sigma = np.around(np.std(data[0]),3)
                y_sigma = np.around(np.std(data[1]),3)
                axes[i][0].add_patch(patches.Rectangle((-1*x_sigma,-1*y_sigma), 2*x_sigma, 2*y_sigma, color="green",fill=False, linestyle='dotted'))
                axes[i][0].add_patch(patches.Rectangle((-2*x_sigma,-2*y_sigma), 4*x_sigma, 4*y_sigma, color="red",fill=False, linestyle='-.'))
                
                # scatter plot for tool data
                axes[i][0].scatter(data[0], data[1], c=color, cmap=colorMap[i])
                axes[i][0].autoscale = True
                
                # Histogram data setup
                # Calculate number of bins per axis
                x_intervals = int(np.around(math.sqrt(len(data[0])),0)+1)
                y_intervals = int(np.around(math.sqrt(len(data[1])),0)+1)
                
                # plot histograms
                x_kwargs = dict(alpha=0.5, bins=x_intervals,rwidth=.92, density=True)
                n, bins, hist_patches = axes[i][1].hist([data[0],data[1]],**x_kwargs, color=[colors[0],colors[1]], label=['X','Y'])
                axes[i][2].hist2d(data[0], data[1], bins=x_intervals, cmap='Blues')
                axes[i][1].legend()


                # add a 'best fit' line
                # calculate mean and std deviation per axis
                x_mean = np.mean(data[0])
                y_mean = np.mean(data[1])
                x_sigma = np.around(np.std(data[0]),3)
                y_sigma = np.around(np.std(data[1]),3)
                # calculate function lines for best fit
                x_best = ((1 / (np.sqrt(2 * np.pi) * x_sigma)) *
                    np.exp(-0.5 * (1 / x_sigma * (bins - x_mean))**2))
                y_best = ((1 / (np.sqrt(2 * np.pi) * y_sigma)) *
                    np.exp(-0.5 * (1 / y_sigma * (bins - y_mean))**2))
                # add best fit line to plots
                axes[i][1].plot(bins, x_best, '-.',color=colors[0])
                axes[i][1].plot(bins, y_best, '--',color=colors[1])

                x_count = int(sum( p == True for p in ((data[0] >= (x_mean - x_sigma)) & (data[0] <= (x_mean + x_sigma))) )/len(data[0])*100)
                y_count = int(sum( p == True for p in ((data[1] >= (y_mean - y_sigma)) & (data[1] <= (y_mean + y_sigma))) )/len(data[1])*100)
                # annotate std dev values
                annotation_text = "Xσ: " + str(x_sigma) + " ("+str(x_count) + "%)"
                if x_count < 68:
                    x_count = int(sum( p == True for p in ((data[0] >= (x_mean - 2*x_sigma)) & (data[0] <= (x_mean + 2*x_sigma))) )/len(data[0])*100) 
                    annotation_text += " --> 2σ: " + str(x_count) + "%"
                    if x_count < 95 and x_sigma*2 > 0.1:
                        annotation_text += " -- check axis!"
                    else: annotation_text += " -- OK"
                annotation_text += "\nYσ: " + str(y_sigma) + " ("+str(y_count) + "%)"
                if y_count < 68: 
                    y_count = int(sum( p == True for p in ((data[1] >= (y_mean - 2*y_sigma)) & (data[1] <= (y_mean + 2*y_sigma))) )/len(data[1])*100) 
                    annotation_text += " --> 2σ: " + str(y_count) + "%"
                    if y_count < 95 and y_sigma*2 > 0.1:
                        annotation_text += " -- check axis!"
                    else: annotation_text += " -- OK"
                axes[i][0].annotate(annotation_text, (10,10),xycoords='axes pixels')
                axes[i][0].annotate('σ',(1.1*x_sigma,-1.1*y_sigma),xycoords='data',color='green')
                axes[i][0].annotate('2σ',(1.1*2*x_sigma,-1.1*2*y_sigma),xycoords='data',color='red')
                # # place title for graph
                axes[i][0].set_ylabel("Tool " + str(i) + "\nY")
                axes[i][0].set_xlabel("X")
                axes[i][2].set_ylabel("Y")
                axes[i][2].set_xlabel("X")
                
                if i == 0:
                    axes[i][0].set_title('Scatter Plot')
                    axes[i][1].set_title('Histogram')
                    axes[i][2].set_title('2D Histogram')
            plt.tight_layout()
            figManager = plt.get_current_fig_manager()
            figManager.window.showMaximized()
            plt.ion()
            plt.show()

        if export:
            # export JSON data to file
            try:
                with open('output.json','w') as outputfile:
                    json.dump(self.calibrationResults, outputfile)
            except Exception as e1:
                print('Error exporting data:')
                print(e1)
                self.updateStatusbar('Error exporting data, please check terminal for details.')

    def stats(self):
        ###################################################################################
        # Report on repeated executions
        ###################################################################################
        print('')
        print('Repeatability statistics for '+str(self.cycles)+' repeats:')
        print('+-------------------------------------------------------------------------------------------------------+')
        print('|   |                   X                             |                        Y                        |')
        print('| T |   Avg   |   Max   |   Min   |  StdDev |  Range  |   Avg   |   Max   |   Min   |  StdDev |  Range  |')
        for index in range(self.num_tools):
            # create array of results for current tool
            _rawCalibrationData = [line for line in self.calibrationResults if line['tool'] == str(index)]
            x_array = [float(line['X']) for line in _rawCalibrationData]
            y_array = [float(line['Y']) for line in _rawCalibrationData]
            mpp_value = np.average([float(line['mpp']) for line in _rawCalibrationData])
            cycles = np.max(
                [float(line['cycle']) for line in _rawCalibrationData]
            )
            x_avg = np.average(x_array)
            y_avg = np.average(y_array)
            x_min = np.min(x_array)
            y_min = np.min(y_array)
            x_max = np.max(x_array)
            y_max = np.max(y_array)
            x_std = np.std(x_array)
            y_std = np.std(y_array)
            x_ran = x_max - x_min
            y_ran = y_max - y_min
            print('| {0:1.0f} '.format(index) 
                + '| {0:7.3f} '.format(x_avg)
                + '| {0:7.3f} '.format(x_max)
                + '| {0:7.3f} '.format(x_min)
                + '| {0:7.3f} '.format(x_std)
                + '| {0:7.3f} '.format(x_ran)
                + '| {0:7.3f} '.format(y_avg)
                + '| {0:7.3f} '.format(y_max)
                + '| {0:7.3f} '.format(y_min)
                + '| {0:7.3f} '.format(y_std)
                + '| {0:7.3f} '.format(y_ran)
                + '|'
            )        
        print('+-------------------------------------------------------------------------------------------------------+')
        print('Note: Repeatability cannot be better than one pixel (MPP=' + str(mpp_value) + ').')

    def parseData( self, rawData ):
        # create empty output array
        toolDataResult = []
        # get number of tools
        _numTools = np.max([ int(line['tool']) for line in rawData ]) + 1
        _cycles = np.max([ int(line['cycle']) for line in rawData ])
        
        for i in range(_numTools):
            x = [float(line['X']) for line in rawData if int(line['tool']) == i]
            y = [float(line['Y']) for line in rawData if int(line['tool']) == i]
            # variable to hold return data coordinates per tool formatted as a 2D array [x_value, y_value]
            tempPairs = []

            # calculate stats
            # mean values
            x_mean = np.around(np.mean(x),3)
            y_mean = np.around(np.mean(y),3)
            # median values
            x_median = np.around(np.median(x),3)
            y_median = np.around(np.median(y),3)
            # ranges (max - min per axis)
            x_range = np.around(np.max(x) - np.min(x),3)
            y_range = np.around(np.max(y) - np.min(y),3)
            # standard deviations
            x_sig = np.around(np.std(x),3)
            y_sig = np.around(np.std(y),3)

            # normalize data around mean
            x -= x_mean
            y -= y_mean
            
            # temporary object to append coordinate pairs into return value
            tempPairs.append(x)
            tempPairs.append(y)

            # add data to return object
            toolDataResult.append(tempPairs)
        # return dataset
        return ( _numTools, _cycles, toolDataResult )

    def disconnectFromPrinter(self):
        # temporarily suspend GUI and display status message
        self.image_label.setText('Restoring machine to initial state..')
        self.updateStatusbar('Restoring machine and disconnecting...')
        self.connection_button.setText('Pending..')
        self.connection_button.setDisabled(True)
        self.disconnection_button.setDisabled(True)
        self.calibration_button.setDisabled(True)
        self.cp_button.setDisabled(True)
        self.cp_button.setText('Pending..')
        self.jogpanel_button.setDisabled(True)
        self.offsets_box.setVisible(False)
        self.connection_status.setText('Disconnecting..')
        self.connection_status.setStyleSheet(style_orange)
        self.cp_label.setText('<b>CP:</b> <i>undef</i>')
        self.cp_label.setStyleSheet(style_orange)
        self.repeatSpinBox.setDisabled(True)
        self.xray_box.setDisabled(True)
        self.xray_box.setChecked(False)
        self.loose_box.setDisabled(True)
        self.toolBox.setVisible(False)
        self.min_thslider_label.setVisible(False)
        self.min_thslider.setVisible(False)
        self.max_thslider_label.setVisible(False)
        self.max_thslider.setVisible(False)
        self.set_thres_button.setVisible(False)
        self.repaint()
        # End video threads and restart default thread
        # Clean up threads and detection
        self.video_thread.alignment = False
        self.video_thread.detect_on = False
        self.video_thread.display_crosshair = False
        self.detect_box.setChecked(False)
        self.detect_box.setVisible(True)

        # update status 
        self.updateStatusbar('Unloading tools and disconnecting from machine..')
        # Wait for printer to stop moving and unload tools
        _ret_error = self.printer.gCode('M400')
        if self.printer.isIdle():
            tempCoords = self.printer.getCoords()
            _ret_error += self.printer.gCode('T-1')
            # return carriage to controlled point position
            if len(self.cp_coords) > 0:
                _ret_error += self.printer.gCode('G1 X' + str(self.cp_coords['X']))
                _ret_error += self.printer.gCode('G1 Y' + str(self.cp_coords['Y']))
                _ret_error += self.printer.gCode('G1 Z' + str(self.cp_coords['Z']))
            else:
                _ret_error += self.printer.gCode('G1 X' + str(tempCoords['X']))
                _ret_error += self.printer.gCode('G1 Y' + str(tempCoords['Y']))
                _ret_error += self.printer.gCode('G1 Z' + str(tempCoords['Z']))
        # update status with disconnection state
        if _ret_error == 0:
            self.updateStatusbar('Disconnected.')
            self.image_label.setText('Disconnected.')
        else: 
            # handle unforeseen disconnection error (power loss?)
            self.statusBar.showMessage('Disconnect: error communicating with machine.')
            self.statusBar.setStyleSheet(style_red)
        # Reinitialize printer object
        self.printer = None
        
        # Tools unloaded, reset GUI
        self.image_label.setText('Welcome to TAMV. Enter your printer address and click \"Connect..\" to start.')
        self.connection_button.setText('Connect..')
        self.connection_button.setDisabled(False)
        self.disconnection_button.setDisabled(True)
        self.calibration_button.setDisabled(True)
        self.cp_button.setDisabled(True)
        self.cp_button.setText('Set Controlled Point..')
        self.jogpanel_button.setDisabled(True)
        self.offsets_box.setVisible(False)
        self.connection_status.setText('Disconnected.')
        self.connection_status.setStyleSheet(style_red)
        self.cp_label.setText('<b>CP:</b> <i>undef</i>')
        self.cp_label.setStyleSheet(style_red)
        self.repeatSpinBox.setDisabled(True)
        self.xray_box.setDisabled(True)
        self.loose_box.setDisabled(True)
        self.resetConnectInterface()

    def runCalibration(self):
        # reset debugString
        self.debugString = ''
        # prompt for user to apply results
        msgBox = QMessageBox(parent=self)
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText('Do you want to start automated tool alignment?')
        msgBox.setWindowTitle('Start Calibration')
        yes_button = msgBox.addButton('Start calibration..',QMessageBox.YesRole)
        yes_button.setObjectName('active')
        yes_button.setStyleSheet(style_green)
        no_button = msgBox.addButton('Cancel',QMessageBox.NoRole)

        returnValue = msgBox.exec_()
        if msgBox.clickedButton() == no_button:
            return
        # close camera settings dialog so it doesn't crash
        try:
            if self.camera_dialog.isVisible():
                self.camera_dialog.reject()
        except: None
        # update GUI
        self.cp_button.setDisabled(True)
        self.jogpanel_button.setDisabled(False)
        self.calibration_button.setDisabled(True)
        self.xray_box.setDisabled(False)
        self.xray_box.setChecked(False)
        self.xray_box.setVisible(True)
        self.loose_box.setDisabled(False)
        self.loose_box.setChecked(False)
        self.loose_box.setVisible(True)
        self.invert_box.setDisabled(False)
        self.invert_box.setChecked(False)
        self.invert_box.setVisible(True)
        self.toolBox.setVisible(False)
        self.detect_box.setVisible(False)
        for i in range(self.num_tools):
            current_tool = self.printer.getG10ToolOffset(i)
            x_tableitem = QTableWidgetItem("{:.3f}".format(current_tool['X']))
            y_tableitem = QTableWidgetItem("{:.3f}".format(current_tool['Y']))
            x_tableitem.setBackground(QColor(255,255,255,255))
            y_tableitem.setBackground(QColor(255,255,255,255))
            self.offsets_table.setVerticalHeaderItem(i,QTableWidgetItem('T'+str(i)))
            self.offsets_table.setItem(i,0,x_tableitem)
            self.offsets_table.setItem(i,1,y_tableitem)
        # get number of repeat cycles
        self.repeatSpinBox.setDisabled(True)
        self.cycles = self.repeatSpinBox.value()

        # create the Nozzle detection capture thread
        self.video_thread.display_crosshair = True
        self.video_thread.detection_on = True
        self.video_thread.xray = False
        self.video_thread.loose = False
        self.video_thread.alignment = True

    def toggle_xray(self):
        try:
            self.video_thread.toggleXray()
        except Exception as e1:
            self.updateStatusbar('Detection thread not running.')
            print( 'Detection thread error in XRAY: ')
            print(e1)

    def toggle_loose(self):
        try:
            self.video_thread.toggleLoose()
        except Exception as e1:
            self.updateStatusbar('Detection thread not running.')
            print( 'Detection thread error in LOOSE: ')
            print(e1)

    def toggle_invert(self):
        try:
            self.video_thread.toggleInvert()
        except Exception as e1:
            self.updateStatusbar('Detection thread not running.')
            print( 'Detection thread error in INVERT: ')
            print(e1)

    @pyqtSlot(str)
    def updateStatusbar(self, statusCode ):
        self.statusBar.showMessage(statusCode)

    @pyqtSlot(str)
    def updateMessagebar(self, statusCode ):
        self.image_label.setText(statusCode)

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        #self.mutex.lock()
        self.current_frame = cv_img
        if self.crosshair:
            # Draw alignment circle on image
            alpha = 0.5
            beta = 1-alpha
            center = ( int(camera_width/2), int(camera_height/2) )
            overlay = cv2.circle( 
                cv_img.copy(), 
                center, 
                6, 
                (0,255,0), 
                int( camera_width/1.75 )
            )
            overlay = cv2.circle( 
                overlay.copy(), 
                center, 
                5, 
                (0,0,255), 
                2
            )
            for i in range(0,8):
                overlay = cv2.circle( 
                overlay.copy(), 
                center, 
                25*i, 
                (0,0,0), 
                1
            )
            overlay = cv2.line(overlay, (center[0],center[1]-int( camera_width/3 )), (center[0],center[1]+int( camera_width/3 )), (128, 128, 128), 1)
            overlay = cv2.line(overlay, (center[0]-int( camera_width/3 ),center[1]), (center[0]+int( camera_width/3 ),center[1]), (128, 128, 128), 1)
            cv_img = cv2.addWeighted(overlay, beta, cv_img, alpha, 0)
        # Updates the image_label with a new opencv image
        qt_img = self.convert_cv_qt(cv_img)
        self.image_label.setPixmap(qt_img)
        #self.mutex.unlock()

    def convert_cv_qt(self, cv_img):
        # Convert from an opencv image to QPixmap
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(display_width, display_height, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)

    def addCalibrationResult(self, result={}):
        self.calibrationResults.append(result)

if __name__=='__main__':
    os.putenv("QT_LOGGING_RULES","qt5ct.debug=false")
    app = QApplication(sys.argv)
    a = App()
    a.show()
    sys.exit(app.exec_())
