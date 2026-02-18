# -*- coding: utf-8 -*-
"""
Точка входа приложения: SeeOSC + расчёт АЧХ.
Импортирует seeOSC и расширяет его функционалом АЧХ.
"""

import os
import sys

os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'  # До импорта pyqtgraph/Qt

import seeOSC
from ach_calculator import load_ach_config, calc_ach

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtWidgets import (
    QLabel, QVBoxLayout, QPushButton, QWidget, QSplitter,
    QMessageBox, QFileDialog,
)
from pyqtgraph.exporters import ImageExporter


class MainMenuWithACH(seeOSC.MainMenu):
    """Расширение MainMenu функционалом расчёта и сохранения АЧХ."""

    def _add_extra_buttons_after_nav(self) -> None:
        """Добавляет график АЧХ, кнопки и подключает авто-расчёт при смене осциллограммы."""
        self._ensure_ach_plot_exists()
        self.osc_now_changed.connect(self._recalc_ach_for_current)

        self.bttn_save_ach_png = QPushButton("Сохранить АЧХ в PNG")
        self.bttn_save_ach_png.clicked.connect(self._on_clicked_save_ach_png)
        self.bttn_save_ach_png.setEnabled(False)
        self.main_layout_v.addWidget(self.bttn_save_ach_png)

    def _ensure_ach_plot_exists(self) -> None:
        """Создаёт график АЧХ при первом расчёте с возможностью растягивания по ширине и высоте."""
        if hasattr(self, "now_plot_ach"):
            return
        self.now_plot_ach = pg.PlotWidget(parent=self)
        self.now_plot_ach.setTitle("АЧХ")
        self.now_plot_ach.showGrid(x=True, y=True)
        self.now_plot_ach.addLegend()
        self.now_plot_ach.setMinimumSize(QSize(400, 150))
        self.coords_label_ach = QLabel("X: —  Y: —")
        self.coords_label_ach.setStyleSheet("font-size: 11px; color: #666;")
        self.ach_container = QWidget()
        ach_vbox = QVBoxLayout(self.ach_container)
        ach_vbox.setContentsMargins(0, 0, 0, 0)
        ach_vbox.addWidget(self.now_plot_ach)
        ach_vbox.addWidget(self.coords_label_ach)
        self.ach_width_spacer = QWidget()
        self.ach_width_spacer.setMinimumSize(30, 30)
        self.ach_h_splitter = QSplitter(Qt.Horizontal)
        self.ach_h_splitter.addWidget(self.ach_container)
        self.ach_h_splitter.addWidget(self.ach_width_spacer)
        self.ach_h_splitter.setSizes([600, 50])
        self.ach_h_splitter.setStretchFactor(0, 1)
        self.ach_h_splitter.setStretchFactor(1, 0)
        self.plots_splitter.addWidget(self.ach_h_splitter)
        self.plots_splitter.setSizes([400, 200])
        self.now_plot_ach.scene().sigMouseMoved.connect(
            lambda pos, p=self.now_plot_ach, lbl=self.coords_label_ach:
            self._update_coords_label(pos, p, lbl)
        )

    def _open_osc(self, name_osc: str) -> None:
        """Переопределение: после загрузки файла автоматически рассчитываем АЧХ."""
        super()._open_osc(name_osc)
        if hasattr(self, "osc_file") and hasattr(self, "num_osc"):
            self._recalc_ach_for_current()

    def _recalc_ach_for_current(self, _osc_index=None) -> None:
        """Рассчитывает АЧХ для текущей осциллограммы. Вызывается при смене кадра (сигнал osc_now_changed)."""
        if not hasattr(self, "osc_file") or not hasattr(self, "num_osc"):
            return
        idx_from = idx_to = self.osc_now

        self._ensure_ach_plot_exists()

        config = load_ach_config()
        freq_range = config.get("freq_range", [50, 500])
        db_range = config.get("db_range", [10, 70])
        fD_default = config.get("fD_kHz", 1000)

        if idx_from < self.start_data_osc or idx_to >= self.end_data_osc:
            batch_start = max(0, (idx_from // 500) * 500)
            batch_end = min(self.num_osc, batch_start + max(500, idx_to - idx_from + 1))
            osc_batch = np.array(self.osc_file.getDotsOSC(batch_start, batch_end))
            k_mkV_batch = np.array(self.osc_file.get_K_mkV(batch_start, batch_end))
        else:
            batch_start = self.start_data_osc
            osc_batch = self.osc_datas
            k_mkV_batch = self.K_mkV

        self.now_plot_ach.clear()
        colors = [
            (255, 0, 0, 180), (0, 128, 0, 180), (0, 0, 255, 180),
            (255, 165, 0, 180), (148, 0, 211, 180), (255, 192, 203, 180),
        ]

        for i, idx in enumerate(range(idx_from, idx_to + 1)):
            local_idx = idx - batch_start
            osc_data = osc_batch[local_idx]
            k_mkV = float(k_mkV_batch[local_idx])
            try:
                freq_osc = self.osc_file.oscDefMod[idx].freq
            except (AttributeError, IndexError):
                freq_osc = fD_default
            freq_arr, ach_db, _ = calc_ach(osc_data, k_mkV, freq_osc, config)
            mask = (freq_arr >= freq_range[0]) & (freq_arr <= freq_range[1])
            f_plot = freq_arr[mask]
            a_plot = ach_db[mask]
            color = colors[i % len(colors)]
            curve_name = f"№ {idx + 1}"
            self.now_plot_ach.plot(f_plot, a_plot, pen=pg.mkColor(color), name=curve_name)

        self.now_plot_ach.setXRange(freq_range[0], freq_range[1])
        self.now_plot_ach.setYRange(db_range[0], db_range[1])
        self.now_plot_ach.setLabel("bottom", "Частота, кГц")
        self.now_plot_ach.setLabel("left", "дБ отн. 1 В/(м/с)")
        self.bttn_save_ach_png.setEnabled(True)

    def _on_clicked_save_ach_png(self) -> None:
        """Сохраняет график АЧХ в PNG."""
        if not hasattr(self, "now_plot_ach"):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить АЧХ", "", "PNG (*.png)"
        )
        if not path:
            return
        if not path.endswith(".png"):
            path += ".png"
        exporter = ImageExporter(self.now_plot_ach.plotItem)
        exporter.export(path)


class App(seeOSC.SeeOSC):
    """Главное окно приложения с поддержкой АЧХ."""

    def create_menu(self):
        self.menu = MainMenuWithACH()
        self.setCentralWidget(self.menu)
        self.show()


if __name__ == "__main__":
    try:
        app = QtWidgets.QApplication([])
        ex = App()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "Критическая ошибка", f"Критическая ошибка: {e}")
