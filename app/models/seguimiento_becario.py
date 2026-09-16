"""Entidad SeguimientoBecario — HU-05/HU-08 (tabla creada en init_db).

Representa el seguimiento de UN becario en UNA gestión académica
(porcentajes, horas becarias, materias, carpeta y carta). Los datos son
por gestión/período, NO fijos del becario, por eso vive en tabla aparte
vinculada por becario_id en vez de columnas en Becario (HU-02).

SQL aplicado por app/persistence/database.py:

    CREATE TABLE IF NOT EXISTS seguimiento_becario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        becario_id INTEGER NOT NULL REFERENCES becario(id),
        gestion TEXT NOT NULL,
        porcentaje_anterior TEXT NOT NULL DEFAULT '0%',
        porcentaje_gestion TEXT NOT NULL DEFAULT '0%',
        horas_becarias INTEGER NOT NULL DEFAULT 0,
        materias_en_orden INTEGER NOT NULL DEFAULT 0,
        carpeta_cancelada INTEGER NOT NULL DEFAULT 0,
        carta_renovacion INTEGER NOT NULL DEFAULT 0,
        UNIQUE (becario_id, gestion)
    );

Recomendación aplicada: tabla aparte (este archivo), no columnas en Becario,
porque cada gestión genera una fila nueva por becario y así no se
rompe lo definido en HU-02.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SeguimientoBecario:
    id: Optional[int]
    becario_id: int
    gestion: str
    porcentaje_anterior: str = "0%"
    porcentaje_gestion: str = "0%"
    horas_becarias: bool = False
    materias_en_orden: bool = False
    carpeta_cancelada: bool = False
    carta_renovacion: bool = False
