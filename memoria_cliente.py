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
DIAS_MANUAL = 10         # v1.42: correcciones manuales (xlsx corregido)
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


def _en_mayusculas(titulo: str) -> bool:
    letras = [ch for ch in str(titulo or "") if ch.isalpha()]
    return len(letras) >= 8 and sum(ch.isupper() for ch in letras) >= 0.8 * len(letras)


def _gramas(texto: str, k: int = 3) -> set:
    w = _n(texto).split()[:80]
    return {" ".join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


def _jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _limite(e: dict) -> str:
    dias = DIAS_MANUAL if e.get("manual") else DIAS_SUBTEMAS
    return (datetime.now() - timedelta(days=dias)).isoformat(timespec="seconds")


def _vigente(e: Any) -> bool:
    return isinstance(e, dict) and bool(str(e.get("subtema") or "").strip()) \
        and str(e.get("fecha") or "") >= _limite(e)


def cargar_subtemas(brand: str, extra=None) -> list:
    """Entradas vigentes: [{titulo, texto, subtema, fecha, manual?, tono?}].
    Las correcciones manuales (`manual`) duran DIAS_MANUAL días."""
    try:
        with open(_ruta_subtemas(brand, extra), encoding="utf-8") as f:
            data = json.load(f)
        return [e for e in (data.get("entradas") or []) if _vigente(e)]
    except (OSError, ValueError, AttributeError):
        return []


def _escribir_subtemas(brand: str, entradas: list, extra=None) -> None:
    entradas = sorted(entradas, key=lambda x: x.get("fecha") or "", reverse=True)[:MAX_SUBTEMAS]
    ruta = _ruta_subtemas(brand, extra)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ruta), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"entradas": entradas}, f, ensure_ascii=False)
    os.replace(tmp, ruta)


def _entrada(titulo: str, texto: str, subtema: str) -> dict:
    return {"titulo": str(titulo or "")[:300], "texto": _n(texto)[:500],
            "subtema": str(subtema or "").strip()}


def buscar_subtema(entradas: list, titulo: str, texto: str = "") -> Optional[str]:
    """Subtema de una noticia previa igual o muy parecida, o None."""
    e = buscar_entrada(entradas, titulo, texto)
    return e["subtema"] if e else None


def buscar_entrada(entradas: list, titulo: str, texto: str = "") -> Optional[dict]:
    """Entrada de una noticia previa igual o muy parecida, o None. A igual
    parecido gana la corrección manual.

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
            return e
        s = 0.0
        ec = _contenido(et)
        # Un titular en MAYÚSCULAS no dice cuáles son nombres propios.
        mismos_propios = _propios(et) == p or _en_mayusculas(et) or _en_mayusculas(titulo)
        if len(c) >= 4 and len(ec) >= 4 and mismos_propios:
            jt = _jac(c, ec)
            if jt >= UMBRAL_TITULO:
                s = jt
        if g and e.get("texto"):
            jg = _jac(g, _gramas(e["texto"]))
            if jg >= UMBRAL_TEXTO and len(g) >= 15:
                s = max(s, jg)
        if s and e.get("manual"):
            s += 0.001
        if s > mejor_s:
            mejor, mejor_s = e, s
    return mejor


def guardar_subtemas(brand: str, nuevas: list, extra=None) -> int:
    """Agrega o renueva [{titulo, texto, subtema}] (por titular normalizado).
    Una corrección manual vigente no se pisa con lo que dio una corrida."""
    try:
        previas = cargar_subtemas(brand, extra)
        ahora = datetime.now().isoformat(timespec="seconds")
        por_tit = {_n(e.get("titulo")): e for e in previas if _n(e.get("titulo"))}
        for e in nuevas or []:
            k = _n(e.get("titulo"))
            if k and e.get("subtema"):
                if (por_tit.get(k) or {}).get("manual") and not e.get("manual"):
                    continue
                por_tit[k] = dict(e, fecha=ahora)
        _escribir_subtemas(brand, list(por_tit.values()), extra)
        return min(len(por_tit), MAX_SUBTEMAS)
    except (OSError, ValueError):
        return 0


def borrar_subtemas(brand: str, extra=None) -> bool:
    try:
        os.remove(_ruta_subtemas(brand, extra))
        return True
    except OSError:
        return False


def exportar_subtemas(brand: str, extra=None) -> bytes:
    """Memoria de subtemas vigente como JSON, para descargarla y volver a
    subirla en otra sesión (Streamlit Cloud borra el disco al reiniciar)."""
    data = {"cliente": brand, "tipo": "memoria_subtemas",
            "entradas": cargar_subtemas(brand, extra)}
    return json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8")


def importar_subtemas(brand: str, contenido, extra=None) -> int:
    """Fusiona un JSON descargado con `exportar_subtemas` con la memoria
    actual. Por titular gana la entrada más reciente; cada una conserva su
    fecha, así lo vencido (más de DIAS_SUBTEMAS) se descarta solo.
    Devuelve cuántas entradas vigentes se importaron. Lanza ValueError si
    el archivo no es una memoria de subtemas."""
    if isinstance(contenido, (bytes, bytearray)):
        contenido = contenido.decode("utf-8-sig")
    try:
        data = json.loads(contenido)
    except ValueError as exc:
        raise ValueError("El archivo no es un JSON válido.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("entradas"), list):
        raise ValueError("El archivo no es una memoria de subtemas descargada de la app.")
    por_tit = {_n(e.get("titulo")): e for e in cargar_subtemas(brand, extra) if _n(e.get("titulo"))}
    importadas = 0
    for e in data["entradas"]:
        if not _vigente(e):
            continue
        k, fecha = _n(e.get("titulo")), str(e.get("fecha") or "")
        if not k:
            continue
        actual = por_tit.get(k)
        if actual is None or (fecha > str(actual.get("fecha") or "")
                              and (e.get("manual") or not actual.get("manual"))):
            nueva = {"titulo": str(e.get("titulo") or "")[:300],
                     "texto": str(e.get("texto") or "")[:500],
                     "subtema": str(e["subtema"]).strip(), "fecha": fecha}
            if e.get("manual"):
                nueva["manual"] = True
            if str(e.get("tono") or "") in TONOS:
                nueva["tono"] = e["tono"]
            por_tit[k] = nueva
        importadas += 1
    try:
        _escribir_subtemas(brand, list(por_tit.values()), extra)
    except OSError:
        return 0
    return importadas


# ============================================================================
# v1.42: correcciones manuales desde el xlsx de resultados. El analista
# descarga el xlsx del boletín, corrige Subtema_IA (y si quiere Tono_IA) y
# lo sube: cada fila queda en la memoria como corrección manual, así la
# misma noticia (o una muy parecida) en el boletín de la 1 o de las 6
# retoma el subtema y el tono corregidos.
# ============================================================================
TONOS = ("Positivo", "Neutro", "Negativo")
_COLS_TITULO = ("titulo",)
# Hoja «Base, boletín SGB»: TEMA = Subtema_IA, IMPACTO = Tono_IA.
_COLS_SUBTEMA = ("subtema ia", "subtema", "tema")
_COLS_TONO = ("tono ia", "tono", "impacto")
_COLS_TEXTO = ("cuerpoes", "cuerpo", "texto", "texto completo", "resumen aclaracion",
               "resumen corto", "resumen", "contexto analizado")


def _celda(v: Any) -> str:
    s = "" if v is None else str(v).strip()
    return "" if s.lower() in ("nan", "none", "-") else s


# Valores que el analista pone en la hoja para notas descartadas.
_NO_VALE = frozenset({"no aplica", "noaplica", "n a", "na", "duplicada", "duplicado",
                      "duplicadas", "x", "ninguno", "sin subtema"})
_COLS_FECHA = ("fecha informe", "fecha")
_COLS_HORA = ("hora b", "hora boletin", "boletin")


def _fecha_boletin(fecha: str, hora: str) -> str:
    """ISO de la nota según el boletín (FECHA INFORME + HORA B); '' si no
    se entiende la fecha. «1:00 p.m.» => 13:00, «6:00 p.m.» => 18:00."""
    f = str(fecha or "").strip()
    if not f:
        return ""
    d = None
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", f)
    if m:
        d = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    else:
        m = re.match(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", f)
        if m:
            y = int(m.group(3))
            d = (y + 2000 if y < 100 else y, int(m.group(2)), int(m.group(1)))
    if not d:
        return ""
    hh = 12
    h = _n(hora)
    m = re.match(r"(\d{1,2})(?:\s+(\d{2}))?\s*(a m|am|p m|pm)?", h)
    if m:
        hh = int(m.group(1)) % 12 if m.group(3) else int(m.group(1))
        if m.group(3) in ("p m", "pm"):
            hh += 12
        hh = min(hh, 23)
    try:
        return datetime(d[0], d[1], d[2], hh).isoformat(timespec="seconds")
    except ValueError:
        return ""


def correcciones_de_tabla(cabecera, filas, ahora: Optional[str] = None) -> list:
    """Filas [{titulo, texto, subtema, tono?, fecha, manual}] de una tabla
    de resultados (xlsx corregido o la hoja de Google Sheets del boletín).
    Necesita «Título» y «Subtema_IA»/«Subtema»; usa «Tono_IA»/«Tono», el
    texto más largo disponible y FECHA INFORME + HORA B para fechar cada
    nota (sin fecha, la de ahora). Por titular gana la nota más reciente.
    Las notas más viejas que DIAS_MANUAL quedan fuera."""
    cab = [_n(c) for c in cabecera]

    def col(opciones):
        for o in opciones:
            if o in cab:
                return cab.index(o)
        return None
    i_t, i_s, i_o = col(_COLS_TITULO), col(_COLS_SUBTEMA), col(_COLS_TONO)
    if i_t is None or i_s is None:
        return []
    i_f, i_h = col(_COLS_FECHA), col(_COLS_HORA)
    i_x = [cab.index(o) for o in _COLS_TEXTO if o in cab]
    ahora = ahora or datetime.now().isoformat(timespec="seconds")
    limite = (datetime.now() - timedelta(days=DIAS_MANUAL)).isoformat(timespec="seconds")
    por_tit: Dict[str, dict] = {}
    for fila in filas:
        fila = list(fila or [])
        get = (lambda i: _celda(fila[i]) if i is not None and i < len(fila) else "")
        tit, sub = get(i_t), get(i_s)
        k = _n(tit)
        if not k or not sub or _n(sub) in _NO_VALE:
            continue
        tono = get(i_o).capitalize()
        # Con columna de tono, solo cuentan las filas con un tono real:
        # «No aplica», «Duplicada» o vacío no son referencia de nada.
        if i_o is not None and tono not in TONOS:
            continue
        fecha = _fecha_boletin(get(i_f), get(i_h)) if i_f is not None else ""
        fecha = fecha or ahora
        if fecha < limite:
            continue
        texto = max((get(i) for i in i_x), key=len, default="")
        e = _entrada(tit, texto, sub)
        e.update(fecha=min(fecha, ahora), manual=True)
        if tono in TONOS:
            e["tono"] = tono
        if k not in por_tit or e["fecha"] >= por_tit[k]["fecha"]:
            por_tit[k] = e
    return list(por_tit.values())


def fusionar_correcciones(entradas: list, correcciones: list) -> list:
    """Memoria + correcciones (Sheets): una entrada por titular; la
    corrección manual gana a la automática y, entre manuales, la más
    reciente."""
    por_tit = {_n(e.get("titulo")): e for e in entradas or [] if _n(e.get("titulo"))}
    for e in correcciones or []:
        k = _n(e.get("titulo"))
        if not k or not str(e.get("subtema") or "").strip():
            continue
        a = por_tit.get(k)
        if a is None or not a.get("manual") or str(e.get("fecha") or "") >= str(a.get("fecha") or ""):
            por_tit[k] = dict(e, manual=True)
    return list(por_tit.values())


def leer_correcciones_xlsx(contenido: bytes) -> list:
    """Filas corregidas de un xlsx de resultados (la primera hoja que tenga
    «Título» y «Subtema_IA» o «Subtema»). Lanza ValueError si no las
    encuentra."""
    import io
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as exc:  # archivo dañado o que no es xlsx
        raise ValueError("No se pudo abrir el xlsx: %s" % exc) from exc
    filas = []
    try:
        for ws in wb.worksheets:
            it = ws.iter_rows(values_only=True)
            for _ in range(10):  # la cabecera puede no estar en la fila 1
                cab = next(it, None)
                if cab is None:
                    break
                nombres = [_n(c) for c in cab]
                if any(c in _COLS_TITULO for c in nombres) and \
                        any(c in _COLS_SUBTEMA for c in nombres):
                    # Lo que subes ahora es la corrección vigente: sin fecha del boletín.
                    nombres_sin_fecha = [("" if n in _COLS_FECHA + _COLS_HORA else c)
                                         for n, c in zip(nombres, cab)]
                    filas = correcciones_de_tabla(nombres_sin_fecha, it)
                    break
            if filas:
                break
    finally:
        wb.close()
    if not filas:
        raise ValueError("El xlsx no tiene las columnas «Título» y «Subtema_IA» (o «Subtema») "
                         "con datos.")
    return filas


def importar_correcciones_xlsx(brand: str, contenido: bytes, extra=None) -> int:
    """Guarda en la memoria de subtemas, como corrección manual (gana sobre
    lo que dio cualquier corrida y dura DIAS_MANUAL días), cada noticia del
    xlsx corregido. Devuelve cuántas noticias quedaron. ValueError si el
    archivo no sirve."""
    filas = leer_correcciones_xlsx(contenido)
    try:
        _escribir_subtemas(brand, fusionar_correcciones(cargar_subtemas(brand, extra), filas), extra)
    except OSError:
        return 0
    return len(filas)
