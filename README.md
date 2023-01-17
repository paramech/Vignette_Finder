Before working make sure to install all the modules listed in **requirements.txt**. If an error occures during the automatic IDE configuration, it would make sense to install latest versions of modules aviable on your Python interpretator (3.11 was used in that project).

* **app.py** - main file to run the app. In the GUI you will be able to open folder with .tif images of evenly lit white wall from every band of Geoscan Pollux multispectral camera using "Открыть" button. Run the main script by using "Запустить скрипт" and wait until the calibration is finished, this process will be followed by the messages in the text browser. After that, "Сохранить" button will allow you to save .json and .ini configuration files containing key metadata, vignette centers and coefficients.

* **example_input** - folder with 10 example photos of evenly lit whit wall from each band.

* **example_output** - folder with processed configuration files of example_input photos.
##

Перед началом работы необходимо установить требуемые модули согласно **requirements.txt**. В случае возникновения ошибки автоматической настройки среды разработки имеет смысл установить самые актуальные версии модулей под вашу версию интерпретатора Python (т.е. если она не соответствует 3.11).

* **app.py** - основной файл для запуска приложения. В графическом интерфейсе вы можете открыть директорию с .tif изображениями равномерно освещенной белой стены с каждого канала мультиспектральной камеры Geoscan Pollux, используя кнопку "Открыть. Запустить основной скрипт можно используя одноименную кнопку, после чего вычислительный процесс будет сопровождаться сообщениями в текстовом окне вплоть до окончания обработки. После этого, с помощью кнопки "Сохранить" можно получить .json и .ini файлы, содержащиеся конфигурационные данные: метаданные, центры и коэффициенты виньетирования. 

* **example_input** - директория с 10 фотографиями равномерно освящённой стены каждого канала для тестирования.

* **example_output** - директория с полученными конфигурационными данными файлов в example_input.
