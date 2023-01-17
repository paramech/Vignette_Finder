import os
import sys
import numpy as np
import pandas as pd
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from PyQt5 import QtCore, QtGui, QtWidgets
from scipy.optimize import curve_fit
from scipy import ndimage
from pyexiv2 import Image
import json
import configparser

IMG_WIDTH = 1440
IMG_HEIGHT = 1080
centers = []  # to store vignette centers as x;y
coefficients = []  # to store vignette coefficients as 1;2;3;4;5;6
radiometrics = []  # to store radiometric calibration metadata from video stream
band_senses = []  # to store band sensetivity metadata from video stream


# def poly6(x, b, c, d, e, f, g):
#    return 1 + b * x + c * x**2 + d * x**3 + e * x**4 + f * x**5 + g * x**6
def poly6(x, b, c, e, g):
    return 1 + b * x + c * x**2 + e * x**4 + g * x**6


class Ui_MainWindow(object):  # Qt-generated app interface
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setFixedSize(543, 408)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(0, 20, 540, 50))
        font = QtGui.QFont()
        font.setFamily("Ubuntu Mono")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setStyleSheet("")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.text = QtWidgets.QTextBrowser(self.centralwidget)
        self.text.setGeometry(QtCore.QRect(15, 65, 520, 300))
        self.text.setStyleSheet("")
        self.text.setObjectName("text")
        self.btn_start = QtWidgets.QPushButton(self.centralwidget)
        self.btn_start.setEnabled(False)
        self.btn_start.setGeometry(QtCore.QRect(15, 370, 150, 30))
        self.btn_start.setObjectName("btn_start")
        self.btn_clear = QtWidgets.QPushButton(self.centralwidget)
        self.btn_clear.setGeometry(QtCore.QRect(425, 370, 110, 30))
        self.btn_clear.setObjectName("btn_clear")
        self.line = QtWidgets.QFrame(self.centralwidget)
        self.line.setGeometry(QtCore.QRect(-3, 10, 550, 30))
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.btn_open = QtWidgets.QPushButton(self.centralwidget)
        self.btn_open.setGeometry(QtCore.QRect(0, 0, 80, 25))
        self.btn_open.setAutoFillBackground(False)
        self.btn_open.setStyleSheet("")
        self.btn_open.setObjectName("btn_open")
        self.btn_save = QtWidgets.QPushButton(self.centralwidget)
        self.btn_save.setEnabled(False)
        self.btn_save.setGeometry(QtCore.QRect(80, 0, 90, 25))
        self.btn_save.setObjectName("btn_save")
        MainWindow.setCentralWidget(self.centralwidget)
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Vignette Finder"))
        self.label.setText(_translate("MainWindow", "Определение параметров виньетирования"))
        self.text.setHtml(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Ubuntu\'; font-size:11pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#000000;\">"
                                                   "Чтобы начать, откройте директорию с фотографиями</span></p></body></html>"))

        self.btn_open.setText(_translate("MainWindow", "Открыть"))
        self.btn_open.clicked.connect(self.open_file)
        self.btn_start.setText(_translate("MainWindow", "Запустить скрипт"))
        self.btn_start.clicked.connect(self.finder)
        self.btn_clear.setText(_translate("MainWindow", "Очистить"))
        self.btn_clear.clicked.connect(self.text.clear)
        self.btn_save.setText(_translate("MainWindow", "Сохранить"))
        self.btn_save.clicked.connect(self.save_file)

    def open_file(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Выберите директорию")
        if folder:
            self.text.append("Открыта директория {}".format(folder))
            self.btn_start.setEnabled(True)
            os.chdir(folder)
            QtWidgets.qApp.processEvents()

    def finder(self):
        avg_arr = []  # array to store average images as arrays of uint16
        meta_check = True  # flag to stop program if there are metadata disparities
        allfiles = os.listdir(os.getcwd())
        img_list = [filename for filename in allfiles if filename.startswith("img") and filename.endswith(".tif")]
        img_list.sort()
        if len(img_list) == 0:
            self.text.append("Фотографии в директории отсутствуют")
            pass
        else:
            note = "Найдены следующие изображения: "
            for img in img_list:  # display found images in the chat feed
                note += "{}, ".format(img)
            note = note[:len(note)-2]
            self.text.append(note)
            QtWidgets.qApp.processEvents()

            for i in range(5):  # cycle for each video stream
                names = [name for name in img_list if "img{}_".format(i) in name]
                images = np.array([np.array(mpimg.imread(name)) for name in names])
                avg = np.array(np.mean(images, axis=0), dtype='uint16')
                avg_arr.append(avg)

                img_f = Image(names[0])  # first image as metadata reference
                metadata = img_f.read_xmp()
                # More metadata filters can be implemented
                radiometric = metadata['Xmp.MicaSense.RadiometricCalibration']
                radiometrics.append("{:.10f}".format(float(radiometric[:-6]))+";0")
                band_sens = metadata['Xmp.Camera.BandSensitivity']
                band_senses.append(band_sens)
                for j in range(1, len(names)):  # comparison with remaining images
                    img_f = Image(names[j])
                    metadata = img_f.read_xmp()
                    if metadata['Xmp.MicaSense.RadiometricCalibration'] != radiometric:
                        self.text.append("Обнаружено несовпадение тегов Xmp.MicaSense.RadiometricCalibration для "
                                         "изображений потока {}".format(i))
                        meta_check = False
                        break
                    if metadata['Xmp.Camera.BandSensitivity'] != band_sens:
                        self.text.append("Обнаружено несовпадение тегов Xmp.Camera.BandSensitivity для "
                                         "изображений потока {}".format(i))
                        meta_check = False
                        break

            if meta_check:
                self.text.append("Метаданные изображений совпадают, поиск параметров...")
                QtWidgets.qApp.processEvents()
                for i in range(5):
                    # Calculating vignette center position which is supposed to be the brightest point in the image
                    note = ("Центр виньетирования для канала {}: ".format(i))
                    image = avg_arr[i].T
                    image = image - 3840.0  # blacklevel
                    com = ndimage.center_of_mass(image)  # center of mass calculation method
                    xc = int(com[0])
                    yc = int(com[1])
                    center = str(xc)+";"+str(yc)
                    centers.append(center)
                    note += str(xc)+", "+str(yc)
                    self.text.append(note)
                    QtWidgets.qApp.processEvents()

                    note = "Коэффициенты полинома: "
                    # Calculating "brightest pixel" value. All image will be normalized to that value. Averaging 11x11
                    Vref = image[xc-5:xc+6, yc-5:yc+6].mean()
                    Vx = np.empty(IMG_WIDTH)
                    df_r = []
                    df_V = []
                    j = 0
                    k = 0
                    """ Following cycle computes each pixel to brighest pixel ratio, distance to vignetting center 
                    and stores data in the arrays to be dumped later """
                    while j < IMG_WIDTH:
                        while k < IMG_HEIGHT:
                            Vx[j] = image[j, k] / Vref
                            if Vx[j] < 1.2:
                                r = ((j - xc) ** 2 + (k - yc) ** 2) ** (1 / 2)
                                df_r.append(r)
                                df_V.append(str(Vx[j]))
                            k = k + 1
                        k = 0
                        j = j + 1
                    df0 = np.vstack((df_r, df_V)).T
                    df0 = df0.astype(np.float64)
                    df0 = pd.DataFrame(df0, columns=['r', 'V'])
                    popt, pcov = curve_fit(poly6, df0['r'], df0['V'])  # coefficients calculation

                    """Coefficients have to exist within certain limits. Stored coefficients will be compared to those 
                    limits. An error will appear in the chat feed if limits are exceeded"""
                    err_arr = []
                    checks = str(popt)[1:-1].split()
                    checks.insert(2, "0")
                    checks.insert(4, "0")
                    checks = list(map(float, checks))
                    note += str(checks)
                    coefficient = ""
                    for j in range(len(checks)):
                        coefficient += str(checks[j])+";"
                    coefficient = coefficient[:len(coefficient)-1]
                    coefficients.append(coefficient)  # reformatted coefficients is appended into array
                    if checks[0] < -10e-05 or checks[0] > 10e-05:
                        err_arr.append(0)
                    if checks[1] < -10e-07 or checks[1] > 10e-07:
                        err_arr.append(1)
                    if checks[3] < -10e-13 or checks[3] > 10e-13:
                        err_arr.append(3)
                    if checks[5] < -10e-19 or checks[5] > 10e-19:
                        err_arr.append(5)
                    note = note.replace("'", "")
                    note = note.replace("[", "")
                    note = note.replace("]", "")
                    if len(err_arr) != 0:  # if limits were exceeded, exceeding coefficients will be listed
                        note += "; потенциально некачественные: "
                        for err in err_arr:
                            note += str(checks[err]) + ", "
                        note = note[:len(note)-2]
                    self.text.append(note)
                    QtWidgets.qApp.processEvents()
                    # v0 = poly6(df0['r'], *popt)
                    # plt.plot(df0['r'], v0, color='red')

                self.text.append("Скрипт завершен, сохраните файлы конфигурации")
                QtWidgets.qApp.processEvents()
                self.btn_save.setEnabled(True)

    def save_file(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Выберите директорию")
        if folder:
            self.text.append("Файлы были сохранены в директорию {}".format(folder))
            os.chdir(folder)
            QtWidgets.qApp.processEvents()

            # Parameters to format metadata, centers and coefficients into configuration files
            params = (band_senses[0], centers[0], coefficients[0], radiometrics[0], band_senses[1], centers[1],
                      coefficients[1], radiometrics[1], band_senses[2], centers[2], coefficients[2], radiometrics[2],
                      band_senses[3], centers[3], coefficients[3], radiometrics[3], band_senses[4], centers[4],
                      coefficients[4], radiometrics[4])
            json_string = '''
                        {
                                "Cams": {
                                    "0": {
                                        "central_wavelength": "470",
                                        "band_name": "Blue",
                                        "wavelength_fwhm": "28",
                                        "fnumber": "1.8",
                                        "band_sensitivity": "%s",
                                        "vignetting_center": "%s",
                                        "vignetting_polynomial": "%s",
                                        "radiometric_calibration": "%s"
                                    },
                                    "1": {
                                        "central_wavelength": "560",
                                        "band_name": "Green",
                                        "wavelength_fwhm": "20",
                                        "fnumber": "1.8",
                                        "band_sensitivity": "%s",
                                        "vignetting_center": "%s",
                                        "vignetting_polynomial": "%s",
                                        "radiometric_calibration": "%s"
                                    },
                                    "2": {
                                        "central_wavelength": "665",
                                        "band_name": "Red",
                                        "wavelength_fwhm": "14",
                                        "fnumber": "1.8",
                                        "band_sensitivity": "%s",
                                        "vignetting_center": "%s",
                                        "vignetting_polynomial": "%s",
                                        "radiometric_calibration": "%s"
                                    },
                                    "3": {
                                        "central_wavelength": "720",
                                        "band_name": "Rededge",
                                        "wavelength_fwhm": "12",
                                        "fnumber": "1.8",
                                        "band_sensitivity": "%s",
                                        "vignetting_center": "%s",
                                        "vignetting_polynomial": "%s",
                                        "radiometric_calibration": "%s"
                                    },
                                    "4": {
                                        "central_wavelength": "840",
                                        "band_name": "NIR",
                                        "wavelength_fwhm": "40",
                                        "fnumber": "1.8",
                                        "band_sensitivity": "%s",
                                        "vignetting_center": "%s",
                                        "vignetting_polynomial": "%s",
                                        "radiometric_calibration": "%s"
                                    }
                                }
                            }''' % params
            ini_string = '''
                        [Cam0]
                        central_wavelength=470
                        band_name=Blue
                        wavelength_fwhm=28
                        fnumber=1.8
                        band_sensitivity=%s
                        vignetting_center=%s
                        vignetting_polynomial=%s
                        radiometric_calibration=%s
                        
                        [Cam1]
                        central_wavelength=560
                        band_name=Green
                        wavelength_fwhm=20
                        fnumber=1.8
                        band_sensitivity=%s
                        vignetting_center=%s
                        vignetting_polynomial=%s
                        radiometric_calibration=%s
                        
                        [Cam2]
                        central_wavelength=668
                        band_name=Red
                        wavelength_fwhm=14
                        fnumber=1.8
                        band_sensitivity=%s
                        vignetting_center=%s
                        vignetting_polynomial=%s
                        radiometric_calibration=%s
                        
                        [Cam3]
                        central_wavelength=720
                        band_name=Rededge
                        wavelength_fwhm=12
                        fnumber=1.8
                        band_sensitivity=%s
                        vignetting_center=%s
                        vignetting_polynomial=%s
                        radiometric_calibration=%s
                        
                        [Cam4]
                        central_wavelength=840
                        band_name=NIR
                        wavelength_fwhm=40
                        fnumber=1.8
                        band_sensitivity=%s
                        vignetting_center=%s
                        vignetting_polynomial=%s
                        radiometric_calibration=%s''' % params

            json_result = json.loads(json_string)
            with open('tags.json', 'w') as f:  # save .json file
                json.dump(json_result, f, indent=2)
            config = configparser.ConfigParser(allow_no_value=True)
            config.read_string(ini_string)
            with open('tags.ini', 'w') as f:  # save .ini file
                config.write(f)
            self.btn_start.setEnabled(False)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
