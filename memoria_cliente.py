# -*- coding: utf-8 -*-
"""Memoria de clasificaciones por cliente (modo Claude Haiku).

Una noticia que ya se clasificó para el mismo cliente, con la misma
configuración, no vuelve al modelo: hereda su tono, subtema y tema. Ahorra
tiempo y costo al repetir un dossier o cuando una nota reaparece otro día,
y da el mismo resultado entre corridas.

La memoria vive junto al historial (``HISTORIAL_DIR`` o ``./historial``), un
JSON por cliente: ``memoria_<cliente>.json``. Solo sirve si la *huella* de
la configuración coincide (marca, alias, voceros, criterio, guía, temas,
PKL y versión de las instrucciones del motor): si algo de eso cambia, la
memoria anterior se descarta. Todo es best-effort: ningún error de lectura
o escritura interrumpe la corrida.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from historial_cliente import _dir_historial, _slug

DIAS_MAX = 45          # una entrada sin usar más de esto se descarta
MAX_ENTRADAS = 20000


def _n(texto: Any) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t.lower()).split())


def clave(titulo: str, contexto: str) -> str:
    """Identidad de la noticia: título y comienzo del Contexto analizado."""
    return hashlib.sha1((_n(titulo) + "|" + _n(contexto)[:400]).encode()).hexdigest()[:20]


def huella(config: dict) -> str:
    """Huella de todo lo que cambia el resultado de la clasificación."""
    return hashlib.sha1(json.dumps(config, ensure_ascii=False, sort_keys=True,
                                   default=str).encode()).hexdigest()[:16]


def _ruta(brand: str, extra=None) -> str:
    return os.path.join(_dir_historial(extra), "memoria_%s.json" % _slug(brand))


def cargar(brand: str, huella_actual: str, extra=None) -> Dict[str, dict]:
    """{clave: {tono, subtema, tema, fecha}} vigente para esta configuración."""
    try:
        with open(_ruta(brand, extra), encoding="utf-8") as f:
            data = json.load(f)
        if data.get("huella") != huella_actual:
            return {}
        limite = (datetime.now() - timedelta(days=DIAS_MAX)).isoformat(timespec="seconds")
        return {k: v for k, v in (data.get("entradas") or {}).items()
                if isinstance(v, dict) and str(v.get("fecha") or "") >= limite}
    except (OSError, ValueError, AttributeError):
        return {}


def guardar(brand: str, huella_actual: str, nuevas: Dict[str, dict], extra=None) -> int:
    """Fusiona `nuevas` con la memoria vigente. Devuelve cuántas quedaron."""
    try:
        entradas = cargar(brand, huella_actual, extra)
        ahora = datetime.now().isoformat(timespec="seconds")
        for k, v in (nuevas or {}).items():
            entradas[k] = dict(v, fecha=ahora)
        if len(entradas) > MAX_ENTRADAS:
            mas_nuevas = sorted(entradas.items(), key=lambda kv: kv[1].get("fecha") or "",
                                reverse=True)[:MAX_ENTRADAS]
            entradas = dict(mas_nuevas)
        ruta = _ruta(brand, extra)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ruta), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"huella": huella_actual, "entradas": entradas}, f, ensure_ascii=False)
        os.replace(tmp, ruta)
        return len(entradas)
    except (OSError, ValueError):
        return 0


def borrar(brand: str, extra=None) -> bool:
    try:
        os.remove(_ruta(brand, extra))
        return True
    except OSError:
        return False


# ============================================================================
# v1.37: memoria de SUBTEMAS para el boletín (corridas cada 30-60 minutos).
# Independiente de la memoria de clasificaciones: no depende de la huella
# de configuración ni de la versión del motor, así un ajuste del perfil o
# una versión nueva no borra los subtemas del día. Guarda por noticia el
# título, el comienzo del texto y el Subtema_IA final; en la corrida
# siguiente una noticia igual o muy parecida hereda ese subtema.
# ============================================================================
DIAS_SUBTEMAS = 3        # el boletín es diario: tres días bastan
MAX_SUBTEMAS = 6000
UMBRAL_TITULO = 0.80     # Jaccard de palabras de contenido del titular
UMBRAL_TEXTO = 0.70      # Jaccard de 3-gramas del comienzo del texto

_VACIAS = set("""a al ante con contra de del desde el en entre es fue ha han hay la las le les lo
los mas no o para pero por que se sin sobre su sus un una uno unos unas y ya este esta estos
estas ese esa como tras segun hoy""".split())


def _ruta_subtemas(brand: str, extra=None) -> str:
    return os.path.join(_dir_historial(extra), "subtemas_%s.json" % _slug(brand))


def _contenido(titulo: str) -> set:
    return {w for w in _n(titulo).split() if len(w) >= 3 and w not in _VACIAS}


def _propios(titulo: str) -> set:
    """Palabras con mayúscula inicial que no abren el titular (lugares,
    personas): dos notas del mismo molde con otro lugar o persona no son la
    misma noticia."""
    toks = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñü]+", str(titulo or ""))
    return {_n(w) for w in toks[1:] if w[:1].isupper() and len(w) >= 3} - _VACIAS


def _gramas(texto: str, k: int = 3) -> set:
    w = _n(texto).split()[:80]
    return {" ".join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


def _jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def cargar_subtemas(brand: str, extra=None) -> list:
    """Entradas vigentes: [{t, p, g, subtema, fecha}]."""
    try:
        with open(_ruta_subtemas(brand, extra), encoding="utf-8") as f:
            data = json.load(f)
        limite = (datetime.now() - timedelta(days=DIAS_SUBTEMAS)).isoformat(timespec="seconds")
        return [e for e in (data.get("entradas") or [])
                if isinstance(e, dict) and e.get("subtema") and str(e.get("fecha") or "") >= limite]
    except (OSError, ValueError, AttributeError):
        return []


def _entrada(titulo: str, texto: str, subtema: str) -> dict:
    return {"titulo": str(titulo or "")[:300], "texto": _n(texto)[:500],
            "subtema": str(subtema or "").strip()}


def buscar_subtema(entradas: list, titulo: str, texto: str = "") -> Optional[str]:
    """Subtema de una noticia previa igual o muy parecida, o None.

    Igual: mismo titular normalizado. Parecida: titulares con casi las
    mismas palabras de contenido (y los mismos nombres propios), o el mismo
    comienzo del texto (la misma nota republicada con otro titular)."""
    tn = _n(titulo)
    if not tn:
        return None
    c, p, g = _contenido(titulo), _propios(titulo), _gramas(texto)
    mejor, mejor_s = None, 0.0
    for e in entradas:
        et = e.get("titulo") or ""
        if _n(et) == tn:
            return e["subtema"]
        s = 0.0
        ec = _contenido(et)
        if len(c) >= 4 and len(ec) >= 4 and _propios(et) == p:
            jt = _jac(c, ec)
            if jt >= UMBRAL_TITULO:
                s = jt
        if g and e.get("texto"):
            jg = _jac(g, _gramas(e["texto"]))
            if jg >= UMBRAL_TEXTO and len(g) >= 15:
                s = max(s, jg)
        if s > mejor_s:
            mejor, mejor_s = e["subtema"], s
    return mejor


def guardar_subtemas(brand: str, nuevas: list, extra=None) -> int:
    """Agrega o renueva [{titulo, texto, subtema}] (por titular normalizado)."""
    try:
        previas = cargar_subtemas(brand, extra)
        ahora = datetime.now().isoformat(timespec="seconds")
        por_tit = {_n(e.get("titulo")): e for e in previas if _n(e.get("titulo"))}
        for e in nuevas or []:
            k = _n(e.get("titulo"))
            if k and e.get("subtema"):
                por_tit[k] = dict(e, fecha=ahora)
        entradas = sorted(por_tit.values(), key=lambda e: e.get("fecha") or "",
                          reverse=True)[:MAX_SUBTEMAS]
        ruta = _ruta_subtemas(brand, extra)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ruta), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"entradas": entradas}, f, ensure_ascii=False)
        os.replace(tmp, ruta)
        return len(entradas)
    except (OSError, ValueError):
        return 0


def borrar_subtemas(brand: str, extra=None) -> bool:
    try:
        os.remove(_ruta_subtemas(brand, extra))
        return True
    except OSError:
        return False
