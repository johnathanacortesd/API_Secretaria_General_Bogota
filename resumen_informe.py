# -*- coding: utf-8 -*-
"""Resumen para informe a partir de un XLSX CORREGIDO (ya analizado).

Uso en estas apps (Secretaría General / Defensoría del Pueblo):

* Se resube el xlsx corregido y se lee SOLO la primera hoja, sin importar
  su nombre. Las demás hojas, si las hay, se ignoran y se avisa cuántas
  fueron ignoradas.
* Columnas obligatorias (se buscan sin distinguir mayúsculas ni acentos):
  ``Tono_IA``, ``Subtema_IA`` y ``Contexto analizado``.
* El tono dominante es el valor de ``Tono_IA`` con más apariciones y su
  porcentaje se calcula sobre el total de filas con ``Tono_IA`` no vacío
  (filas totalmente vacías se ignoran y se reportan). El porcentaje se
  redondea al entero más cercano y se escribe con espacio antes del
  símbolo, tal como pidió el usuario: ``51 %`` (no ``51%``).
* El subtema principal es el valor de ``Subtema_IA`` con más apariciones
  (desempate: el que aparece primero en el archivo). El párrafo 1 se
  construye con una plantilla fija + un fragmento redactado con la API
  (modelo de la app, ``gpt-6-luna``) a partir de los ``Contexto analizado``
  de ese subtema. Ese fragmento debe medir entre 140 y 160 caracteres.
* El párrafo 2 resume con la API los subtemas destacados siguientes
  (puestos 2 a 5; si solo hay un subtema, se usa ese). Empieza siempre
  con ``En términos generales, la agenda mediática se centró en ``.

Sin ``OPENAI_API_KEY`` en los Secrets la app NO falla: genera un resumen
extractivo (recorte de los contextos, sin inventar texto) y lo marca
claramente como "sin IA". La vía principal, con clave, es la API.

Este módulo es puro (sin Streamlit en la importación) para poder
probarlo sin desplegar. La función ``render_resumen_tab`` importa
Streamlit de forma perezosa y es la que usa ``app.py``.
"""

import io
import math
import re
import unicodedata

import pandas as pd

MODELO_RESUMEN = "gpt-6-luna"
MIN_FRAGMENTO = 140
MAX_FRAGMENTO = 160
MAX_CONTEXTO_POR_SUBTEMA = 8
MAX_CHARS_CONTEXTO_API = 600


# --------------------------------------------------------------------------
# Lectura: solo la primera hoja
# --------------------------------------------------------------------------

def _sin_acentos(texto):
    s = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in s if not unicodedata.combining(c))


def _clave_columna(nombre):
    """Clave comparable para nombres de columna: minúsculas, sin acentos,
    sin espacios ni guiones bajos."""
    s = _sin_acentos(nombre).lower().strip()
    return re.sub(r"[\s_\-]+", "", s)


def leer_primera_hoja(archivo_bytes):
    """Lee solo la primera hoja de un xlsx.

    Devuelve ``(df, nombre_primera_hoja, total_hojas)``. ``df`` trae
    todas las celdas como texto (las vacías quedan como "").
    """
    bio = io.BytesIO(archivo_bytes)
    xls = pd.ExcelFile(bio, engine="openpyxl")
    nombres = list(xls.sheet_names or [])
    if not nombres:
        raise ValueError("El archivo no trae ninguna hoja.")
    df = pd.read_excel(xls, sheet_name=0, dtype=str, engine="openpyxl")
    df = df.fillna("")
    # Filas totalmente vacías (fantasmas de export) no cuentan.
    antes = len(df)
    df = df[df.apply(lambda fila: any(str(v).strip() for v in fila), axis=1)]
    df = df.reset_index(drop=True)
    return df, nombres[0], len(nombres), antes - len(df)


def resolver_columnas(df):
    """Encuentra Tono_IA, Subtema_IA y Contexto analizado por clave.

    Devuelve dict con los nombres reales de columna. Lanza ValueError
    con las columnas disponibles si falta alguna.
    """
    por_clave = {_clave_columna(c): c for c in df.columns}
    buscadas = {
        "tono": ["tonoia", "tono"],
        "subtema": ["subtemaia", "subtema"],
        "contexto": ["contextoanalizado", "contexto"],
    }
    resueltas = {}
    faltantes = []
    for campo, claves in buscadas.items():
        hallada = None
        for clave in claves:
            if clave in por_clave:
                hallada = por_clave[clave]
                break
        if hallada is None:
            faltantes.append(campo)
        else:
            resueltas[campo] = hallada
    if faltantes:
        disponibles = ", ".join(str(c) for c in df.columns)
        raise ValueError(
            "Faltan columnas en la primera hoja: %s. Columnas encontradas: %s"
            % (", ".join(faltantes), disponibles)
        )
    return resueltas


# --------------------------------------------------------------------------
# Estadísticas deterministas (sin IA): tono dominante y subtemas top
# --------------------------------------------------------------------------

_MAPA_TONO = {
    "positivo": "Positivo",
    "positive": "Positivo",
    "pos": "Positivo",
    "negativo": "Negativo",
    "negative": "Negativo",
    "neg": "Negativo",
    "neutro": "Neutro",
    "neutral": "Neutro",
    "neu": "Neutro",
}


def normalizar_tono(valor):
    v = _sin_acentos(valor).strip().lower()
    if v in _MAPA_TONO:
        return _MAPA_TONO[v]
    return str(valor or "").strip()


def _normalizar_subtema(valor):
    return re.sub(r"\s+", " ", str(valor or "").strip())


def _porcentaje(n, total):
    if not total:
        return 0
    # Redondeo "humano": 50.5 -> 51 (round() de Python haría 50).
    return int(math.floor(n * 100.0 / total + 0.5))


def calcular_estadisticas(df, columnas):
    """Cuenta tonos y subtemas. No llama a ninguna API."""
    col_tono = columnas["tono"]
    col_sub = columnas["subtema"]
    col_ctx = columnas["contexto"]

    tonos = [normalizar_tono(v) for v in df[col_tono]]
    tonos = [t for t in tonos if t]
    total = len(tonos)

    conteo_tono = {}
    for t in tonos:
        conteo_tono[t] = conteo_tono.get(t, 0) + 1
    # Dominante: más apariciones; desempate alfabético (determinista).
    tono_dominante = None
    tono_n = 0
    if conteo_tono:
        tono_dominante, tono_n = sorted(
            conteo_tono.items(), key=lambda kv: (-kv[1], kv[0])
        )[0]
    pct_tono = _porcentaje(tono_n, total)

    # Subtemas: agrupar sin distinguir mayúsculas, mostrar la forma más
    # frecuente en el archivo; desempate por primera aparición.
    orden = {}
    conteo_sub = {}
    forma = {}
    for i, v in enumerate(df[col_sub]):
        s = _normalizar_subtema(v)
        if not s:
            continue
        clave = s.lower()
        if clave not in conteo_sub:
            conteo_sub[clave] = 0
            orden[clave] = i
            forma[clave] = s
        conteo_sub[clave] += 1
        # La forma mostrada es la más frecuente: si esta forma supera a
        # la guardada, se reemplaza (conteo por forma exacta).
    # Forma más frecuente por clave (segunda pasada, exacta).
    forma_exacta = {}
    for v in df[col_sub]:
        s = _normalizar_subtema(v)
        if s:
            forma_exacta[s] = forma_exacta.get(s, 0) + 1
    for clave in list(forma):
        candidatos = [f for f in forma_exacta if f.lower() == clave]
        if candidatos:
            forma[clave] = max(candidatos, key=lambda f: forma_exacta[f])

    subtemas = sorted(
        (
            {
                "subtema": forma[clave],
                "n": conteo_sub[clave],
                "pct": _porcentaje(conteo_sub[clave], total),
                "primera_aparicion": orden[clave],
            }
            for clave in conteo_sub
        ),
        key=lambda d: (-d["n"], d["primera_aparicion"]),
    )

    contextos_top = []
    if subtemas:
        top = subtemas[0]["subtema"].lower()
        for v_sub, v_ctx in zip(df[col_sub], df[col_ctx]):
            if _normalizar_subtema(v_sub).lower() == top:
                ctx = re.sub(r"\s+", " ", str(v_ctx or "").strip())
                if ctx:
                    contextos_top.append(ctx)
            if len(contextos_top) >= MAX_CONTEXTO_POR_SUBTEMA:
                break

    return {
        "total": total,
        "conteo_tono": conteo_tono,
        "tono_dominante": tono_dominante,
        "tono_n": tono_n,
        "tono_pct": pct_tono,
        "tono_pct_txt": "%d %%" % pct_tono,
        "subtemas": subtemas,
        "subtema_top": subtemas[0] if subtemas else None,
        "contextos_top": contextos_top,
    }


# --------------------------------------------------------------------------
# Fragmento 140-160 caracteres (vía API, con respaldo extractivo)
# --------------------------------------------------------------------------

def _recortar_fragmento(texto, minimo=MIN_FRAGMENTO, maximo=MAX_FRAGMENTO):
    """Recorta un texto largo a [minimo, maximo] caracteres en un límite
    de palabra. Devuelve "" si el texto es más corto que el mínimo."""
    t = re.sub(r"\s+", " ", str(texto or "").strip()).rstrip(".")
    if len(t) < minimo:
        return ""
    if len(t) <= maximo:
        return t
    # Buscar un límite de palabra dentro de [minimo, maximo].
    ventana = t[minimo:maximo + 1]
    # El corte ideal es el último espacio en la ventana extendida.
    trozo = t[:maximo]
    ultimo_espacio = trozo.rfind(" ")
    if ultimo_espacio >= minimo:
        return trozo[:ultimo_espacio]
    # Si no hay espacio en rango, cortar en el primer espacio tras mínimo.
    siguiente = t.find(" ", minimo, maximo + 1)
    if siguiente != -1:
        return t[:siguiente]
    return trozo


def _fragmento_extractivo(contextos):
    """Respaldo sin IA: concatena contextos hasta alcanzar 140-160."""
    unido = " ".join(contextos)
    frag = _recortar_fragmento(unido)
    if frag:
        return frag, []
    # Texto corto: se devuelve tal cual (sin inventar relleno) y se avisa.
    t = re.sub(r"\s+", " ", unido.strip()).rstrip(".")
    return t, [
        "Sin IA y con poco texto en Contexto analizado: el fragmento quedó "
        "en %d caracteres (se piden 140 a 160)." % len(t)
    ]


def _llamar_openai(api_key, modelo, system, user, max_tokens):
    """Una llamada chat completions. Devuelve el texto o lanza excepción."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def _fragmento_con_api(api_key, cliente, aliases, subtema_top, contextos):
    """Pide a la API un fragmento de 140-160 caracteres. Reintenta hasta
    3 veces si la longitud no cae en rango. Si no lo logra, recorta o
    avisa, pero nunca inventa datos fuera de los contextos."""
    alias_txt = ", ".join(aliases) if aliases else "ninguno"
    contexto_txt = "\n".join(
        "- " + c[:MAX_CHARS_CONTEXTO_API] for c in contextos
    )
    system = (
        "Redactor senior de informes de monitoreo de medios. Escribe solo "
        "lo que piden, sin copiar titulares y sin inventar datos fuera de "
        "los contextos entregados."
    )
    advertencias = []
    ultimo = ""
    for intento in range(3):
        extra = ""
        if intento and ultimo:
            extra = (
                " Tu fragmento anterior tenía %d caracteres; debe tener "
                "entre 140 y 160 caracteres contando espacios. Ajusta la "
                "longitud sin cambiar el hecho." % len(ultimo)
            )
        user = (
            "Cliente: %s. Marcas y palabras relacionadas: %s.\n"
            "Subtema con más apariciones: %s.\n"
            "Contextos analizados de esas noticias:\n%s\n\n"
            "Redacta UN solo fragmento en español, en minúscula inicial, "
            "sin punto final, que complete la frase 'noticias relacionadas "
            "a ...' y resuma qué dicen esas noticias sobre el cliente. "
            "El fragmento debe tener entre 140 y 160 caracteres contando "
            "espacios. No empieces el fragmento repitiendo el nombre del "
            "cliente, porque la frase ya lo nombra; empieza directamente "
            "por el hecho (ej. 'la propuesta para…'). No copies el subtema "
            "literal si es un recorte de "
            "titular, no menciones medios y no agregues datos que no estén "
            "en los contextos.%s"
            % (cliente, alias_txt, subtema_top, contexto_txt, extra)
        )
        try:
            ultimo = _llamar_openai(
                api_key, MODELO_RESUMEN, system, user, max_tokens=160
            )
        except Exception as exc:  # noqa: BLE001 - se reporta como aviso
            advertencias.append("La llamada a la API falló (%s); se usó "
                                "respaldo extractivo." % exc)
            return _fragmento_extractivo(contextos)[0], advertencias, False
        ultimo = re.sub(r"\s+", " ", ultimo).strip().rstrip(".")
        if MIN_FRAGMENTO <= len(ultimo) <= MAX_FRAGMENTO:
            return ultimo, advertencias, True
    # Fuera de rango tras 3 intentos: recortar si sobra, avisar si falta.
    if len(ultimo) > MAX_FRAGMENTO:
        recortado = _recortar_fragmento(ultimo)
        if recortado:
            advertencias.append(
                "La API devolvió %d caracteres; se recortó a %d en un "
                "límite de palabra." % (len(ultimo), len(recortado))
            )
            return recortado, advertencias, True
    advertencias.append(
        "La API devolvió %d caracteres tras 3 intentos (se piden 140 a "
        "160); se conserva tal cual para no inventar relleno."
        % len(ultimo)
    )
    return ultimo, advertencias, True


def _parrafo2_con_api(api_key, cliente, subtemas_destacados):
    """Párrafo 2 con la API. Empieza siempre con la frase fija."""
    prefijo = "En términos generales, la agenda mediática se centró en "
    lista = "\n".join(
        "- %s (%d apariciones)" % (s["subtema"], s["n"])
        for s in subtemas_destacados
    )
    system = (
        "Redactor senior de informes de monitoreo de medios. Escribe un "
        "solo párrafo, sin inventar temas fuera de la lista entregada."
    )
    user = (
        "Cliente: %s.\nSubtemas destacados (en orden de apariciones):\n%s\n\n"
        "Redacta UN solo párrafo en español que empiece EXACTAMENTE con "
        "'%s' y continúe resumiendo esos subtemas destacados, en el mismo "
        "estilo del ejemplo: noticias donde se menciona al cliente o al "
        "cargo de manera referencial y los demás temas de la agenda. Una "
        "sola oración larga o dos cortas, con punto final. No copies "
        "titulares y no agregues temas nuevos."
        % (cliente, lista, prefijo)
    )
    try:
        texto = _llamar_openai(api_key, MODELO_RESUMEN, system, user, 260)
    except Exception as exc:  # noqa: BLE001
        return None, ["La llamada a la API para el párrafo 2 falló (%s); "
                      "se usó respaldo extractivo." % exc]
    texto = re.sub(r"\s+", " ", texto).strip()
    if not texto.startswith(prefijo):
        texto = prefijo + texto.lstrip()
    if not texto.endswith("."):
        texto += "."
    return texto, []


def _parrafo2_extractivo(subtemas_destacados):
    prefijo = "En términos generales, la agenda mediática se centró en "
    temas = "; ".join(s["subtema"] for s in subtemas_destacados)
    return prefijo + "los siguientes subtemas destacados: " + temas + "."


# --------------------------------------------------------------------------
# Orquestación
# --------------------------------------------------------------------------

def generar_texto_informe(df, columnas, cliente, aliases, api_key=None):
    """Devuelve el texto completo + estadísticas + advertencias."""
    stats = calcular_estadisticas(df, columnas)
    advertencias = []
    if not stats["total"]:
        raise ValueError("La primera hoja no trae filas con Tono_IA.")
    if not stats["subtema_top"]:
        raise ValueError("La primera hoja no trae filas con Subtema_IA.")

    uso_api = bool(api_key)
    if uso_api:
        fragmento, adv, _ok = _fragmento_con_api(
            api_key, cliente, aliases,
            stats["subtema_top"]["subtema"], stats["contextos_top"],
        )
        advertencias.extend(adv)
        if not fragmento:
            fragmento, adv2 = _fragmento_extractivo(stats["contextos_top"])
            advertencias.extend(adv2)
            uso_api = False
    else:
        fragmento, adv = _fragmento_extractivo(stats["contextos_top"])
        advertencias.extend(adv)
        advertencias.append(
            "Sin OPENAI_API_KEY en los Secrets: el fragmento es extractivo "
            "(recorte de Contexto analizado), no redactado por la API."
        )

    # Párrafo 1: plantilla fija del usuario + fragmento 140-160.
    frag = fragmento.strip().rstrip(".")
    if frag:
        frag = frag[0].lower() + frag[1:] if frag[0].isupper() else frag
    tono_min = (stats["tono_dominante"] or "").lower()
    parrafo1 = (
        "En el reciente periodo, la visibilidad de la %s en medios "
        "tradicionales registró un tono %s del %s, impulsado por noticias "
        "relacionadas a %s."
        % (cliente, tono_min, stats["tono_pct_txt"], frag)
    )

    # Párrafo 2: subtemas destacados (puestos 2-5; si solo hay uno, ese).
    destacados = stats["subtemas"][1:5] or stats["subtemas"][:1]
    if uso_api:
        parrafo2, adv2 = _parrafo2_con_api(api_key, cliente, destacados)
        advertencias.extend(adv2)
        if parrafo2 is None:
            parrafo2 = _parrafo2_extractivo(destacados)
            uso_api = False
    else:
        parrafo2 = _parrafo2_extractivo(destacados)
        if api_key is None:
            advertencias.append(
                "Sin OPENAI_API_KEY: el párrafo 2 también es extractivo."
            )

    return {
        "parrafo1": parrafo1,
        "parrafo2": parrafo2,
        "fragmento": frag,
        "fragmento_caracteres": len(frag),
        "stats": stats,
        "destacados": destacados,
        "uso_api": uso_api,
        "advertencias": advertencias,
        "texto_completo": parrafo1 + "\n\n" + parrafo2,
    }


# --------------------------------------------------------------------------
# Interfaz Streamlit (import perezoso)
# --------------------------------------------------------------------------

def render_resumen_tab(cliente, aliases):
    """Sección 'Resumen para informe' para app.py.

    ``cliente`` es el nombre completo (ej. 'Secretaría General de la
    Alcaldía de Bogotá') y ``aliases`` la lista de marcas/palabras
    relacionadas del perfil fijo de este repo.
    """
    import streamlit as st

    st.markdown("### 📝 Resumen para informe")
    st.markdown(
        "Resube aquí el **xlsx corregido** (el que ya trae `Tono_IA`, "
        "`Subtema_IA` y `Contexto analizado`). Solo se lee la **primera "
        "hoja, sin importar su nombre**; las demás hojas se ignoran. "
        "Con esa información se genera el texto de dos párrafos para el "
        "informe, con el tono dominante, su porcentaje y el subtema con "
        "más apariciones."
    )
    st.caption(
        "Enfoque de este repo: %s. Marcas y palabras relacionadas: %s."
        % (cliente, ", ".join(aliases) if aliases else "—")
    )
    archivo = st.file_uploader(
        "XLSX corregido", type=["xlsx"], key="resumen_xlsx_corregido"
    )
    if archivo is None:
        return
    # Si cambia el archivo, el resultado anterior ya no aplica.
    _firma = (archivo.name, archivo.size)
    if st.session_state.get("resumen_firma") != _firma:
        st.session_state["resumen_firma"] = _firma
        st.session_state.pop("resumen_resultado", None)
    try:
        df, hoja, total_hojas, vacias = leer_primera_hoja(archivo.getvalue())
    except Exception as exc:  # noqa: BLE001 - mensaje accionable al usuario
        st.error("No se pudo leer el archivo: %s" % exc)
        return
    st.info(
        "Primera hoja leída: **%s** (%d filas). %s"
        % (
            hoja,
            len(df),
            ("Se ignoraron %d hojas adicionales." % (total_hojas - 1))
            if total_hojas > 1 else "El archivo trae una sola hoja.",
        )
    )
    if vacias:
        st.caption("Se ignoraron %d filas totalmente vacías." % vacias)
    try:
        columnas = resolver_columnas(df)
    except ValueError as exc:
        st.error(str(exc))
        return
    if st.button("Generar texto para informe", key="resumen_generar",
                 type="primary"):
        api_key = None
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            api_key = None
        with st.spinner("Generando texto…"):
            try:
                resultado = generar_texto_informe(
                    df, columnas, cliente, aliases, api_key=api_key
                )
            except ValueError as exc:
                st.error(str(exc))
                return
        # Guardar en sesión: así el texto y el botón de descarga siguen
        # visibles en la siguiente ejecución (un botón solo vale un run).
        st.session_state["resumen_resultado"] = resultado
    resultado = st.session_state.get("resumen_resultado")
    if resultado is None:
        return
    if True:
        stats = resultado["stats"]
        st.markdown("#### Datos calculados (primera hoja)")
        st.markdown(
            "- Total con `Tono_IA`: **%d** filas\n"
            "- Tono dominante: **%s** · %d apariciones · **%s**\n"
            "- Subtema con más apariciones: **%s** · %d apariciones"
            % (
                stats["total"],
                stats["tono_dominante"],
                stats["tono_n"],
                stats["tono_pct_txt"],
                stats["subtema_top"]["subtema"],
                stats["subtema_top"]["n"],
            )
        )
        conteo = [
            {"Tono": t, "Apariciones": n,
             "Porcentaje": "%d %%" % _porcentaje(n, stats["total"])}
            for t, n in sorted(
                stats["conteo_tono"].items(), key=lambda kv: -kv[1]
            )
        ]
        st.dataframe(conteo, use_container_width=True, hide_index=True)
        top_sub = [
            {"Subtema_IA": s["subtema"], "Apariciones": s["n"]}
            for s in stats["subtemas"][:5]
        ]
        st.dataframe(top_sub, use_container_width=True, hide_index=True)
        for adv in resultado["advertencias"]:
            st.warning(adv)
        st.markdown("#### Texto para el informe")
        st.caption(
            "Fragmento del párrafo 1: %d caracteres (se piden 140 a 160) · "
            "Vía: %s"
            % (
                resultado["fragmento_caracteres"],
                "API (%s)" % MODELO_RESUMEN if resultado["uso_api"]
                else "extractiva (sin IA)",
            )
        )
        st.text_area(
            "Texto generado (copiar y pegar)",
            value=resultado["texto_completo"],
            height=220,
            key="resumen_texto_final",
        )
        st.download_button(
            "⬇ Descargar texto (.txt)",
            data=resultado["texto_completo"].encode("utf-8"),
            file_name="resumen_informe.txt",
            mime="text/plain",
            key="resumen_descargar_txt",
        )
