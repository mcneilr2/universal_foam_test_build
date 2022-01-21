import serial
import time
import PyQt5.QtWidgets as qtw
from PyQt5 import QtGui
import mysql.connector
import pandas as pd
import qdarkstyle
import threading


######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################

extend = 11
retract = 10
fullspeed = 255.0
halfspeed = 127.0
quarterspeed = 63.75
default_pausetime = 5
default_forcestop = 2
perm_offset = 14.76

######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################

#################################################  SERIAL COMMUNICATION CLASS ########################################
class Arduino():
    def __init__(self, serial_port='COM3', baud_rate=9600,
            read_timeout=5):
        """
        Initializes the serial connection to the Arduino board
        """
        try:
            self.conn = serial.Serial(serial_port, baud_rate)
            self.conn.timeout = read_timeout # Timeout for readline()
            self.failout = 'good conn'
        
        except:
            self.failout = 'failed out of arduino'

    def gohome(self):
        command = (''.join(('WH', str(0), ':', str(0)))).encode()
        self.conn.write(command)

    def go_the_distance(self, pin_number, distance, speedvalue):
        command = (''.join(('WG', str(pin_number), ':',
            str(distance),':', str(speedvalue)))).encode()
        self.conn.write(command)

    def force_stop(self, force, offset):
        command = (''.join(('WF', str(0), ':',
            str(force), ':', str(offset)))).encode()
        self.conn.write(command)
        line_received = self.conn.readline().decode().strip()
        return line_received

    def stop(self):
        command = (''.join(('WS', str(0), ':',
            str(0)))).encode()
        self.conn.write(command)

    def close(self):
        self.conn.close()

    def read(self, offset):
        command = (''.join(('RF', str(0), ':', str(offset)))).encode()
        self.conn.write(command) 
        line_received = self.conn.readline().decode().strip()
        return line_received

    def tare(self):
        command = (''.join(('RT', str(0), ':', str(0)))).encode()
        self.conn.write(command)
        line_received = self.conn.readline().decode().strip()
        return line_received

    def calib(self, spring):
        command = (''.join(('WC', str(0), ':',
            str(spring), ':', str(0)))).encode()
        self.conn.write(command)
        return

######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################


#################################################  GUI CONSTRUCTION ########################################
class MainWindow(qtw.QWidget):
    def __init__(self):

        super().__init__()
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        ######## Layout Management ########
        #set main layout
        mainlayout = qtw.QGridLayout()
        self.setLayout(mainlayout)
        self.setWindowTitle("Universal Foam Tester")
        #setup sublayouts
        topboxlayout = qtw.QHBoxLayout()
        leftbuttonlayout = qtw.QVBoxLayout()
        displaylayout = qtw.QGridLayout()
        radiobuttonlayout = qtw.QHBoxLayout()
        displacementlayout = qtw.QFormLayout()
        buttonlayout = qtw.QVBoxLayout()

        self.entryfields = qtw.QTabWidget()
        tab1 = qtw.QWidget()
        tab2 = qtw.QWidget()
        tab3 = qtw.QWidget()
        tab1hbox = qtw.QGridLayout()
        tab2hbox = qtw.QGridLayout()
        tab3hbox = qtw.QGridLayout()
        tab1.setLayout(tab1hbox)
        tab2.setLayout(tab2hbox)
        tab3.setLayout(tab3hbox)

        ######## Define Sublayouts ########

        ##Test Selection
        #define the test selection
        self.testchoose = qtw.QComboBox()
        self.testchoose.addItem("Choose Test")
        self.testchoose.addItem("Firmness")
        self.testchoose.addItem("Firmness (local)")
        self.testchoose.addItem("Support Factor")
        # self.testchoose.addItem("Support Factor")
        # self.testchoose.addItem("Hysteresis")
        test_l = qtw.QLabel('&Test:')
        test_l.setBuddy(self.testchoose)
        #add the widgets to the topboxlayout
        topboxlayout.addWidget(test_l)
        topboxlayout.addWidget(self.testchoose)

        ##Start/Stop Buttons
        #define the start/stop widgets
        self.startbutton = qtw.QPushButton("Start Test", clicked = lambda: self.test_initiate())
        #add the widgets to the leftbuttonlayout
        leftbuttonlayout.addWidget(self.startbutton)
        
        ##Force/Displ Display
        #define the display widgets
        self.forcereading = qtw.QLabel('0.0')
        self.forcebutton = qtw.QPushButton("Display Force",  clicked = lambda: self.thread2())
        self.tare_button = qtw.QPushButton("Set Tare", clicked = lambda: self.thread())
        self.tare_label = qtw.QLabel('0.0')
        

        #add the widgets to the displaylayout
        displaylayout.addWidget(self.forcebutton, 0, 0)
        displaylayout.addWidget(self.forcereading, 0, 1)
        displaylayout.addWidget(self.tare_button, 1, 0)
        displaylayout.addWidget(self.tare_label, 1, 1)

        ##Extend/Retract Radio Buttons
        #define the radiobutton widgets
        self.extendbox = qtw.QRadioButton("Extend")
        self.retractbox = qtw.QRadioButton("Retract")
        self.extendbox.setChecked(True)
        #add the widgets to the radiobuttonlayout
        radiobuttonlayout.addWidget(self.extendbox)
        radiobuttonlayout.addWidget(self.retractbox)
        
        ##Displacement Entry
        #define the entry field widgets
        self.distance = qtw.QLineEdit()
        distancelabel = qtw.QLabel("Displacement (mm):")
        self.speed = qtw.QLineEdit()
        speedlabel = qtw.QLabel("Speed (%):")
        #add widgets to displacementlayout
        displacementlayout.addRow(distancelabel, self.distance)
        displacementlayout.addRow(speedlabel, self.speed)

        ##Move Button
        #define move button
        self.movebutton = qtw.QPushButton("Move", clicked = lambda: self.move_function())
        self.homebutton = qtw.QPushButton("Retract Home", clicked = lambda: self.home_function())
        buttonlayout.addWidget(self.movebutton)
        buttonlayout.addWidget(self.homebutton)

        ## Tab1
        #define entry widgets for test tab
        self.opID_entry = qtw.QLineEdit()
        opID_label = qtw.QLabel("Operator ID:")
        self.date_entry = qtw.QLineEdit()
        date_label = qtw.QLabel("Date (yyyy-mm-dd):")
        self.batchID_entry = qtw.QLineEdit()
        batchID_label = qtw.QLabel("DOE_ID:")
        self.sampleID_entry = qtw.QLineEdit()
        sampleID_label = qtw.QLabel("Sample ID:")
        self.th_entry = qtw.QLineEdit()
        th_label = qtw.QLabel("Thickness (mm):")
        self.firmness_calc = qtw.QLabel('')
        firmness_label = qtw.QLabel("Firmness (N):")
        self.support_calc = qtw.QLabel('')
        support_label = qtw.QLabel("Support Factor (N/N):")
        self.firmness_l_calc = qtw.QLabel('')
        firmness_l_label = qtw.QLabel("Firmness (local) (N):")
        self.enterbutton = qtw.QPushButton("Commit Results to Database", clicked = lambda: self.commit())
        self.pbar = qtw.QProgressBar(self)
        proglabel = qtw.QLabel("Test Recovery")
        #define tab layout
        tab1hbox.addWidget(opID_label, 0, 0)
        tab1hbox.addWidget(self.opID_entry, 0, 1)
        tab1hbox.addWidget(date_label, 1, 0)
        tab1hbox.addWidget(self.date_entry, 1, 1)
        tab1hbox.addWidget(batchID_label, 2, 0)
        tab1hbox.addWidget(self.batchID_entry, 2, 1)
        tab1hbox.addWidget(sampleID_label, 3, 0)
        tab1hbox.addWidget(self.sampleID_entry, 3, 1)
        tab1hbox.addWidget(th_label, 0, 2)
        tab1hbox.addWidget(self.th_entry, 0, 3)
        tab1hbox.addWidget(firmness_label, 1, 2)
        tab1hbox.addWidget(self.firmness_calc, 1, 3)
        tab1hbox.addWidget(support_label, 2, 2)
        tab1hbox.addWidget(self.support_calc, 2, 3)
        tab1hbox.addWidget(firmness_l_label, 3, 2)
        tab1hbox.addWidget(self.firmness_l_calc, 3, 3)
        tab1hbox.addWidget(self.enterbutton, 4, 3)
        tab1hbox.addWidget(proglabel, 4, 0)
        tab1hbox.addWidget(self.pbar, 4, 1, 1, 2)

        ## Tab2
        self.table = qtw.QTableWidget(10, 10)
        self.table.setAlternatingRowColors(True)
        #define back end widgets
        tab2hbox.setContentsMargins(5, 5, 5, 5)
        tab2hbox.addWidget(self.table)
        conn = mysql.connector.connect(host = 'localhost', user = 'root', passwd = 'password', database = 'foam')
        query = """select * from tests order by sample_id desc"""
        df = pd.read_sql(query, conn)
        self.table.setHorizontalHeaderLabels(df.columns)
        for row in df.iterrows():
            values = row[1]
            for col_index, value in enumerate(values):
                tableItem = qtw.QTableWidgetItem(str(value))
                self.table.setItem(row[0], col_index, tableItem)

        ## Tab3
        #define entry widgets for test tab
        self.calibrate = qtw.QPushButton("Run Calibration", clicked = lambda: self.calibration())
        #define tab layout
        tab3hbox.addWidget(self.calibrate, 0,0)
    
        #add tabs to widget
        self.entryfields.addTab(tab1, "&Test Results")
        self.entryfields.addTab(tab2, "Test Database")
        self.entryfields.addTab(tab3, "Device Calibration")
    
        ######## Add Sublayouts to MainLayout ########
        mainlayout.addLayout(topboxlayout, 0, 0)
        mainlayout.addLayout(leftbuttonlayout, 1, 0)
        mainlayout.addLayout(displaylayout, 2, 0)
        mainlayout.addLayout(radiobuttonlayout, 0, 1)
        mainlayout.addLayout(displacementlayout, 1, 1)
        mainlayout.addLayout(buttonlayout, 2, 1)
        mainlayout.addWidget(self.entryfields, 3, 0, 1, 2)
    
        self.show()

######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################


#################################################  FORCE CELL COMMUNICATION FUNCTIONS ################################
    
    def set_tare(self):
        self.click()
        a = Arduino()
        if a.failout == 'failed out of arduino':
            noent = qtw.QMessageBox()
            noent.setIcon(qtw.QMessageBox.Warning)
            noent.setText("Check USB Connections")
            noent.setWindowTitle("No Serial Connect")
            noent.setStandardButtons(qtw.QMessageBox.Ok)
            noent.buttonClicked.connect(self.unclick)
            noent.exec()
            return
        else:
            time.sleep(2)
            offset = a.tare()
            offset = a.tare()
            offset = a.tare()
            self.tare_label.setText(offset)
            a.close()
            self.unclick()
        return

    def display_force(self):
        self.click()
        if float(self.tare_label.text()) > -1.0:
            self.tare_check()
        else:
            a = Arduino()
            if a.failout == 'failed out of arduino':
                noent = qtw.QMessageBox()
                noent.setIcon(qtw.QMessageBox.Warning)
                noent.setText("Check USB Connections")
                noent.setWindowTitle("No Serial Connect")
                noent.setStandardButtons(qtw.QMessageBox.Ok)
                noent.buttonClicked.connect(self.unclick)
                noent.exec()
                return
            else:
                time.sleep(2)
                offset = self.tare_label.text()
                for i in range(1):
                    force = float(a.read(offset)) - perm_offset
                self.forcereading.setText(str(round(force, 1)))
                a.close()
                self.unclick()
        return


    def tare_check(self):
        noent = qtw.QMessageBox()
        noent.setIcon(qtw.QMessageBox.Warning)
        noent.setText("Set tare with no weight")
        noent.setWindowTitle("Load calibration")
        noent.setStandardButtons(qtw.QMessageBox.Ok)
        noent.exec()
        return

    def calibration(self):
        commence = qtw.QMessageBox()
        commence.setIcon(qtw.QMessageBox.Question)
        commence.setText("Proceed with Calibration?\nEnsure that the load cell is clear and the desired spring is loaded for calibration")
        commence.setWindowTitle("Proceed")
        commence.setStandardButtons(qtw.QMessageBox.Ok | qtw.QMessageBox.No)
        commence.buttonClicked.connect(self.calibration_1)
        commence.exec()
        return

    def calibration_1(self, i):
        self.click()
        if i.text() == 'OK':
            a = Arduino()
            if a.failout == 'failed out of arduino':
                noent = qtw.QMessageBox()
                noent.setIcon(qtw.QMessageBox.Warning)
                noent.setText("Check USB Connections")
                noent.setWindowTitle("No Serial Connect")
                noent.setStandardButtons(qtw.QMessageBox.Ok)
                noent.buttonClicked.connect(self.unclick)
                noent.exec()
                return
            else:
                time.sleep(2)
                spring_force = 101.69
                a.calib(spring_force)
                for x in range(15):
                    print(a.conn.readline().decode().strip())
                
                a.go_the_distance(retract, 40, fullspeed)
                a.close()
            self.unclick()
            return

    def set_tare(self):
        self.click()
        a = Arduino()
        if a.failout == 'failed out of arduino':
            noent = qtw.QMessageBox()
            noent.setIcon(qtw.QMessageBox.Warning)
            noent.setText("Check USB Connections")
            noent.setWindowTitle("No Serial Connect")
            noent.setStandardButtons(qtw.QMessageBox.Ok)
            noent.buttonClicked.connect(self.unclick)
            noent.exec()
            return
        else:
            time.sleep(2)
            offset = a.tare()
            self.tare_label.setText(offset)
            a.close()
            self.unclick()
            return
    
    def display_force(self):
        self.click()
        if float(self.tare_label.text()) > -1.0:
            self.tare_check()
        else:
            a = Arduino()
            if a.failout == 'failed out of arduino':
                noent = qtw.QMessageBox()
                noent.setIcon(qtw.QMessageBox.Warning)
                noent.setText("Check USB Connections")
                noent.setWindowTitle("No Serial Connect")
                noent.setStandardButtons(qtw.QMessageBox.Ok)
                noent.buttonClicked.connect(self.unclick)
                noent.exec()
                return
            else:
                time.sleep(2)
                offset = self.tare_label.text()
                for i in range(4):
                    force = float(a.read(offset)) - perm_offset
                self.forcereading.setText(str(round(force, 5)))
                a.close()
            self.unclick()
            return


######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################


#################################################  MOTOR CONTROL FUNCTIONS ###########################################
    

    def home_function(self):
        self.click()
        a = Arduino()
        if a.failout == 'failed out of arduino':
            noent = qtw.QMessageBox()
            noent.setIcon(qtw.QMessageBox.Warning)
            noent.setText("Check USB Connections")
            noent.setWindowTitle("No Serial Connect")
            noent.setStandardButtons(qtw.QMessageBox.Ok)
            noent.buttonClicked.connect(self.unclick)
            noent.exec()
            return
        else:
            time.sleep(2)
            a.gohome()
            a.close()
            self.unclick()
        return

    def test_initiate(self):
        if self.testchoose.currentIndex() == 0:
            nochoose = qtw.QMessageBox()
            nochoose.setIcon(qtw.QMessageBox.Warning)
            nochoose.setText("Please make a test selection")
            nochoose.setWindowTitle("No test selected")
            nochoose.setStandardButtons(qtw.QMessageBox.Ok)
            nochoose.exec()
        if self.testchoose.currentIndex() == 1:
            self.firmness()
        elif self.testchoose.currentIndex() == 2:
            self.firmness_l()
        elif self.testchoose.currentIndex() == 3:
            self.support()
        return

    def firmness(self):
        a = Arduino()
        if a.failout == 'failed out of arduino':
                noent = qtw.QMessageBox()
                noent.setIcon(qtw.QMessageBox.Warning)
                noent.setText("Check USB Connections")
                noent.setWindowTitle("No Serial Connect")
                noent.setStandardButtons(qtw.QMessageBox.Ok)
                noent.buttonClicked.connect(self.unclick)
                noent.exec()
                return
        else:
            time.sleep(2)
            offset = self.tare_label.text()
            if (-50000 > float(offset) > -1):
                self.tare_check()
            else:
                if not self.th_entry.text():
                    self.thickness_check()
                else:
                    a.force_stop(default_forcestop, offset)
                    a.close()
                    commence = qtw.QMessageBox()
                    commence.setIcon(qtw.QMessageBox.Question)
                    commence.setText("Proceed with measurement?")
                    commence.setWindowTitle("Proceed")
                    commence.setStandardButtons(qtw.QMessageBox.Ok | qtw.QMessageBox.No)
                    commence.buttonClicked.connect(self.firmness_1)
                    commence.exec()
            a.close()

    def firmness_1(self, i):
        self.click()
        if i.text() == 'OK':
            pausetime = default_pausetime
            offset = self.tare_label.text()
            a = Arduino()
            if a.failout == 'failed out of arduino':
                noent = qtw.QMessageBox()
                noent.setIcon(qtw.QMessageBox.Warning)
                noent.setText("Check USB Connections")
                noent.setWindowTitle("No Serial Connect")
                noent.setStandardButtons(qtw.QMessageBox.Ok)
                noent.buttonClicked.connect(self.unclick)
                noent.exec()
                return
            else:
                time.sleep(2)
                thickness = self.th_entry.text()
                twofive_distance = 0.25*float(thickness)
                a.go_the_distance(extend, twofive_distance, 20)
                time.sleep(pausetime)
                force = float(a.read(offset)) - perm_offset
                self.firmness_calc.setText((str(round(force, 1))))
                time.sleep(0.1)
                a.go_the_distance(retract, (10), fullspeed)
                a.close()
                # for i in range(100):
                #     time.sleep(0.1)
                #     self.pbar.setValue(i)
            self.unclick()
        return
        
    def firmness_l(self):
        a = Arduino()
        if a.failout == 'failed out of arduino':
            noent = qtw.QMessageBox()
            noent.setIcon(qtw.QMessageBox.Warning)
            noent.setText("Check USB Connections")
            noent.setWindowTitle("No Serial Connect")
            noent.setStandardButtons(qtw.QMessageBox.Ok)
            noent.buttonClicked.connect(self.unclick)
            noent.exec()
            return
        else:
            time.sleep(2)
            offset = self.tare_label.text()
            if (-50000 > float(offset) > -1):
                self.tare_check()
            else:
                if not self.th_entry.text():
                    self.thickness_check()
                else:
                    a.force_stop(default_forcestop, offset)
                    a.close()
                    commence = qtw.QMessageBox()
                    commence.setIcon(qtw.QMessageBox.Question)
                    commence.setText("Proceed with measurement?")
                    commence.setWindowTitle("Proceed")
                    commence.setStandardButtons(qtw.QMessageBox.Ok | qtw.QMessageBox.No)
                    commence.buttonClicked.connect(self.firmness_l_1)
                    commence.exec()
            a.close()

    def firmness_l_1(self, i):
        self.click()
        if i.text() == 'OK':
            pausetime = default_pausetime
            offset = self.tare_label.text()
            a = Arduino()
            if a.failout == 'failed out of arduino':
                noent = qtw.QMessageBox()
                noent.setIcon(qtw.QMessageBox.Warning)
                noent.setText("Check USB Connections")
                noent.setWindowTitle("No Serial Connect")
                noent.setStandardButtons(qtw.QMessageBox.Ok)
                noent.buttonClicked.connect(self.unclick)
                noent.exec()
                return
            else:
                time.sleep(2)
                thickness = self.th_entry.text()
                twofive_distance = 0.25*float(thickness)
                a.go_the_distance(extend, twofive_distance, 20)
                time.sleep(pausetime)
                force = float(a.read(offset)) - perm_offset
                self.firmness_l_calc.setText((str(round(force, 1))))
                time.sleep(0.1)
                a.go_the_distance(retract, (10), fullspeed)
                a.close()
                # for i in range(100):
                #     time.sleep(0.1)
                #     self.pbar.setValue(i)
        self.unclick()
        return
    def support(self):
        a = Arduino()
        if a.failout == 'failed out of arduino':
            noent = qtw.QMessageBox()
            noent.setIcon(qtw.QMessageBox.Warning)
            noent.setText("Check USB Connections")
            noent.setWindowTitle("No Serial Connect")
            noent.setStandardButtons(qtw.QMessageBox.Ok)
            noent.buttonClicked.connect(self.unclick)
            noent.exec()
            return
        else:
            time.sleep(2)
            offset = self.tare_label.text()
            if (-50000 > float(offset) > -1):
                self.tare_check()
            else:
                if not self.th_entry.text():
                    self.thickness_check()
                else:
                    a.force_stop(default_forcestop, offset)
                    a.close()
                    commence = qtw.QMessageBox()
                    commence.setIcon(qtw.QMessageBox.Question)
                    commence.setText("Proceed with measurement?")
                    commence.setWindowTitle("Proceed")
                    commence.setStandardButtons(qtw.QMessageBox.Ok | qtw.QMessageBox.No)
                    commence.buttonClicked.connect(self.support_1)
                    commence.exec()
            a.close()

    def support_1(self, i):
        self.click()
        if i.text() == 'OK':
            a = Arduino()
            if a.failout == 'failed out of arduino':
                noent = qtw.QMessageBox()
                noent.setIcon(qtw.QMessageBox.Warning)
                noent.setText("Check USB Connections")
                noent.setWindowTitle("No Serial Connect")
                noent.setStandardButtons(qtw.QMessageBox.Ok)
                noent.buttonClicked.connect(self.unclick)
                noent.exec()
                return
            else:
                time.sleep(2)
                thickness = self.th_entry.text()
                twofive_distance = 0.25*float(thickness)
                offset = self.tare_label.text()
                a.go_the_distance(extend, twofive_distance, quarterspeed)
                time.sleep(default_pausetime)
                force = float(a.read(offset))
                force = force - perm_offset
                self.firmness_calc.setText((str(round(force, 1))))
                time.sleep(60)
                fourtydistance = 0.4*float(thickness)
                a.go_the_distance(extend, fourtydistance, quarterspeed)
                time.sleep(default_pausetime)
                sixfiveforce = a.read(offset)
                force = (float(sixfiveforce)-perm_offset)/(float(self.firmness_calc.text()))
                self.support_calc.setText((str(round(force, 1))))
                time.sleep(0.5)
                a.go_the_distance(retract, 10, fullspeed)
                a.close()
            self.unclick()
        return
    

    def move_function(self):
        if not self.distance.text() or not self.speed.text():
            noent = qtw.QMessageBox()
            noent.setIcon(qtw.QMessageBox.Warning)
            noent.setText("Indicate speed/displacement")
            noent.setWindowTitle("Blank Entry")
            noent.setStandardButtons(qtw.QMessageBox.Ok)
            noent.exec()
        else: 
            self.click()    
            if self.extendbox.isChecked():
                pin_number = extend
            if self.retractbox.isChecked():
                pin_number = retract

            travel = self.distance.text()
            speedvalue = (float(self.speed.text())/100)*255
            
            
            a = Arduino()
            if a.failout == 'failed out of arduino':
                noent = qtw.QMessageBox()
                noent.setIcon(qtw.QMessageBox.Warning)
                noent.setText("Check USB Connections")
                noent.setWindowTitle("No Serial Connect")
                noent.setStandardButtons(qtw.QMessageBox.Ok)
                noent.buttonClicked.connect(self.unclick)
                noent.exec()
                return
            else:
                time.sleep(2)
                a.go_the_distance(pin_number, travel, speedvalue)
                time.sleep(1)
                a.close()
                self.unclick()
        return



######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################


#################################################  PROGRAM HANDLING ################################
    def thickness_check(self):
        noent = qtw.QMessageBox()
        noent.setIcon(qtw.QMessageBox.Warning)
        noent.setText("Indicate sample thickness")
        noent.setWindowTitle("Blank Entry")
        noent.setStandardButtons(qtw.QMessageBox.Ok)
        noent.exec()
        return

    def thread(self):
        t1=threading.Thread(target = self.set_tare)
        t1.start()

    def thread2(self):
        t1=threading.Thread(target = self.display_force)
        t1.start()

    def click(self):
        self.tare_button.setEnabled(False)
        self.forcebutton.setEnabled(False)
        self.startbutton.setEnabled(False)
        self.movebutton.setEnabled(False) 
        self.homebutton.setEnabled(False)
        self.enterbutton.setEnabled(False)
        self.calibrate.setEnabled(False)
        return

    def unclick(self):
        self.tare_button.setEnabled(True)
        self.forcebutton.setEnabled(True)
        self.startbutton.setEnabled(True)
        self.movebutton.setEnabled(True) 
        self.homebutton.setEnabled(True)
        self.enterbutton.setEnabled(True)
        self.calibrate.setEnabled(True)
        return 


######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################


#################################################  COMMUNICATION WITH SQL DATABASE ################################
    def commit(self):
        self.click()
        self.conn = mysql.connector.connect(host = 'localhost', user = 'root', passwd = 'password', database = 'foam')
        c = self.conn.cursor()
        if not self.sampleID_entry.text() or not self.batchID_entry.text() or not self.date_entry.text() or not self.opID_entry.text() or not self.th_entry.text():
            self.thickness_check()
        else:
            sample_id = self.sampleID_entry.text()
            doe_id = self.batchID_entry.text()
            test_date = self.date_entry.text()
            operator = self.opID_entry.text()
            thickness = self.th_entry.text()
            if self.firmness_calc.text():
                test_name = 'firmness (N)'
                entry = self.firmness_calc.text()
                query = """INSERT INTO tests(sample_id,DOE_ID,test_name,
                result,test_date, operator, thickness) 
                VALUES(%s, %s, %s, %s, %s, %s, %s);"""
                c.execute(query, (sample_id, doe_id, test_name, entry, test_date, operator, thickness))
                self.conn.commit()
                self.firmness_calc.setText('')

            if self.firmness_l_calc.text():
                test_name = 'firmness (N) (local)'
                entry = self.firmness_l_calc.text()
                query = """INSERT INTO tests(sample_id,DOE_ID,test_name,
                result,test_date, operator, thickness) 
                VALUES(%s, %s, %s, %s, %s, %s, %s);"""
                c.execute(query, (sample_id, doe_id, test_name, entry, test_date, operator, thickness))
                self.conn.commit()
                self.firmness_l_calc.setText('')

            if self.support_calc.text():
                test_name = 'support factor (N/N)'
                entry = self.support_calc.text()
                query = """INSERT INTO tests(sample_id,DOE_ID,test_name,
                result,test_date, operator, thickness) 
                VALUES(%s, %s, %s, %s, %s, %s, %s);"""
                c.execute(query, (sample_id, doe_id, test_name, entry, test_date, operator, thickness))
                self.conn.commit()
                self.support_calc.setText('')

        query = """select * from tests order by test_date desc, test_id desc"""
        df = pd.read_sql(query, self.conn)
        self.table.setHorizontalHeaderLabels(df.columns)
        for row in df.iterrows():
            values = row[1]
            for col_index, value in enumerate(values):
                tableItem = qtw.QTableWidgetItem(str(value))
                self.table.setItem(row[0], col_index, tableItem)
        c.close()
        self.unclick()
        return



######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################
######################################################################################################################
#################################################  GUI INITIALIZATION ################################################
if __name__ == '__main__':
    app = qtw.QApplication([])
    UFT = MainWindow()
    UFT.setWindowIcon(QtGui.QIcon('LY.png'))
    app.exec_()























    # def hysteresis(self):
    #     if not self.th_entry.text():
    #         self.thickness_check()
    #     if float(self.tare_label.text()) > -1.0:
    #         self.tare_check()
    #     else:
    #         commence = qtw.QMessageBox()
    #         commence.setIcon(qtw.QMessageBox.Question)
    #         commence.setText("Proceed with hysteresis measurement?")
    #         commence.setWindowTitle("Proceed")
    #         commence.setStandardButtons(qtw.QMessageBox.Ok | qtw.QMessageBox.No)
    #         commence.buttonClicked.connect(self.hysteresis_1)
    #         commence.exec()
    #     return
    
    # def hysteresis_1(self, i):
    #     if i.text() == 'OK':
    #         a = Arduino()
    #         time.sleep(2)
    #         thickness = self.th_entry.text()
    #         twofivedistance = 0.25*float(thickness)
    #         fourtydistance = 0.4*float(thickness)
    #         offset = self.tare_label.text()
    #         a.go_the_distance(extend, twofivedistance, fullspeed)
    #         pausetime = self.pausetime_check()
    #         time.sleep(pausetime)
    #         a.go_the_distance(extend, fourtydistance, fullspeed)
    #         time.sleep(pausetime)
    #         a.go_the_distance(retract, fourtydistance, fullspeed)
    #         time.sleep(pausetime)
    #         force = float(a.read(offset))
    #         force = force - stupid_offset
    #         self.hysteresis_calc.setText((str(round(force, 1))))
    #         time.sleep(0.5)
    #         a.go_the_distance(retract, thickness, fullspeed)
    #         time.sleep(0.5)
    #         a.close()
    #     return
