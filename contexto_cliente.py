# -*- coding: utf-8 -*-
"""Contexto analizado por SEGMENTOS del CuerpoEs.

El Contexto analizado es la evidencia con la que se decide el tono y se
redacta el subtema, así que tiene que traer TODO lo que la nota dice del
cliente, no las tres primeras oraciones que lo nombran:

1. El CuerpoEs se parte en oraciones.
2. Se ubican las menciones del cliente por categoría:
   - `marca`: la marca y sus alias (Secretaría General, Alcaldía de Bogotá);
   - `vocero`: los voceros del perfil y el alcalde por su cargo;
   - `distrito`: la Alcaldía, el Distrito o la administración distrital;
   - `adscrita`: secretarías distritales, entidades del Distrito y sus
     directivos por cargo (secretario de Movilidad, gerente del Metro).
   Las dos últimas solo con `distrito=True` (perfil de la Secretaría General).
   No cuentan las menciones ajenas: candidatos a la Alcaldía, exalcaldes,
   otros alcaldes, secretarías de otra ciudad u homónimos del vocero.
3. Cada mención es un SEGMENTO: la oración, más la anterior cuando la
   oración depende de ella («Frente a esto, el alcalde…») y la siguiente
   cuando continúa la cita o el sujeto («El mandatario agregó…»).
4. Los segmentos se priorizan (vocero y marca primero, luego los que traen
   una valoración, una gestión o una respuesta) y se unen en el orden del
   texto hasta el tope. Entre segmentos no contiguos va « […] ».

Todo el texto es literal: no se resume ni se inventa nada.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Callable, Dict, List, Optional, Sequence, Tuple

SEPARADOR = ' […] '
TOPE_GENERAL = 1200
TOPE_RADIODIFUSION = 900
MAX_ORACION = 700          # una «oración» más larga es un transcript sin puntos
VENTANA_TRANSCRIPT = 300   # caracteres a cada lado de la mención
MEDIOS_RADIODIFUSION = {'radio', 'television', 'tv', 'aire', 'cable', 'am', 'fm'}

PESO = {'vocero': 3, 'marca': 3, 'distrito': 2, 'adscrita': 2}
NOMBRE_CATEGORIA = {'vocero': 'vocero', 'marca': 'marca o alias',
                    'distrito': 'Alcaldía o Distrito', 'adscrita': 'entidad adscrita'}


def nz(s) -> str:
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9ñ ]+', ' ', s)).strip()


# ─── oraciones ────────────────────────────────────────────────────────────
_ABREV = {'a', 'm', 'p', 'dr', 'dra', 'sr', 'sra', 'srta', 'ing', 'lic', 'no', 'art', 'aprox',
          'ej', 'etc', 'vs', 'ud', 'uds', 'sres', 'd', 'c', 'e', 'g', 'ph', 'jr', 'av', 'cra',
          'cl', 'km', 'gral', 'cnel', 'tte', 'núm', 'num', 'pág', 'pag', 'tel'}


def limpiar(texto) -> str:
    s = ''.join(ch for ch in str(texto or '') if (ch >= ' ' or ch in '\n\t')
                and ch not in '￾￿')
    s = re.sub(r'https?://\S+|www\.\S+', '', s)
    s = re.sub(r'^[ \t]*link[ \t]*', '', s, flags=re.I)
    return re.sub(r'[ \t]+', ' ', s).strip()


def partir_oraciones(texto: str) -> List[str]:
    """Oraciones literales, en orden. Corta por saltos de línea y por . ! ? …
    seguidos de mayúscula, dígito o comilla; no cortan las abreviaturas
    («a. m.», «Dr.»), las iniciales («J. Pérez») ni los decimales."""
    out: List[str] = []
    for bloque in re.split(r'\r?\n+', limpiar(texto)):
        bloque = bloque.strip()
        if not bloque:
            continue
        ini = 0
        for m in re.finditer(r'[.!?…]+["”»\')\]]*', bloque):
            fin = m.end()
            if fin < len(bloque) and not bloque[fin].isspace():
                continue                                   # 12.500, U.S.A
            if m.group(0)[0] == '.':
                prev = re.split(r'\s+', bloque[ini:m.start()].strip())[-1] if m.start() > ini else ''
                p = re.sub(r'[^a-záéíóúüñ]', '', prev.lower())
                if p in _ABREV or (len(p) == 1 and p.isalpha()):
                    continue
            sig = bloque[fin:].lstrip()
            if sig and not (sig[0].isupper() or sig[0].isdigit() or sig[0] in '"“«(¿¡—–-'):
                continue
            trozo = bloque[ini:fin].strip()
            if trozo:
                out.append(trozo)
            ini = fin
        resto = bloque[ini:].strip()
        if resto:
            out.append(resto)
    return out


# ─── catálogo del Distrito (Bogotá) ───────────────────────────────────────
_SECTORES = (r'gobierno|seguridad(?: convivencia y justicia)?|movilidad|hacienda|salud|educacion|'
             r'habitat|integracion social|cultura(?: recreacion y deporte)?|ambiente|'
             r'desarrollo economico|planeacion|la mujer|mujer|juridica')
# Lugares que sitúan a una secretaría o alcaldía fuera de Bogotá.
_OTROS_LUGARES = (r'cundinamarca|soacha|medellin|cali|barranquilla|cartagena|bucaramanga|cucuta|'
                  r'pereira|manizales|ibague|villavicencio|neiva|pasto|monteria|santa marta|'
                  r'armenia|popayan|tunja|valledupar|sincelejo|riohacha|quibdo|yopal|chia|cajica|'
                  r'zipaquira|mosquera|funza|madrid|facatativa|fusagasuga|girardot|la calera|'
                  r'cota|sibate|antioquia|valle|atlantico|bolivar|santander|boyaca|tolima|huila|'
                  r'meta|narino|cauca|caldas|risaralda|quindio|cesar|magdalena|cordoba|sucre|'
                  r'choco|casanare|envigado|itagui|bello|soledad|palmira|buenaventura|tulua')
_NO_BOGOTA = r'(?! (?:de|del) (?:%s)\b)(?! (?:departamental|municipal|nacional)\b)' % _OTROS_LUGARES

_ENTIDADES = (
    r'idu|instituto de desarrollo urbano|transmilenio|empresa metro(?: de bogota)?|'
    r'metro de bogota|uaesp|idrd|idpc|ipes|eaab|acueducto de bogota|empresa de acueducto|'
    r'idiger|idpac|idartes|idipron|idpyba|instituto distrital de [a-zñ]+(?: [a-zñ]+)?|'
    r'instituto de proteccion y bienestar animal|catastro distrital|uaecd|'
    r'jardin botanico(?: de bogota)?|orquesta filarmonica de bogota|canal capital|capital salud|'
    r'subred(?:es)? integradas? de servicios de salud|'
    r'subred (?:norte|sur|centro oriente|sur occidente)|bomberos(?: de)? bogota|'
    r'cuerpo oficial de bomberos|terminal de transportes?(?: de bogota)?|'
    r'operadora distrital de transporte|la rolita|renobo|agencia atenea|'
    r'caja de (?:la )?vivienda popular|dadep|defensoria del espacio publico|veeduria distrital|'
    r'unidad de mantenimiento vial|umv|fondos? de desarrollo local|'
    r'alcaldias? local(?:es)?|alcalde(?:sa)?s? local(?:es)?|loteria de bogota|'
    r'unidad administrativa especial de [a-zñ]+(?: [a-zñ]+)?')

# (categoría, etiqueta para el informe, patrón sobre texto normalizado)
_PATRONES_DISTRITO: List[Tuple[str, str, str]] = [
    ('vocero', 'alcalde de Bogotá',
     r'alcalde(?: mayor)? (?:de bogota|carlos fernando galan|carlos galan|galan)|alcalde mayor|'
     r'mandatario (?:distrital|capitalino|de los bogotanos|de bogota|de la capital)|'
     r'burgomaestre(?: de bogota| capitalino)?|administracion (?:de )?(?:carlos fernando )?galan|'
     r'gobierno (?:de )?(?:carlos fernando )?galan'),
    ('marca', 'Secretaría General', r'secretari[ao] general(?: de la alcaldia)?'),
    ('distrito', 'Alcaldía de Bogotá',
     r'alcaldia (?:mayor )?(?:de bogota|distrital)|alcaldia mayor'),
    ('distrito', 'Alcaldía',
     r'alcaldia(?! local| locales| municipal| de (?!bogota)| del )'),
    ('distrito', 'Distrito',
     r'administracion (?:distrital|de bogota|de la ciudad)|gobierno (?:distrital|de bogota)|'
     r'distrito capital|(?:el|del|al) distrito(?! (?:de|militar|judicial|electoral|capital|creativo|grafiti|turistico|especial)\b)|'
     r'(?:autoridades|entidades|funcionarios) (?:distritales|del distrito)|gabinete distrital'),
    ('adscrita', 'secretaría distrital',
     r'secretari[ao]s? (?:distrital(?:es)? )?(?:de|del|de la) (?:%s)\b%s|'
     r'secretari[ao]s? distrital(?:es)?(?: de [a-zñ]+)?|secretari[ao] (?:juridic[ao]|privad[ao]) '
     r'(?:distrital|de la alcaldia)' % (_SECTORES, _NO_BOGOTA)),
    ('adscrita', 'entidad del Distrito', r'(?:%s)\b' % _ENTIDADES),
]

# Homónimos y usos del apellido que no son el alcalde.
_HOMONIMOS = re.compile(
    r'\b(?:luis carlos galan(?: sarmiento)?|juan manuel galan|galan sarmiento|'
    r'(?:avenida|av|barrio|aeropuerto|colegio|estadio|parque|plaza|puente|sector|localidad) '
    r'(?:luis carlos )?galan)\b')

# Lo que hace «valorativa» a una oración: crítica, hecho adverso, gestión,
# resultado o respuesta. Sube la prioridad del segmento.
_VALORATIVA = re.compile(
    r'\b(?:critic|cuestion|denunci|rechaz|quej|reclam|sancion|investig|irregular|sobrecost|'
    r'corrup|retras|demor|afectaci|falla|crisis|incumpl|polemic|escandal|protest|exig|'
    r'responsab|respond|reconoc|admit|explic|aclar|advirt|alert|anunci|entreg|inaugur|lanz|'
    r'invirt|inversion|benefici|avance|logr|premi|habilit|ejecut|recuper|puso en marcha|'
    r'pone en marcha|firm|aprob|suspend|cancel|prohib|orden)\w*')

# La oración depende de la anterior (hay que traerla para que se entienda).
_DEPENDE_ANTERIOR = re.compile(
    r'^(?:ante |frente a |al respecto|sobre (?:esto|este|esta|el tema|la situacion)|'
    r'por su parte|a su turno|en respuesta|en ese sentido|en este sentido|sin embargo|'
    r'no obstante|pese a |por ello|por eso|por esta razon|asi |asi las cosas|de esta manera|'
    r'esto |este |esta |estos |estas |dicho |dicha |ello |la medida|el anuncio|tras |luego de )')
# La oración siguiente continúa el segmento (misma voz o mismo sujeto).
_CONTINUA = re.compile(
    r'^(?:ademas|tambien|asimismo|igualmente|agrego|anadio|explico|senalo|indico|aseguro|afirmo|'
    r'dijo|puntualizo|advirtio|concluyo|preciso|reitero|segun (?:el|la) (?:mandatario|funcionari[oa]|'
    r'entidad|secretari[oa]|alcalde)|(?:el|la) (?:mandatari[oa]|funcionari[oa]|entidad|'
    r'administracion|secretari[oa]|gerente|director|directora) )|'
    r'\b(?:agrego|anadio|explico|senalo|indico|aseguro|afirmo|dijo|puntualizo|advirtio|concluyo|'
    r'preciso|reitero|manifesto|sostuvo) (?:el|la) (?:mandatari[oa]|funcionari[oa]|alcalde|'
    r'secretari[oa]|gerente|director|directora)\b')


class Detector:
    """Ubica las menciones del cliente en un texto."""

    def __init__(self, brand: str = '', aliases: Sequence[str] = (), voceros: Sequence[str] = (),
                 distrito: bool = False,
                 enmascarar: Optional[Callable[[str], str]] = None) -> None:
        self.distrito = bool(distrito)
        self.enmascarar = enmascarar
        pats: List[Tuple[str, str, re.Pattern]] = []
        vistos = set()
        for cat, nombres in (('marca', [brand, *(aliases or [])]), ('vocero', list(voceros or []))):
            for nombre in sorted({str(x).strip() for x in nombres if str(x or '').strip()},
                                 key=lambda x: -len(nz(x))):
                n = nz(nombre)
                if len(n) < 2 or n in vistos:
                    continue
                vistos.add(n)
                pats.append((cat, nombre, re.compile(r'(?<![a-z0-9ñ])' + re.escape(n)
                                                     + r'(?![a-z0-9ñ])')))
        if self.distrito:
            for cat, etiqueta, pat in _PATRONES_DISTRITO:
                pats.append((cat, etiqueta, re.compile(r'(?<![a-z0-9ñ])(?:' + pat + r')')))
        self.patrones = pats

    def activo(self) -> bool:
        return bool(self.patrones)

    def menciones(self, texto: str) -> List[Tuple[str, str]]:
        """[(categoría, etiqueta)] de las menciones del texto, sin repetir.
        Las adscritas llevan el nombre tal como aparece."""
        crudo = str(texto or '')
        if not crudo.strip() or not self.patrones:
            return []
        if self.enmascarar is not None:
            try:
                crudo = self.enmascarar(crudo)
            except Exception:  # noqa: BLE001 - el enmascarado nunca tumba el extracto
                pass
        n = nz(crudo)
        if self.distrito:
            n = _HOMONIMOS.sub(' xajenax ', n)
        out: List[Tuple[str, str]] = []
        for cat, etiqueta, pat in self.patrones:
            m = pat.search(n)
            if not m:
                continue
            if cat == 'adscrita':
                etiqueta = m.group(0).strip()
            if (cat, etiqueta) not in out:
                out.append((cat, etiqueta))
        return out

    def menciona(self, texto: str) -> bool:
        return bool(self.menciones(texto))


def _ventana(oracion: str, det: Detector) -> str:
    """Transcript sin puntuación: ventana literal alrededor de la primera
    mención, cortada en límites de palabra."""
    palabras = oracion.split()
    norm, inicio = [], []          # tokens normalizados y su posición en `unido`
    largo = 0
    for w in palabras:
        t = nz(w)
        inicio.append(largo)
        norm.append(t)
        largo += len(t) + 1
    unido = ' '.join(norm)
    k = None
    for _, _, pat in det.patrones:
        for m in pat.finditer(unido):
            tok = max(0, sum(1 for x in inicio if x <= m.start()) - 1)
            # Se confirma sobre el texto crudo (respeta menciones ajenas).
            if det.menciona(' '.join(palabras[max(0, tok - 6):tok + 8])):
                k = tok if k is None else min(k, tok)
                break
    if k is None:
        return oracion[:2 * VENTANA_TRANSCRIPT].rsplit(' ', 1)[0] + ' …'
    pos = len(' '.join(palabras[:k]))
    a = max(0, pos - VENTANA_TRANSCRIPT)
    b = min(len(oracion), pos + VENTANA_TRANSCRIPT)
    if a > 0:
        a = oracion.find(' ', a) + 1
    if b < len(oracion):
        b = oracion.rfind(' ', 0, b)
    return ('… ' if a > 0 else '') + oracion[a:b].strip() + (' …' if b < len(oracion) else '')


def _etiquetas(menc: Sequence[Tuple[str, str]]) -> List[str]:
    """«Nombre (categoría)» sin formas redundantes: «Galán» sobra si ya está
    «Carlos Fernando Galán»; «Alcaldía» si ya está «Alcaldía de Bogotá»."""
    normas = [nz(e) for _, e in menc]
    out, vistos = [], set()
    for (c, e), n in zip(menc, normas):
        if n in vistos or any(n != o and (' %s ' % n) in (' %s ' % o) for o in normas):
            continue
        vistos.add(n)
        out.append('%s (%s)' % (e, NOMBRE_CATEGORIA[c]))
    return out


def construir(cuerpo: str, titulo: str, det: Detector, tipo_medio: str = '',
              tope: Optional[int] = None) -> Dict[str, object]:
    """Segmentos del cuerpo con menciones del cliente.

    Devuelve {'contexto', 'segmentos', 'menciones', 'categorias',
    'titulo_menciona', 'oraciones_con_mencion', 'lead'}. 'contexto' es ''
    cuando el cuerpo no nombra al cliente (quien llama decide el respaldo).
    """
    if tope is None:
        tope = TOPE_RADIODIFUSION if nz(tipo_medio) in MEDIOS_RADIODIFUSION else TOPE_GENERAL
    tit = limpiar(titulo)
    m_tit = det.menciones(tit)
    orac = partir_oraciones(cuerpo)
    lead = ' '.join(orac[:2])[:320].strip()
    vacio = {'contexto': '', 'segmentos': [],
             'menciones': _etiquetas(m_tit),
             'categorias': sorted({c for c, _ in m_tit}), 'titulo_menciona': bool(m_tit),
             'oraciones_con_mencion': 0, 'lead': lead}
    if not orac or not det.activo():
        return vacio
    hits: Dict[int, List[Tuple[str, str]]] = {}
    vistas = set()
    norm = []
    for i, o in enumerate(orac):
        n = nz(o)
        norm.append(n)
        ms = det.menciones(o)
        if ms and n not in vistas:           # el mismo cable repetido no suma
            hits[i] = ms
        vistas.add(n)
    if not hits:
        return vacio
    tit_toks = {w for w in nz(tit).split() if len(w) > 3}

    # Segmentos: la oración con mención + la anterior si depende de ella +
    # hasta dos siguientes si continúan la voz o el sujeto.
    rangos: List[List[int]] = []
    for i in sorted(hits):
        a = b = i
        if i > 0 and (i - 1) not in hits and (
                _DEPENDE_ANTERIOR.search(norm[i]) or orac[i][:1] in '"“«—–-' or len(orac[i]) < 60):
            a = i - 1
        for j in (i + 1, i + 2):
            if j >= len(orac) or j in hits:
                break
            if orac[j - 1].rstrip().endswith(':') or orac[j][:1] in '"“«—–-' \
                    or _CONTINUA.search(norm[j]):
                b = j
            else:
                break
        if rangos and a <= rangos[-1][1] + 1:
            rangos[-1][1] = max(rangos[-1][1], b)
        else:
            rangos.append([a, b])

    def _texto_oracion(i: int) -> str:
        o = orac[i]
        return _ventana(o, det) if len(o) > MAX_ORACION else o

    segs = []
    for k, (a, b) in enumerate(rangos):
        cats = [c for i in range(a, b + 1) for c, _ in hits.get(i, [])]
        puntos = max(PESO[c] for c in cats)
        txt_n = ' '.join(norm[a:b + 1])
        if _VALORATIVA.search(txt_n):
            puntos += 2
        if k == 0:
            puntos += 1
        if len(tit_toks & set(txt_n.split())) >= 2:
            puntos += 1
        segs.append({'a': a, 'b': b, 'puntos': puntos,
                     'partes': [_texto_oracion(i) for i in range(a, b + 1)],
                     'hit': [i - a for i in range(a, b + 1) if i in hits]})

    # Selección por prioridad hasta el tope; el orden final es el del texto.
    elegidos: Dict[int, str] = {}
    usado = 0
    for k in sorted(range(len(segs)), key=lambda k: (-segs[k]['puntos'], k)):
        s = segs[k]
        txt = ' '.join(s['partes'])
        costo = len(txt) + (len(SEPARADOR) if elegidos else 0)
        if usado + costo > tope:
            if elegidos:
                continue
            # El primer segmento elegido no cabe entero: sus oraciones con
            # mención, en orden, hasta el tope (al menos una).
            partes, largo = [], 0
            for j in s['hit']:
                p = s['partes'][j]
                if partes and largo + len(p) + 1 > tope:
                    break
                partes.append(p)
                largo += len(p) + 1
            txt = ' '.join(partes)[:tope]
            costo = len(txt)
        elegidos[k] = txt
        usado += costo
    orden = sorted(elegidos)
    contexto = ''
    for pos, k in enumerate(orden):
        if pos:
            contiguo = segs[orden[pos - 1]]['b'] + 1 == segs[k]['a']
            contexto += ' ' if contiguo else SEPARADOR
        contexto += elegidos[k]
    menc: List[Tuple[str, str]] = list(m_tit)
    for i in sorted(hits):
        for par in hits[i]:
            if par not in menc:
                menc.append(par)
    return {'contexto': contexto.strip(), 'segmentos': [elegidos[k] for k in orden],
            'menciones': _etiquetas(menc),
            'categorias': sorted({c for c, _ in menc}), 'titulo_menciona': bool(m_tit),
            'oraciones_con_mencion': len(hits), 'lead': lead}
