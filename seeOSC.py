# Версия SeeOsc без открытия ald файла

import inspect
import os
import sys

os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5' # Устанавливаю переменную окружения для pyqtgraph

import numpy as np
import pyqtgraph as pg

from numba import njit
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtWidgets import (QWidget, QPushButton,
                             QLabel, QVBoxLayout,
                             QHBoxLayout, QMessageBox,
                             QMainWindow, QFileDialog,
                             QLayout, QLineEdit, QFrame,
                             QSplitter)
from PyQt5.QtGui import QFontDatabase, QFont

import Aegis_osc

from Fourier import Fourier, four2
from work_with_osc import DataOsc, get_dB_osc


LOG_LEVEL = Aegis_osc.LogLevel


@njit
def set_K_mkV_and_dB(end_data_osc: int, K_mkV: np.ndarray, osc_datas: np.ndarray) -> np.ndarray:
    """Метод рассчитывает Децибелы для осциллограммы"""
    dB_data = np.zeros(end_data_osc, dtype=np.int32)  # Массив с нужной длиной
    for i in range(end_data_osc):
        dB_data[i] = np.int32(get_dB_osc(osc_datas[i], K_mkV[i]))
    return dB_data

class MainMenu(QWidget):
    # Создаем сигнал, который уведомит об отображении графиков
    graphs_shown = pyqtSignal()
    osc_now_changed = pyqtSignal(object)

    def __init__(self):
        super().__init__()  # Вызываю конструктор родительского класса QWidget
        self.__set_style_for_app()
        self.logger = Aegis_osc.Logger("log_seeOSC.txt")

        self.dB_text = None
        self.text = None
        self.now_plot_spectr_item = None
        self.now_plot_osc_item = None
        self.main_layout_v = QVBoxLayout(self)
        self.main_layout_v.setSizeConstraint(QLayout.SetMinimumSize)
        self.layout_num_osc_h = QHBoxLayout()
        self.edit_osc_num = QLineEdit()
        self.edit_osc_widget = QWidget()
        self.bttn_goto_osc = QPushButton("Перейти")

        # Кнопка для получения открытия отдельной осциллограммы
        self.startWidget = QWidget(self)
        self.startVLayout = QVBoxLayout(self)
        self.bttn_open_alone_osc = QPushButton()
        self.bttn_open_alone_osc.setText("открыть osc")
        self.bttn_open_alone_osc.clicked.connect(self._on_clicked_bttn_open_osc)
        self.startVLayout.addWidget(self.bttn_open_alone_osc)
        self.startWidget.setLayout(self.startVLayout)
        self.startWidget.setMinimumSize(300, 150)

        self.file_open = QLabel(self)
        self.info_now_num_osc = QLabel(self)

        # Блок добавления элементов в главное меню
        self.main_layout_v.addWidget(self.startWidget)

    def _on_clicked_bttn_open_osc(self) -> None:
        """Обработчик события клика для кнопки создания нового датасета"""
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "osc files (*.osc)")

        self._open_osc(path)

    def _open_osc(self, name_osc: str):
        try:
            self.startWidget.setMinimumSize(0, 0)  # Сбрасываем ограничения на размер виджета

            self.name_osc = name_osc

            self.logger.logg(LOG_LEVEL._INFO_, f"Открытие файла .osc: {self.name_osc}",
                        os.path.basename(__file__),
                        inspect.currentframe().f_lineno, 
                        inspect.currentframe().f_code.co_name)
            self.osc_file = Aegis_osc.File_osc(self.name_osc, self.logger)

            self.file_open.setText(f"Открыт файл .osc: {self.name_osc}")
            self.num_osc = self.osc_file.sdoHdr.NumOSC

            # Предварительная инициализация массивов
            self.start_data_osc = 0
            self.end_data_osc = min(self.num_osc, 500)

            # Получаем данные и инициализируем массивы заранее
            self.logger.logg(LOG_LEVEL._INFO_, f"Получение данных из файла .osc",
                        os.path.basename(__file__),
                        inspect.currentframe().f_lineno, 
                        inspect.currentframe().f_code.co_name)
            self.osc_datas = np.array(self.osc_file.getDotsOSC(0, self.end_data_osc))  
                      
            # Заполняем массивы за один проход, без использования np.append
            self.logger.logg(LOG_LEVEL._INFO_, f"Старт получения K_mkV",
                        os.path.basename(__file__),
                        inspect.currentframe().f_lineno, 
                        inspect.currentframe().f_code.co_name)
            self.K_mkV = np.array(self.osc_file.get_K_mkV(0, self.end_data_osc))
            self.logger.logg(LOG_LEVEL._INFO_, f"Конец получения K_mkV",
                        os.path.basename(__file__),
                        inspect.currentframe().f_lineno, 
                        inspect.currentframe().f_code.co_name)
            self.logger.logg(LOG_LEVEL._INFO_, f"Старт получения децибел",
                    os.path.basename(__file__),
                    inspect.currentframe().f_lineno, 
                    inspect.currentframe().f_code.co_name)
            self.dB_data = set_K_mkV_and_dB(self.end_data_osc, self.K_mkV, self.osc_datas)
            self.logger.logg(LOG_LEVEL._INFO_, f"Конец получения децибел",
                        os.path.basename(__file__),
                        inspect.currentframe().f_lineno, 
                        inspect.currentframe().f_code.co_name)
            self.osc_now = 0
            if not hasattr(self, "now_plot_osc"):
                self.logger.logg(LOG_LEVEL._INFO_, f"Создание графиков и их отображение",
                        os.path.basename(__file__),
                        inspect.currentframe().f_lineno,
                        inspect.currentframe().f_code.co_name)
                self.now_plot_osc = pg.PlotWidget(parent=self)
                self.now_plot_spectr = pg.PlotWidget(parent=self)

                self.now_plot_osc.setTitle("Осциллограмма")
                self.now_plot_spectr.setTitle("Спектр осциллограммы")
                self.now_plot_osc.showGrid(x=True, y=True)
                self.now_plot_spectr.showGrid(x=True, y=True)

                self.now_plot_osc.setMinimumSize(QSize(600, 250))
                self.now_plot_osc.setMaximumHeight(400)
                self.now_plot_spectr.setMinimumSize(QSize(600, 250))
                self.now_plot_spectr.setMaximumHeight(400)

                # Метки координат курсора для осциллограммы и спектра
                self.coords_label_osc = QLabel("X: —  Y: —")
                self.coords_label_spectr = QLabel("X: —  Y: —")
                for lbl in (self.coords_label_osc, self.coords_label_spectr):
                    lbl.setStyleSheet("font-size: 11px; color: #666;")
                # Контейнеры: график + метка координат X/Y (осциллограмма и спектр)
                self.plot_layout_h = QHBoxLayout()
                for plot, lbl in [
                    (self.now_plot_osc, self.coords_label_osc),
                    (self.now_plot_spectr, self.coords_label_spectr),
                ]:
                    container = QWidget()
                    vbox = QVBoxLayout(container)
                    vbox.setContentsMargins(0, 0, 0, 0)
                    vbox.addWidget(plot)
                    vbox.addWidget(lbl)
                    self.plot_layout_h.addWidget(container)

                # Верхняя часть: осциллограмма и спектр (без растягивания)
                self.top_plots_widget = QWidget()
                self.top_plots_widget.setLayout(self.plot_layout_h)

                self.plots_splitter = QSplitter(Qt.Vertical)
                self.plots_splitter.addWidget(self.top_plots_widget)

                self.now_plot_osc.scene().sigMouseMoved.connect(
                    lambda pos, p=self.now_plot_osc, lbl=self.coords_label_osc:
                    self._update_coords_label(pos, p, lbl)
                )
                self.now_plot_spectr.scene().sigMouseMoved.connect(
                    lambda pos, p=self.now_plot_spectr, lbl=self.coords_label_spectr:
                    self._update_coords_label(pos, p, lbl)
                )

                self.main_layout_v.addWidget(self.file_open)

                self.layout_num_osc_h.addWidget(self.info_now_num_osc)
                self.layout_num_osc_h.addWidget(self.get_separator())
                self.layout_num_osc_h.addWidget(QLabel("№ осциллограммы:"))
                self.layout_num_osc_h.addWidget(self.edit_osc_num)
                self.layout_num_osc_h.addWidget(self.bttn_goto_osc)
                self.layout_num_osc_h.addStretch()
                
                self.main_layout_v.addLayout(self.layout_num_osc_h)

                self.main_layout_v.addWidget(self.plots_splitter)

                # Поле ввода номера осциллограммы и кнопка перехода
                self.edit_osc_num.setMaximumWidth(120)
                self.edit_osc_num.returnPressed.connect(self._goto_osc_by_edit)
                self.bttn_goto_osc.clicked.connect(self._goto_osc_by_edit)
                self.edit_osc_widget.setLayout(self.layout_num_osc_h)
                self.main_layout_v.addWidget(self.edit_osc_widget)

            if hasattr(self, "edit_osc_num"):
                self.edit_osc_num.setPlaceholderText(f"1 - {self.num_osc}")
            self.now_plot_osc.clear()
            self.now_plot_spectr.clear()

            self.info_now_num_osc.setText(f"Номер кадра: {self.osc_now + 1} из {self.num_osc}")
            self.now_plot_osc_item = self.now_plot_osc.plot(self.osc_datas[self.osc_now])

            self.logger.logg(LOG_LEVEL._INFO_, f"Построение спектра осциллограммы",
                        os.path.basename(__file__),
                        inspect.currentframe().f_lineno, 
                        inspect.currentframe().f_code.co_name)
            spectr = four2(np.array(self.osc_datas[self.osc_now], dtype=np.float64))
            x = np.array([i / (len(spectr) / 2 / 500) for i in range(round(len(spectr) / 2))])
            self.now_plot_spectr_item = self.now_plot_spectr.plot(x, spectr[:round(len(spectr) / 2)])
            # Добавляем информацию о том, какая частота более выражена в сигнале
            index = np.argmax(spectr[:round(len(spectr) / 2)])
            self.text = pg.TextItem(f"{x[index]} кГц", anchor=(0, 1), color="r")
            self.now_plot_spectr.addItem(self.text)

            # Связываем изменение диапазона графика с обновлением позиции текста
            self.now_plot_spectr.sigRangeChanged.connect(self.__update_info_position)

            # Добавляем информацию о децибелах
            self.dB_text = pg.TextItem(f"{self.dB_data[self.osc_now]} Дб", anchor=(0, 1), color="r")
            self.now_plot_osc.addItem(self.dB_text)

            self.__update_info_position()

            # Связываем изменение диапазона графика с обновлением позиции текста
            self.now_plot_osc.sigRangeChanged.connect(self.__update_info_position)

            # self.plot_layout_h.addWidget(pg.plot(self.osc_datas[self.osc_now]))
            if (not hasattr(self, "bttn_next_osc") and
                    not hasattr(self, "bttn_prev_osc")):
                self.logger.logg(LOG_LEVEL._INFO_, f"Создание кнопок для переключения между осциллограммами",
                        os.path.basename(__file__),
                        inspect.currentframe().f_lineno, 
                        inspect.currentframe().f_code.co_name)
                self.bttn_next_osc = QPushButton("Следующая осциллограмма")
                self.bttn_prev_osc = QPushButton("Предыдущая осциллограмма")
                self.bttn_next_osc.clicked.connect(self.open_next_osc)
                self.bttn_prev_osc.clicked.connect(self.open_prev_osc)
                self.main_layout_v.addWidget(self.bttn_next_osc)
                self.main_layout_v.addWidget(self.bttn_prev_osc)

                self._add_extra_buttons_after_nav()
            self.check_next_prev_osc()
            # Отправляем сигнал о том, что графики были отображены
            self.adjustSize()
            self.graphs_shown.emit()
        except Exception as e:
            self.logger.logg(LOG_LEVEL._CRITICAL_, f"Ошибка при открытии файла OSC: {e}",
                        os.path.basename(__file__),
                        inspect.currentframe().f_lineno, 
                        inspect.currentframe().f_code.co_name)

    def _update_coords_label(self, evt, plot_widget, label: QLabel) -> None:
        """Обновляет метку с координатами X/Y при движении курсора над графиком."""
        pos = evt[0] if isinstance(evt, (tuple, list)) and evt else evt
        vb = plot_widget.plotItem.vb
        if vb.sceneBoundingRect().contains(pos):
            mouse_point = vb.mapSceneToView(pos)
            label.setText(f"X: {mouse_point.x():.3g}  Y: {mouse_point.y():.3g}")
        else:
            label.setText("X: —  Y: —")

    def __update_info_position(self) -> None:
        """Обновляет позицию текстового элемента в правом верхнем углу графика."""
        graph = self.sender()

        if graph == self.now_plot_osc:
            y_min, y_max = self.now_plot_osc_item.dataBounds(1)
            x_min, x_max = self.now_plot_osc_item.dataBounds(0)
            x_width = x_max - x_min
            y_height = y_max - y_min
            delta_x = x_width * 0.85
            delta_y = y_height * 0.9
            # Устанавливаем текст в правый верхний угол с небольшим отступом
            self.dB_text.setPos(x_min + delta_x, y_min + delta_y)
            return
        elif graph == self.now_plot_spectr:
            y_min, y_max = self.now_plot_spectr_item.dataBounds(1)
            x_min, x_max = self.now_plot_spectr_item.dataBounds(0)
            x_width = x_max - x_min
            y_height = y_max - y_min
            delta_x = x_width * 0.85
            delta_y = y_height * 0.9
            # Устанавливаем текст в правый верхний угол с небольшим отступом
            self.text.setPos(x_min + delta_x, y_min + delta_y)
            return
        else:
            # Если метод вызван напрямую, то устанавливаем инфо-текст в верхний правый угол у обоих графиков
            # для self.now_plot_osc
            y_min, y_max = self.now_plot_osc_item.dataBounds(1)
            x_min, x_max = self.now_plot_osc_item.dataBounds(0)
            x_width = x_max - x_min
            y_height = y_max - y_min
            delta_x = x_width * 0.85
            delta_y = y_height * 0.9
            # Устанавливаем текст в правый верхний угол с небольшим отступом
            self.dB_text.setPos(x_min + delta_x, y_min + delta_y)

            # для self.now_plot_spectr
            y_min, y_max = self.now_plot_spectr_item.dataBounds(1)
            x_min, x_max = self.now_plot_spectr_item.dataBounds(0)
            x_width = x_max - x_min
            y_height = y_max - y_min
            delta_x = x_width * 0.85
            delta_y = y_height * 0.9
            # Устанавливаем текст в правый верхний угол с небольшим отступом
            self.text.setPos(x_min + delta_x, y_min + delta_y)
        return

    def __load_prev_osc(self):
        if self.osc_now <= 0:
            return
        self.end_data_osc = self.start_data_osc
        self.start_data_osc = self.start_data_osc - 500 if (self.start_data_osc - 500) > 0 else 0
        self.osc_datas = np.array(self.osc_file.getDotsOSC(self.start_data_osc, self.end_data_osc))

        self.K_mkV = np.array(self.osc_file.get_K_mkV(self.start_data_osc, self.end_data_osc))
        self.dB_data = np.array(([get_dB_osc(self.osc_datas[i], self.K_mkV[i])
                                  for i in range(0, self.end_data_osc - self.start_data_osc)]))

    def __load_next_osc(self):
        if self.osc_now >= self.num_osc - 1:
            return
        self.start_data_osc = self.end_data_osc
        self.end_data_osc = self.end_data_osc + 500 if (self.num_osc - self.osc_now) > 500 else self.num_osc
        self.osc_datas = np.array(self.osc_file.getDotsOSC(self.start_data_osc, self.end_data_osc))

        self.K_mkV = np.array(self.osc_file.get_K_mkV(self.start_data_osc, self.end_data_osc))
        self.dB_data = np.array(([get_dB_osc(self.osc_datas[i], self.K_mkV[i])
                                  for i in range(0, self.end_data_osc - self.start_data_osc)]))

    def keyPressEvent(self, event):
        """
        Переопределение метода обработки событий нажатия клавиш
        """
        if event.key() == Qt.Key_Left:
            self.open_prev_osc()
        elif event.key() == Qt.Key_Right:
            self.open_next_osc()
        else:
            event.ignore()  # Позволяет обработать событие другим обработчикам


    def _goto_osc_by_edit(self) -> None:
        """Переход к осциллограмме по номеру из поля edit."""
        text = self.edit_osc_num.text().strip()
        if not text:
            return
        try:
            num = int(text)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", f"Введите число от 1 до {self.num_osc}")
            return
        if num < 1 or num > self.num_osc:
            QMessageBox.warning(self, "Ошибка", f"Введите число от 1 до {self.num_osc}")
            return
        target_index = num - 1  # 0-based
        if target_index == self.osc_now:
            return
        # Загружаем данные, если целевая осциллограмма вне текущего диапазона
        if target_index < self.start_data_osc or target_index >= self.end_data_osc:
            self.start_data_osc = (target_index // 500) * 500
            self.end_data_osc = min(self.start_data_osc + 500, self.num_osc)
            self.osc_datas = np.array(self.osc_file.getDotsOSC(self.start_data_osc, self.end_data_osc))
            self.K_mkV = np.array(self.osc_file.get_K_mkV(self.start_data_osc, self.end_data_osc))
            self.dB_data = np.array([get_dB_osc(self.osc_datas[i], self.K_mkV[i])
                                    for i in range(self.end_data_osc - self.start_data_osc)])
        self.osc_now = target_index
        now_ind = self.osc_now - self.start_data_osc
        self.now_plot_osc.clear()
        self.now_plot_spectr.clear()
        self.info_now_num_osc.setText(f"Номер кадра: {self.osc_now + 1} из {self.num_osc}")
        self.now_plot_osc_item = self.now_plot_osc.plot(self.osc_datas[now_ind])
        spectr = four2(np.array(self.osc_datas[now_ind], dtype=np.float64))
        x = [i / (len(spectr) / 2 / 500) for i in range(round(len(spectr) / 2))]
        self.now_plot_spectr_item = self.now_plot_spectr.plot(x, spectr[:round(len(spectr) / 2)])
        index = np.argmax(spectr[:round(len(spectr) / 2)])
        self.text = pg.TextItem(f"{x[index]} кГц", anchor=(0, 1), color="r")
        self.now_plot_spectr.addItem(self.text)
        self.dB_text = pg.TextItem(f"{self.dB_data[now_ind]} Дб", anchor=(0, 1), color="r")
        self.now_plot_osc.addItem(self.dB_text)
        self.__update_info_position()
        self.check_next_prev_osc()
        self.osc_now_changed.emit(self.osc_now)

    def check_next_prev_osc(self) -> None:
        if self.osc_now + 1 >= self.num_osc:
            self.bttn_next_osc.setEnabled(False)
        elif not self.bttn_next_osc.isEnabled():
            self.bttn_next_osc.setEnabled(True)
        if self.osc_now <= self.start_data_osc:
            self.bttn_prev_osc.setEnabled(False)
        elif not self.bttn_prev_osc.isEnabled():
            self.bttn_prev_osc.setEnabled(True)

    def open_next_osc(self) -> None:
        if self.osc_now >= self.end_data_osc - 1:
            self.__load_next_osc()
            self.check_next_prev_osc()
            if not self.bttn_next_osc.isEnabled():
                return

        self.osc_now += 1
        self.now_plot_osc.clear()
        self.now_plot_spectr.clear()

        self.info_now_num_osc.setText(f"Номер кадра: {self.osc_now + 1} из {self.num_osc}")

        now_ind = self.osc_now - self.start_data_osc
        self.now_plot_osc_item = self.now_plot_osc.plot(self.osc_datas[now_ind])
        spectr = four2(np.array(self.osc_datas[now_ind], dtype=np.float64))
        x = [i / (len(spectr) / 2 / 500) for i in range(round(len(spectr) / 2))]
        self.now_plot_spectr_item = self.now_plot_spectr.plot(x, spectr[:round(len(spectr) / 2)])

        # Добавляем информацию о том, какя частота более выражена в сигнале
        index = np.argmax(spectr[:round(len(spectr) / 2)])
        self.text = pg.TextItem(f"{x[index]} кГц", anchor=(0, 1), color="r")
        self.now_plot_spectr.addItem(self.text)

        # Добавляем информацию децибелах
        self.dB_text = pg.TextItem(f"{self.dB_data[now_ind]} Дб", anchor=(0, 1), color="r")
        self.now_plot_osc.addItem(self.dB_text)

        self.__update_info_position()
        self.check_next_prev_osc()

        # Отправляем сигнал о том, что номер осциллограммы изменился
        self.osc_now_changed.emit(self.osc_now)

    def open_prev_osc(self) -> None:
        if self.osc_now == 0:
            return
        
        if self.osc_now <= (self.start_data_osc - 1):
            self.__load_prev_osc()
            self.check_next_prev_osc()
            if not self.bttn_prev_osc.isEnabled():
                return
        self.osc_now -= 1
        self.now_plot_osc.clear()
        self.now_plot_spectr.clear()

        self.info_now_num_osc.setText(f"Номер кадра: {self.osc_now + 1} из {self.num_osc}")

        now_ind = self.osc_now - self.start_data_osc
        self.now_plot_osc_item = self.now_plot_osc.plot(self.osc_datas[now_ind])
        spectr = four2(np.array(self.osc_datas[now_ind], dtype=np.float64))
        x = [i / (len(spectr) / 2 / 500) for i in range(round(len(spectr) / 2))]
        self.now_plot_spectr_item = self.now_plot_spectr.plot(x, spectr[:round(len(spectr) / 2)])

        # Добавляем текст (аннотацию)
        index = np.argmax(spectr[:round(len(spectr) / 2)])
        self.text = pg.TextItem(f"{x[index]} кГц", anchor=(0, 1), color="r")
        self.now_plot_spectr.addItem(self.text)

        # Добавляем информацию децибелах
        self.dB_text = pg.TextItem(f"{self.dB_data[now_ind]} Дб", anchor=(0, 1), color="r")
        self.now_plot_osc.addItem(self.dB_text)

        self.__update_info_position()
        self.check_next_prev_osc()

        # Отправляем сигнал о том, что номер осциллограммы изменился
        self.osc_now_changed.emit(self.osc_now)

    def _add_extra_buttons_after_nav(self) -> None:
        """Переопределите в подклассе для добавления кнопок после навигации."""
        pass

    def get_separator(self) -> QFrame:
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        # Стилизация через CSS
        separator.setStyleSheet("""
            QFrame {
                background-color: gray;  /* Цвет линии */
                margin: 5px 0px;  /* Отступы сверху и снизу */
            }
        """)
        
        # Фиксированная ширина (опционально)
        separator.setFixedWidth(1)
        
        return separator

    def __set_style_for_app(self) -> None:
        """Устанавливает стиль для приложения."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #fff;
            }
            QLabel {
                font-size: 13px;
            }
            QPushButton {
                font-size: 12px;
                padding: 5px;
            }
            """)


class SeeOSC(QMainWindow):
    def __init__(self):
        super().__init__()
        self.menu = None
        self.create_menu()

    def create_menu(self):
        self.menu = MainMenu()

        self.setCentralWidget(self.menu)
        self.show()


if __name__ == "__main__":
    try:
        app = QtWidgets.QApplication([])
        ex = SeeOSC()
        sys.exit(app.exec())
    except Exception as e:
        QMessageBox.critical(None, "Критическая ошибка", f"Критическая ошибка: {e}")
