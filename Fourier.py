import os
import sys

import numpy as np

from numba import njit

# Теперь импортируем модуль для работы с osc
module_path = os.path.abspath("./")
sys.path.append(module_path)
try:
    import Aegis_osc
except ImportError as e:
    raise "Не удалось импортировать модуль для работы с осциллограммами!"


@njit
def fill_dataset_for_nulls(signal: np.ndarray, target_len: int):
    """Добавляет нули в конец NumPy массива до определённой длины."""
    current_len = len(signal)
    if current_len < target_len:
        fill_len = target_len - current_len
        signal = np.concatenate((signal, np.zeros(fill_len, dtype=signal.dtype)))
    return signal


@njit
def four2(signal: np.ndarray, d: int = -1) -> np.ndarray:
    """
    Реализация алгоритма БПФ на Python на основе кода из книги В.П. Дьяконова.

    Параметры:
    x - массив входных данных (вещественная часть)
    D - направление преобразования (-1 для прямого БПФ, 1 для обратного БПФ)
    """
    m = 1
    val = 1
    while val < len(signal):
        val <<= 1
        m += 1
    if len(signal) < 2 ** m:
        signal = fill_dataset_for_nulls(signal, 2 ** m)
    n = 1 << m  # N = 2^M
    y = np.zeros(n)  # массив для мнимой части

    # Прямое или обратное БПФ
    for l in range(1, m + 1):
        e = 1 << (m + 1 - l)
        f = e >> 1
        u = 1.0
        v = 0.0

        z = np.pi / f
        c = np.cos(z)
        s = d * np.sin(z)

        for j in range(1, f + 1):
            for i in range(j, n + 1, e):
                o = i + f - 1
                p = signal[i - 1] + signal[o]
                q = y[i - 1] + y[o]  # мнимая часть
                r = signal[i - 1] - signal[o]
                t = y[i - 1] - y[o]  # мнимая часть
                signal[o] = r * u - t * v
                y[o] = t * u + r * v
                signal[i - 1] = p
                y[i - 1] = q

            w = u * c - v * s
            v = v * c + u * s
            u = w

    # Перестановка элементов (битовая инверсия)
    j = 1
    for i in range(1, n):
        if i < j:
            j1 = j - 1
            i1 = i - 1
            # Обмен вещественной и мнимой частей
            signal[j1], signal[i1] = signal[i1], signal[j1]
            y[j1], y[i1] = y[i1], y[j1]
        k = n >> 1
        while k < j:
            j -= k
            k >>= 1
        j += k

    # Прямое или обратное БПФ
    if d < 0:  # прямое БПФ
        for k in range(n):
            a = np.sqrt(signal[k] ** 2 + y[k] ** 2)
            signal[k] = a * 2.0 / n
    else:  # обратное БПФ
        for k in range(n):
            signal[k] /= n
            y[k] /= n

    signal[0] = 0
    return signal


class Fourier:
    @staticmethod
    def __find_closest_power(self, number):
        """
        Находит ближайшую степень двойки для заданного числа.

        Параметры:
        number - целое число

        Возвращает:
        power - ближайшая степень двойки (в виде целого числа)
        """
        power = 0
        number -= 1
        while number > 0:
            number >>= 1
            power += 1
        return power

    @staticmethod
    def abs_values_of_spectr(self, file_osc: Aegis_osc.File_osc, num_osc: int) -> tuple[list, list]:
        buf_size_max = max(2048, (1 << (self.__find_closest_power(file_osc.oscDefMod[num_osc].buf_size_max - 1))))
        spectr_buf_size = 1 << (self.__find_closest_power(file_osc.oscDefMod[num_osc].buf_size) - 1)
        # interval = file_osc.oscDefMod[num_osc].freq / 25 * buf_size_max / spectr_buf_size

        osc = file_osc.getDotOSC(6)
        length_osc = len(osc)
        M = self.__find_closest_power(length_osc)
        osc.extend([0 for _ in range((2 << M - 1) - length_osc)])

        # Выполнение прямого БПФ
        spectra = self.four2(osc.copy(), M, D=-1)
        spectra[0] = 0

        K_mkV = file_osc.oscDefMod[num_osc].K_mkV
        freq = file_osc.oscDefMod[num_osc].freq
        x = []
        y = []
        for i in range(spectr_buf_size):
            # x.append(round(i * interval))
            x.append(i / (spectr_buf_size / 500))
            y.append(round(spectra[i] * K_mkV / freq * 2896309))
        return x, y
