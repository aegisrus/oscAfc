# -*- coding: utf-8 -*-
"""
Модуль расчёта АЧХ (амплитудно-частотной характеристики) ПАЭ.
Портировано из MATLAB-алгоритма.
"""

import json
import os
from typing import Optional

import numpy as np
from scipy.ndimage import uniform_filter1d


def _default_config() -> dict:
    """Возвращает конфигурацию по умолчанию (из MATLAB)."""
    return {
        "refGT200": 92,
        "SGT200": 65,
        "unitADC": 3.05,
        "fD_kHz": 1000,
        "fft_size": 8192,
        "smooth_window": 50,
        "skip_bins": 300,
        "freq_range": [50, 500],
        "db_range": [10, 70],
    }


def load_ach_config(config_path: Optional[str] = None) -> dict:
    """
    Загружает конфигурацию АЧХ из JSON-файла.

    Ищет файл в порядке: config_path -> рядом с приложением -> %APPDATA%.
    При отсутствии файла возвращает значения по умолчанию.

    Returns:
        dict: Конфигурация с ключами refGT200, SGT200, unitADC, fD_kHz,
              fft_size, smooth_window, skip_bins, freq_range, db_range.
    """
    default = _default_config()

    search_paths = []
    if config_path and os.path.isfile(config_path):
        search_paths = [config_path]
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        appdata = os.environ.get("APPDATA", "")
        search_paths = [
            os.path.join(app_dir, "ach_config.json"),
            os.path.join(appdata, "oscAfc", "ach_config.json") if appdata else "",
        ]
        search_paths = [p for p in search_paths if p]

    for path in search_paths:
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Мержим с дефолтами, чтобы не потерять новые ключи
                return {**default, **loaded}
            except (json.JSONDecodeError, IOError):
                pass

    return default.copy()


def calc_ach(
    osc_data: np.ndarray,
    k_mkV: float,
    freq_khz: float,
    config: Optional[dict] = None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Рассчитывает АЧХ по осциллограмме.

    Алгоритм:
    1. Sref — абсолютная чувствительность: (20*log10(max*k_mkV) - refGT200) + SGT200
    2. FFT с дополнением до fft_size, берётся амплитудный спектр
    3. specVel = 20*log10(spec / (2*pi*f)) — переход к спектру скорости
    4. Сглаживание uniform_filter1d
    5. ref = Sref / max(specVel[skip_bins:])
    6. ach_db = specVel * ref

    Args:
        osc_data: Осциллограмма в ед. АЦП (np.ndarray)
        k_mkV: Коэффициент перевода АЦП -> мкВ для данной осциллограммы
        freq_khz: Частота дискретизации в кГц
        config: Конфиг (если None — загружается load_ach_config())

    Returns:
        tuple: (freq, ach_db, metadata)
            - freq: массив частот в кГц
            - ach_db: значения АЧХ в дБ отн. 1 В/(м/с)
            - metadata: dict с ключами Sabs (Sref), fmax, ref
    """
    if config is None:
        config = load_ach_config()

    ref_gt200 = config.get("refGT200", 92)
    s_gt200 = config.get("SGT200", 65)
    fft_size = config.get("fft_size", 8192)
    smooth_window = config.get("smooth_window", 50)
    skip_bins = config.get("skip_bins", 300)

    osc_data = np.asarray(osc_data, dtype=np.float64)

    # 1. Абсолютная чувствительность ПАЭ
    max_adc = np.max(np.abs(osc_data))
    max_uV = max_adc * k_mkV
    sref = (20 * np.log10(max_uV) - ref_gt200) + s_gt200

    # 2. FFT, амплитудный спектр (половина — односторонний)
    spec = np.abs(np.fft.fft(osc_data, n=fft_size))
    spec = spec[: fft_size // 2]

    # 3. Частоты и защита от деления на ноль при f=0
    n = len(spec)
    f = np.arange(n, dtype=np.float64) * freq_khz / fft_size
    # f[0]=0 даёт inf в specVel; заменяем нули на f[1] или 1e-10
    f_safe = np.where(f > 0, f, f[1] if n > 1 else 1e-10)

    # 4. Спектр скорости (в дБ)
    spec_vel = 20 * np.log10(spec / (2 * np.pi * f_safe))

    # 5. Сглаживание
    if smooth_window > 1:
        spec_vel = uniform_filter1d(spec_vel, size=smooth_window, mode="nearest")

    # 6. Нормировка
    region = spec_vel[skip_bins:]
    if len(region) == 0:
        ref = 1.0
    else:
        max_spec_vel = np.max(region)
        if np.isfinite(max_spec_vel) and max_spec_vel > 0:
            ref = sref / max_spec_vel
        else:
            ref = 1.0

    ach_db = spec_vel * ref

    # fmax — частота максимума в области skip_bins:
    idx_max = np.argmax(region) + skip_bins
    fmax = float(f[idx_max]) if idx_max < n else 0.0

    metadata = {"Sabs": sref, "fmax": fmax, "ref": ref}

    return f.copy(), ach_db, metadata
