"""Configuración centralizada de auditoría: archivos de logs (sin base de datos)."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOG_FILE = BASE / "logs" / "sistema.log"


def obtener_logger() -> logging.Logger:
    """Devuelve un único logger compartido, con rotación para limitar tamaño."""
    logger = logging.getLogger("software_fj")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_FILE, maxBytes=2_000_000, backupCount=2, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def leer_logs(max_lineas: int = 200) -> str:
    """Muestra solamente las últimas líneas de los eventos registrados."""
    if not LOG_FILE.exists():
        return "Todavía no hay eventos registrados."
    from collections import deque

    with LOG_FILE.open("r", encoding="utf-8", errors="replace") as archivo:
        lineas = deque(archivo, maxlen=max_lineas)
    return "".join(lineas) or "Todavía no hay eventos registrados."
