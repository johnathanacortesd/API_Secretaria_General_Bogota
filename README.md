# Secretaría General de la Alcaldía de Bogotá — Limpieza y Análisis de Noticias

App Streamlit basada en **API_2_Grill v4.67**, adaptada a un solo cliente,
con una función nueva en la **v1.0**: **Resumen para informe** a partir de
un xlsx corregido.

## Cliente y enfoque

| Campo | Valor |
|---|---|
| Marca | Secretaría General de la Alcaldía de Bogotá |
| Alias / palabras relacionadas | Secretaría General, Secretaría General de la Alcaldía Mayor de Bogotá, Alcaldía Mayor de Bogotá, Alcaldía de Bogotá, Distrito Capital, Administración Distrital |
| Voceros | Miguel Silva Moyano (secretario general de la Alcaldía Mayor de Bogotá, verificado en 2026) |
| Criterio de tono | Aspectual estricto (recomendado) |
| Perfil | `clientes/secretaria_general_de_la_alcaldia_de_bogota.json` |

Enfoque: el análisis mide el tono **solo sobre la marca, sus alias y sus
voceros**, no sobre la noticia en general. Las menciones a la Alcaldía o
al cargo de manera referencial también cuentan para la visibilidad de
este cliente, como en el ejemplo del informe. El resto del motor
(agrupación, tono/tema/subtema, guarda positiva, anti-copia) es el de
Grill v4.67 sin cambios.

## Resumen para informe (lo nuevo en v1.0)

Al final de la página, en **📝 Resumen para informe**:

1. Resube el **xlsx corregido** (el que ya trae `Tono_IA`, `Subtema_IA` y
   `Contexto analizado`).
2. Solo se lee la **primera hoja, sin importar su nombre**. Si el archivo
   trae más hojas, se ignoran y la app avisa cuántas ignoró.
3. La app calcula, sin IA:
   - el **tono dominante** de `Tono_IA` (el que más apariciones tiene) y
     su porcentaje sobre el total de filas con `Tono_IA`, con el formato
     pedido: `51 %` (espacio antes del símbolo, entero redondeado);
   - el **subtema con más apariciones** de `Subtema_IA` (desempate: el que
     aparece primero en el archivo).
4. Con la API (`gpt-6-luna`, la misma de Grill) redacta dos párrafos:
   - **Párrafo 1**, con plantilla fija:
     > En el reciente periodo, la visibilidad de la Secretaría General de
     > la Alcaldía de Bogotá en medios tradicionales registró un tono
     > neutro del 51 %, impulsado por noticias relacionadas a […].
     
     El fragmento entre corchetes se redacta con la API a partir de los
     `Contexto analizado` del subtema principal y **debe medir entre 140
     y 160 caracteres** (la app muestra el conteo y reintenta hasta 3
     veces si no cae en rango).
   - **Párrafo 2**, también con la API, que empieza siempre con
     “En términos generales, la agenda mediática se centró en …” y
     resume los subtemas destacados siguientes (puestos 2 a 5; si solo
     hay un subtema, se usa ese).
5. El texto queda en un cuadro para copiar y se puede descargar como
   `.txt`. Las tablas de conteos quedan visibles para auditar el
   porcentaje y el subtema principal.

Sin `OPENAI_API_KEY` la sección no falla: genera un resumen extractivo
(recorte de `Contexto analizado`, sin inventar texto) y lo marca
claramente como “sin IA”. La vía principal, con clave, es la API.

La lógica vive en `resumen_informe.py` (funciones puras, probables sin
Streamlit) y la interfaz en `app.py` (`render_resumen_tab`).

## Conexión manual en Streamlit

1. En Streamlit Cloud, **New app → Deploy** apuntando a este repo, rama
   `main`, archivo principal `app.py`.
2. En **Settings → Secrets**, configura los mismos Secrets que usa
   API_2_Grill (`APP_PASSWORD`, `OPENAI_API_KEY`, y los de configuración
   de regiones/internet). Para usar **solo** el Resumen para informe
   bastan `APP_PASSWORD` y `OPENAI_API_KEY`.
3. El resto del flujo (dossier estándar / columnas personalizadas) es
   el de API_2_Grill: elige el perfil único de este cliente antes de
   procesar.

## Archivos

- `app.py` — interfaz (Grill v4.67 + sección Resumen, versión visible v1.3)
- `resumen_informe.py` — lectura de primera hoja, conteos y redacción
- `clientes/` — solo el perfil de este cliente
- `analyzer_tono_tema.py`, `pipeline.py`, `ai_analyzer.py`,
  `catalogo_tono_tema.py`, `perfil_cliente.py`, `pkl_classifier.py`,
  `historial_cliente.py`, `auditoria_mail.py` — motor Grill v4.67
- `SPEC_TONO_TEMA.md` — especificación de tono/tema heredada de Grill
- `requirements.txt` — dependencias (Streamlit, pandas, openpyxl, openai…)

## Novedades v1.1 (2026-10-30, pendiente de push)

- Sigla **SGB** agregada como alias, junto a "Secretaría General de
  Bogotá".
- La comparación de marca/alias/vocero ya era sin mayúsculas ni acentos
  (se normaliza antes de comparar); se verificó con pruebas: valen
  "miguel silva" en minúsculas, "MIGUEL SILVA MOYANO" y "Miguel Silva"
  (nombre + primer apellido), además del nombre completo.
- Corrección general en estos dos repos (no en Grill): las siglas de 2
  letras ya cuentan en título y en Contexto analizado (antes se exigían
  3 caracteres y "DP" se caía); los bordes de palabra evitan que "DP"
  cuente dentro de otra palabra.

## Novedades v1.2 (2026-10-30, pendiente de push)

- Aviso de cliente en todas las pantallas: en la pantalla de contraseña
  ("Sistema de Limpieza y Análisis") aparece "📍 App de: Secretaría
  General de la Alcaldía de Bogotá", y tras ingresar queda un aviso
  permanente con el mismo texto (fuera del contenedor que se borra al
  procesar, así que también se ve durante el procesamiento y en la vista
  de resultados) y en el pie de página. Las dos apps comparten diseño y
  título de sistema, por eso el aviso es explícito y no depende solo del
  encabezado.

## Novedades v1.3 (2026-10-30, pendiente de push)

- Corrección de la v1.2: el aviso permanente tras ingresar se había
  escrito como texto plano sin `f`, así que en pantalla salía literal
  "{CLIENTE_NOMBRE}" en vez del nombre. Ahora es f-string en los tres
  sitios (contraseña, aviso permanente y pie) y se verifica el texto
  renderizado, no solo el código fuente.
