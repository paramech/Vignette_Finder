import os
import sys
import numpy as np
import pandas as pd
import matplotlib.image as mpimg
from PyQt5 import QtCore, QtGui, QtWidgets
from scipy.optimize import curve_fit
from scipy import ndimage
from pyexiv2 import Image
import json
import configparser

centers = []  # list to store vignette centers as "x;y" strings
coefficients = []  # list to store vignette coefficients as "1.1;2.2;3.3;4.4;5.5;6.6" strings


def meta_filter(img_list):
    """
    Check whether images in img_list contain metadata necessary for image averaging. If they lack tags or the value is 0
    remove those images from the list and display their filenames in the text browser
    :param img_list: filenames list containing all images from opened directory
    :return: filenames list without filtered images, string with names of removed images
    """
    filtered = ""
    for name in img_list:
        img = Image(name)
        exif = img.read_exif()
        try:
            iso_speed = exif['Exif.Photo.ISOSpeedRatings']
            exposure_time = exif['Exif.Photo.ExposureTime']
            if iso_speed is None or exposure_time is None or iso_speed == '0' or exposure_time == '0':
                img_list.remove(name)
                filtered += str(name) + ", "
        except KeyError:
            img_list.remove(name)
            filtered += str(name) + ", "
    return img_list, filtered[:len(filtered)-2]


def check_average(img_list):
    """
    Check whether the metadata from the image corresponds to the metadata from the first image of each band. BandName is
    used to make sure images are from the same band. ISOSpeedRating and ExposureTime are used to make sure averaging
    will deliver correct result. If there is a difference in tags, finish function presumably. Else, find an average
    image and store it in the list. Repeat for each band
    :param img_list: filenames list containing all images from opened directory
    :return: Checkout flag, average images list, image size parameters and blacklevel
    """
    averages = []
    for i in range(5):
        # Filter out all filenames but from band that is being processed
        names = [name for name in img_list if "img{}_".format(i) in name]
        img = Image(names[0])  # read first image and use its metadata as a reference
        exif = img.read_exif()
        xmp = img.read_xmp()
        iso_speed = exif['Exif.Photo.ISOSpeedRatings']
        exposure_time = exif['Exif.Photo.ExposureTime']
        band_name = xmp['Xmp.Camera.BandName']
        # Also define image size parameters and blacklevel from metadata for further use in the main script
        img_width = int(exif['Exif.Image.ImageWidth'])
        img_height = int(exif['Exif.Image.ImageLength'])
        blacklevel = float(exif['Exif.Image.BlackLevel'][:len(exif['Exif.Image.BlackLevel'])-2])
        for j in range(1, len(names)):  # compare metadata from each image (besides first) to the reference
            img = Image(names[j])
            exif = img.read_exif()
            xmp = img.read_xmp()
            if exif['Exif.Photo.ISOSpeedRatings'] != iso_speed or exif['Exif.Photo.ExposureTime'] != exposure_time or \
                    xmp['Xmp.Camera.BandName'] != band_name:
                return False, averages

        # Open images as NumPy arrays of arrays for successful averaging of uint16 pixels
        images = np.array([np.array(mpimg.imread(name)) for name in names])
        average = np.array(np.mean(images, axis=0), dtype='uint16')
        averages.append(average)
    return True, averages, img_width, img_height, blacklevel


def poly6(x, b, c, e, g):
    return 1 + b * x + c * x**2 + e * x**4 + g * x**6


class Ui_MainWindow(object):
    """
    Qt-generated GUI Class with implemented open_file, finder and save_file functions. Open directory with
    images of Geoscan Pollux bands. Launch the main script to calculate vignette coefficients and store them into lists.
    Save tags.json and tags.ini configuration files in chosen directory

    The GUI contains text browser to inform the user about the calibration progress
    """

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
        self.line.setGeometry(QtCore.QRect(0, 10, 543, 30))
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
        """
        Change current directory to the folder of user's choice for further use by the main script. Display selected
        directory in the text browser
        """
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Выберите директорию")
        if folder:
            self.text.append("Открыта директория {}".format(folder))
            self.btn_start.setEnabled(True)  # enable "Запустить скрипт" button to work with inner images
            os.chdir(folder)
            QtWidgets.qApp.processEvents()

    def finder(self):
        """
        Open all filtered images in chosen directory and store them in the list. If there are images in correct format,
        launch check_average and use returned images list to calculate the vignette centers (theorized to correlate
        with mass center of the image) and vignette coefficients as polynomial of pixels brightness approximation.
        Format and store collected data in lists as strings. Check if coefficients exceed proposed limits and display
        warnings in the text browser
        """
        allfiles = os.listdir(os.getcwd())  # get all filenames in the current directory
        # Filter out everything but "img...tif" files and sort them by names
        img_list = [filename for filename in allfiles if filename.startswith("img") and filename.endswith(".tif")]
        img_list.sort()
        if len(img_list) == 0:
            self.text.append("Фотографии в директории отсутствуют")
            pass
        else:
            note = "Найдены следующие изображения: "
            for img in img_list:  # display found images in the text browser
                note += "{}, ".format(img)
            note = note[:len(note)-2]
            self.text.append(note)
            QtWidgets.qApp.processEvents()
            img_list, filtered = meta_filter(img_list)
            note = "Следующие изображения не содержат необходимые теги и будут проигнорированы: {}".format(filtered)
            self.text.append(note)
            QtWidgets.qApp.processEvents()
            meta_check, avg_arr, img_width, img_height, blacklevel = check_average(img_list)
            if meta_check:
                self.text.append("Метаданные изображений совпадают, поиск параметров...")
                QtWidgets.qApp.processEvents()
                for i in range(5):
                    # Calculating vignette center position which is supposed to be the brightest point in the image
                    note = ("Центр виньетирования для канала {}: ".format(i))
                    image = avg_arr[i].T
                    image = image - blacklevel
                    com = ndimage.center_of_mass(image)  # center of mass calculation method
                    xc = int(com[0])
                    yc = int(com[1])
                    center = str(xc)+";"+str(yc)
                    centers.append(center)
                    note += str(xc)+", "+str(yc)
                    self.text.append(note)
                    QtWidgets.qApp.processEvents()

                    note = "Коэффициенты полинома: "
                    # Calculating brightest pixel value. All images will be normalized to that value. Averaging 11x11
                    Vref = image[xc-5:xc+6, yc-5:yc+6].mean()
                    Vx = np.empty(img_width)
                    df_r = []
                    df_V = []
                    j = 0
                    k = 0
                    """ Following cycle computes each pixel to brighest pixel ratio, distance to vignetting center 
                    and stores data in the lists to be used in the save_file function later """
                    while j < img_width:
                        while k < img_height:
                            Vx[j] = image[j, k] / Vref
                            if Vx[j] < 1.2:
                                r = ((j - xc) ** 2 + (k - yc) ** 2) ** (1 / 2)
                                df_r.append(r)  # append radius to the processed pixel into dataframe
                                # append processed pixel value normalized to the brightest pixel value into dataframe
                                df_V.append(str(Vx[j]))
                            k = k + 1
                        k = 0
                        j = j + 1
                    df0 = np.vstack((df_r, df_V)).T
                    df0 = df0.astype(np.float64)
                    df0 = pd.DataFrame(df0, columns=['r', 'V'])  # form a dataframe for approximation
                    popt, pcov = curve_fit(poly6, df0['r'], df0['V'])  # coefficients calculation using polynomial

                    err_arr = []  # list to store limit-exceeding coefficients
                    checks = str(popt)[1:-1].split()  # format coefficients for check and further usage
                    checks.insert(2, "0")
                    checks.insert(4, "0")
                    checks = list(map(float, checks))
                    note += str(checks)
                    coefficient = ""
                    for j in range(len(checks)):
                        coefficient += str(checks[j])+";"
                    coefficient = coefficient[:len(coefficient)-1]
                    coefficient = coefficient.replace("0.0;", "0;")
                    coefficients.append(coefficient)  # append formatted coefficients into err_arr
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
                    if len(err_arr) != 0:  # if limits are exceeded, display exceeding coefficient
                        note += "; потенциально некачественные: "
                        for err in err_arr:
                            note += str(checks[err]) + ", "
                        note = note[:len(note)-2]
                    self.text.append(note)
                    QtWidgets.qApp.processEvents()

                self.text.append("Скрипт завершен, сохраните файлы конфигурации")
                QtWidgets.qApp.processEvents()
                self.btn_save.setEnabled(True)  # enable "Сохранить" button
            else:
                self.text.append("Обнаружены несовпадения в метаданных изображений")
                QtWidgets.qApp.processEvents()

    def save_file(self):
        """
        Change current directory to the folder of user's choice. Get vignette parameters from centers and coefficients
        lists and format them into .json and .ini files templates. Save files into the selected directory
        """
        folder = QtWidgets.QFileDialog.getExistingDirectory(None, "Выберите директорию")
        if folder:
            os.chdir(folder)
            params = (centers[0], coefficients[0], centers[1], coefficients[1], centers[2], coefficients[2], centers[3],
                      coefficients[3], centers[4], coefficients[4])
            json_string = '''
                        {
                                "Cams": {
                                    "0": {
                                        "central_wavelength": "470",
                                        "band_name": "Blue",
                                        "wavelength_fwhm": "28",
                                        "fnumber": "1.8",
                                        "band_sensitivity": "0.83",
                                        "vignetting_center": "%s",
                                        "vignetting_polynomial": "%s",
                                        "radiometric_calibration": "0.000119266;0"
                                    },
                                    "1": {
                                        "central_wavelength": "560",
                                        "band_name": "Green",
                                        "wavelength_fwhm": "20",
                                        "fnumber": "1.8",
                                        "band_sensitivity": "0.8",
                                        "vignetting_center": "%s",
                                        "vignetting_polynomial": "%s",
                                        "radiometric_calibration": "0.000123596;0"
                                    },
                                    "2": {
                                        "central_wavelength": "665",
                                        "band_name": "Red",
                                        "wavelength_fwhm": "14",
                                        "fnumber": "1.8",
                                        "band_sensitivity": "0.4",
                                        "vignetting_center": "%s",
                                        "vignetting_polynomial": "%s",
                                        "radiometric_calibration": "0.000246559;0"
                                    },
                                    "3": {
                                        "central_wavelength": "720",
                                        "band_name": "Rededge",
                                        "wavelength_fwhm": "12",
                                        "fnumber": "1.8",
                                        "band_sensitivity": "0.307",
                                        "vignetting_center": "%s",
                                        "vignetting_polynomial": "%s",
                                        "radiometric_calibration": "0.000322352;0"
                                    },
                                    "4": {
                                        "central_wavelength": "840",
                                        "band_name": "NIR",
                                        "wavelength_fwhm": "40",
                                        "fnumber": "1.8",
                                        "band_sensitivity": "0.73",
                                        "vignetting_center": "%s",
                                        "vignetting_polynomial": "%s",
                                        "radiometric_calibration": "0.000135683;0"
                                    }
                                }
                            }
                            ''' % params
            ini_string = '''
                        [Cam0]
                        central_wavelength=470
                        band_name=Blue
                        wavelength_fwhm=28
                        fnumber=1.8
                        band_sensitivity=0.83
                        vignetting_center=%s
                        vignetting_polynomial=%s
                        radiometric_calibration=0.000119266;0

                        [Cam1]
                        central_wavelength=560
                        band_name=Green
                        wavelength_fwhm=20
                        fnumber=1.8
                        band_sensitivity=0.8
                        vignetting_center=%s
                        vignetting_polynomial=%s
                        radiometric_calibration=0.000123596;0

                        [Cam2]
                        central_wavelength=668
                        band_name=Red
                        wavelength_fwhm=14
                        fnumber=1.8
                        band_sensitivity=0.4
                        vignetting_center=%s
                        vignetting_polynomial=%s
                        radiometric_calibration=0.000246559;0

                        [Cam3]
                        central_wavelength=720
                        band_name=Rededge
                        wavelength_fwhm=12
                        fnumber=1.8
                        band_sensitivity=0.307
                        vignetting_center=%s
                        vignetting_polynomial=%s
                        radiometric_calibration=0.000322352;0

                        [Cam4]
                        central_wavelength=840
                        band_name=NIR
                        wavelength_fwhm=40
                        fnumber=1.8
                        band_sensitivity=0.73
                        vignetting_center=%s
                        vignetting_polynomial=%s
                        radiometric_calibration=0.000135683;0
                        ''' % params

            json_result = json.loads(json_string)  # create json object from json_string
            with open('tags.json', 'w') as f:  # write json object as tags.json file
                json.dump(json_result, f, indent=2)
            config = configparser.ConfigParser(allow_no_value=True)  # setup config parser to work write .ini file
            config.read_string(ini_string)
            with open('tags.ini', 'w') as f:  # write parsed ini_string as tags.ini file
                config.write(f)
            self.text.append("Файлы были сохранены в директорию {}".format(folder))
            self.btn_start.setEnabled(False)  # disable "Запустить скрипт" button until the new directory is opened
            QtWidgets.qApp.processEvents()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)  # initialize Qt app with system arguments
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()  # display Qt GUI using Ui_MainWindow Class methods
    sys.exit(app.exec_())  # finish the program once app is closed
