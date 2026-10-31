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

- `app.py` — interfaz (Grill v4.67 + sección Resumen, versión visible v1.16)
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

## Novedades v1.4 (2026-10-30, pendiente de push)

- El selector "Perfil de cliente" de la pestaña "Dossier estándar" ahora
  sale por defecto con el perfil de esta app ("Secretaría General de la
  Alcaldía de Bogotá"), en vez de "Sin perfil (configuración manual)".
  Al abrir, la marca, los alias, los voceros y el criterio quedan
  precargados; "Sin perfil" sigue disponible si se quiere configurar a
  mano.

## Novedades v1.5 (2026-10-30, pendiente de push)

- Soporte genérico en el motor para subtemas fijos del perfil
  (`subtemas_fijos`: frase → subtema exacto), que se aplica después del
  etiquetado y antes de asignar temas. En este repo el perfil lo trae
  vacío, así que no cambia ningún comportamiento; el cambio de contenido
  es solo para Defensoría (Alertas Tempranas).

## Novedades v1.6 (2026-10-30, pendiente de push; incluye la v1.5, aún sin publicar)

- Nuevas columnas TIPO y GÉNERO, justo antes de "Link Nota", en la
  pestaña estándar y en la de Columnas personalizadas. Se asignan por
  grupo (misma noticia = mismo TIPO y GÉNERO) en el mismo etiquetado
  con IA, sin llamadas extra al modelo.
- TIPO: "Institucional" si la noticia trata de la propia Secretaría/
  Alcaldía o interviene su vocero (la intervención del vocero también
  es Institucional, aunque hable de un proyecto); "Proyectos y
  programas" si trata de un proyecto, programa, iniciativa o acción
  concreta que no es institucional; "Información general" si solo
  menciona de forma general o referencial a la entidad o al cargo.
- GÉNERO: "Opinión" solo si es una columna de opinión firmada (una
  noticia que cita a otra persona NO es opinión); "Entrevista" solo
  si hay un diálogo claro de preguntas y respuestas entre dos personas
  que se alternan (una sola declaración o cita NO es entrevista); en
  cualquier otro caso, y siempre que haya duda, "Noticia".
- Refuerzos deterministas: una Entrevista sin preguntas ni marcas de
  dos interlocutores baja a Noticia; si la Sección del dossier dice
  Opinión/Columna y el modelo marcó Noticia, sube a Opinión (nunca
  sobrescribe una Entrevista). Valor inválido o empate: TIPO =
  Información general, GÉNERO = Noticia. Las duplicadas llevan "-"
  como en Tema/Subtema.

## Novedades v1.7 (2026-10-30; incluida en v1.8, solo Secretaría)

- Perfil ampliado por adición (no reemplaza nada): vocero adicional
  Carlos Fernando Galán, alcalde de Bogotá, y alias adicional Bogotá
  Camina Segura, estrategia distrital. Lo anterior queda intacto
  (Miguel Silva Moyano, Alcaldía de Bogotá, resto de alias).
- Formas adicionales del vocero Galán (mismo v1.7, a pedido del
  usuario): "Galán", "Carlos Galán" y "el alcalde" también cuentan
  como vocero, para darle mayor peso al tono con base en la
  Secretaría o el secretario cuando ese vocero aparece. Con esto
  queda resuelta la limitación anterior de "Galán" solo.

## Novedades v1.8 (2026-10-31; incluida en v1.9, solo Secretaría)

- Filtro de notas ya analizadas (Google Sheets): antes de procesar,
  la app compara la columna NoticiaId del dossier con la columna ID
  de la hoja "Base, boletín SGB" (primera hoja, "Mes actual") y
  solo procesa las notas que NO están en la hoja. El archivo
  descargable contiene solo las notas nuevas; al final se informa
  cuántas notas ya analizadas se omitieron.
- La hoja se lee en cada corrida vía exportación CSV pública (sin
  inicio de sesión, igual que los mapas de región/internet), así que
  si se agregan notas analizadas a la hoja, la siguiente corrida ya
  las excluye. La comparación tolera ID numérico, decimal ("123.0")
  y con espacios; las filas sin ID nunca se omiten (se procesan, por
  duda) y si el dossier no trae columna de ID, se procesa todo.
- El límite de 1.000 filas aplica a las notas NUEVAS, no al total del
  archivo: las omitidas no consumen llamadas a la API.
- Opción "Excluir notas ya analizadas (Google Sheets)" en ambas
  pestañas (activada por defecto). Si la hoja no se puede leer, el
  proceso se detiene con un mensaje claro en vez de reprocesar en
  silencio; desmarcando la opción se procesan todas las notas.
- Defensoría no se toca (sin esta función).
- Rendimiento (misma v1.8): la hoja trae más de 30 mil filas y 21
  columnas, pero la app ahora pide solo la columna ID al leerla
  (usecols), así no parsea ni carga en memoria títulos y resúmenes
  de 32 mil notas; la descarga es la misma (Google no permite bajar
  una sola columna), pero el parseo pasa de 21 columnas a 1 y el
  filtro en sí es una búsqueda en conjunto (instantánea). No hay
  caché: cada corrida lee la hoja actual para no excluir notas
  agregadas entre corridas. La app muestra "Leyendo notas ya
  analizadas (Google Sheets)…" mientras lo hace.

## Novedades v1.9 (2026-10-31; incluida en v1.10, solo Secretaría)

- Orden exacto del xlsx final para el boletín (por perfil
  "formato_boletin", solo Secretaría): ID Noticia, Fecha, Medio,
  Región, Tipo de Medio, Sección - Programa, Título, Duración - Nro.
  Caracteres, CPE, Audiencia, Tier, Tono_IA, Subtema_IA, TIPO, GÉNERO,
  Link Nota, texto, Link Ext, Web Ext, FECHA INFORME, HORA B,
  ID duplicada, Contexto analizado, Resumen - Aclaracion, Audio.
  En la pestaña estándar la salida es exactamente esas 25; en la
  personalizada van esas 25 primero y después las columnas
  personalizadas extra (para no perder datos propios).
- FECHA INFORME es la misma Fecha de la nota (mismo valor y mismo
  formato de fecha). HORA B es la hora del boletín según la hora de
  Bogotá en que se corre: antes de la 1 p.m. -> "1:00 p.m.", desde
  la 1 p.m. -> "6:00 p.m." (se usa hora de Bogotá, no la del
  servidor, que corre en UTC). Tema_IA no está en la lista y por
  tanto no se exporta en este formato, aunque se haya calculado.
- Defensoría no se toca (su perfil no trae el formato boletín y su
  salida queda como antes).

## Novedades v1.10 (2026-10-31, pendiente de push; solo Secretaría)

- Mismo Título => mismo Subtema_IA (garantía final determinista): dos
  notas con el título idéntico, o levemente igual, ya no pueden quedar
  con subtemas distintos. Causa: la unificación v4.31 tiene guarda de
  fidelidad (si ningún subtema es fiel al título Y cuerpo de todas las
  filas, no unifica) y después la guarda por fila y la puerta final
  anti-copia vuelven a separar subtemas (reformulación LLM por grupo,
  no determinista entre grupos). El nuevo pase final corre después de
  la puerta anti-copia y antes de volcar, sin LLM y sin guarda de
  fidelidad, y escribe el mismo subtema en las etiquetas de grupo y en
  los ajustes por fila: nada posterior lo separa. Solo toca el subtema
  (tono, tema, TIPO y GÉNERO quedan como están); hechos distintos que
  solo comparten la marca no se unen.
- Alias de respaldo (2026-10-31): 'Secretaría de' también vale si no
  se encuentran 'Secretaría General de la Alcaldía de Bogotá' ni
  'Secretaría General'. En la práctica, cualquier 'Secretaría de...'
  cuenta como mención (la comparación no distingue mayúsculas ni
  acentos). Los voceros Galán / Carlos Fernando Galán / Carlos Galán
  / el alcalde ya estaban en el perfil desde v1.7; no se veían en la
  app publicada porque v1.7-v1.10 siguen sin push (la app en vivo es
  v1.6): al publicar v1.10, el campo Vocero(s) mostrará todos los
  voceros del perfil por defecto.
- Defensoría no se toca.

## Novedades v1.11 (2026-10-31, pendiente de push; solo Secretaría)

- Corrección del orden del xlsx final (pedido del usuario 2026-10-31):
  entra "Link (Streaming - Imagen)" entre "texto" y "Link Ext", y sale
  "Web Ext". El orden queda: ID Noticia, Fecha, Medio, Región, Tipo de
  Medio, Sección - Programa, Título, Duración - Nro. Caracteres, CPE,
  Audiencia, Tier, Tono_IA, Subtema_IA, TIPO, GÉNERO, Link Nota, texto,
  Link (Streaming - Imagen), Link Ext, FECHA INFORME, HORA B,
  ID duplicada, Contexto analizado, Resumen - Aclaracion, Audio.
  (El usuario lo escribió como "Link (Streaming"; se usa la columna
  existente "Link (Streaming - Imagen".)
- La detección de la columna ID de la hoja ya analizadas ahora acepta
  también "ID Noticia" y "NoticiaId" (antes solo "ID").
- Defensoría no se toca.

## Novedades v1.12 (2026-10-31, nunca pusheada; incluida en v1.13; solo Secretaría)

- Foco exacto del perfil (corrección del usuario 2026-10-31): aliases
  SOLO "Secretaría General", "Secretaría General de la Alcaldía de
  Bogotá" y "Alcaldía de Bogotá"; voceros Miguel Silva Moyano, Miguel
  Silva, Carlos Fernando Galán, Galán, Carlos Galán, el alcalde. Salen
  "Alcaldía Mayor de Bogotá", "Secretaría General de Bogotá",
  "Secretaría General de la Alcaldía Mayor de Bogotá", "Distrito
  Capital", "Administración Distrital", "SGB", "Bogotá Camina Segura"
  y el alias de respaldo "Secretaría de" (que hacía valer CUALQUIER
  "Secretaría de..." y metía notas ajenas a la Secretaría General).
  Auditoría previa: el motor ya era idéntico al de API_2_Grill salvo
  las adiciones documentadas (umbral 3→2 para siglas, 'alerta',
  TIPO/GÉNERO, fix de título, filtro Sheets, boletín, Resumen); la
  agrupación no se tocó: el problema era el foco, no el motor.
- Tono: regla general determinista (vale para cualquier cliente):
  decreto/resolución/acuerdo/ordenanza sin crítica = Neutro (baja
  Negativo a Neutro; con crítica o léxico de falla/incumplimiento se
  respeta el Negativo; no toca Positivos). Corre al final, después de
  la auditoría Jev y de toda canonización de tono.
- Velocidad: las auditorías Jev (tono por grupo y temas por subtema
  distinto) eran secuenciales y dominaban el tiempo de 123 notas
  (más de 5 minutos). Ahora corren en paralelo con los mismos workers
  (8); las llamadas, los resultados por grupo y el orden de aplicación
  son idénticos: solo cambia el tiempo, no la calidad. Los lotes
  principales ya eran paralelos; el fetch de Sheets y el Resumen son
  segundos y no eran el cuello de botella.
- Defensoría no se toca.

## Novedades v1.13 (2026-10-31, nunca pusheada; incluida en v1.14; solo Secretaría)

- Incluye todo lo de v1.12 (foco exacto, regla decreto, Jev paralelo),
  que nunca se pusheó.
- Web Ext vuelve al xlsx del boletín como ÚLTIMA columna (tras Audio):
  Secretaría 26 columnas, Defensoría 24. (v1.11 la había sacado; el
  usuario la necesita para ver la URL web de la nota.)
- GÉNERO por URL web: si la Web Ext trae /opinion/, /columna(s)/ o
  /editorial/ y el grupo quedó como Noticia, la fila pasa a Opinión
  (ejemplo real: https://elpilon.com.co/opinion/columnas/caradura-este-senor
  ya no queda como Noticia). Solo sube Noticia a Opinión; nunca toca
  Entrevista, Opinión ni duplicadas. Mismo criterio del rescate por
  Sección, pero con la evidencia de la URL.
- Fidelidad FINAL por fila (lo grave de la agrupación): la guarda
  v4.35/v4.50 corría ANTES de la puerta anti-copia y del pase
  título-final, y esos dos reescriben subtemas sin re-verificar por
  fila (el título-final impone el canon sin guarda). Ahora, justo
  antes de volcar, cada fila vuelve a verificarse con el mismo cotejo
  (nombre propio + asunto en SU título/cuerpo): si el subtema final
  no corresponde a esa fila, recupera su especificidad con un rótulo
  de su propio titular (o 'Hecho informativo'). No rompe título
  idéntico = mismo subtema cuando el canon sí corresponde a cada fila;
  solo separa la fila cuyo cuerpo prueba otro hecho distinto. No toca
  tono, tema ni la etiqueta del grupo.
- Defensoría no se toca (salvo el motor compartido, que es idéntico).

## Novedades v1.14 (2026-10-31, nunca pusheada; incluida en v1.15; solo Secretaría)

- Incluye todo lo de v1.13 (nunca pusheada).
- Sin cambio de HORA B para Secretaría: sigue "1:00 p.m." antes de la 1
  p.m. de Bogotá y "6:00 p.m." desde la 1 p.m. El campo nuevo es
  genérico (ver Defensoría v1.10) y aquí queda explícito en "6:00 p.m.".
- Defensoría no se toca (salvo el motor compartido, que es idéntico).

## Novedades v1.15 (2026-10-31, PUSH HECHO, solo Secretaría)

- Incluye todo lo de v1.14 (nunca pusheada).
- Sin cambio de HORA B para Secretaría: sigue corte 13, antes
  "1:00 p.m.", después "6:00 p.m.". El horario del boletín ahora es
  un campo genérico de perfil (ver Defensoría v1.11) y aquí queda
  explícito con los valores de siempre.
- Defensoría no se toca (salvo el motor compartido, que es idéntico).

## Novedades v1.16 (2026-10-31, pendiente de push; solo Secretaría)

- FECHA INFORME es la fecha de procesamiento (Bogotá, mismo instante
  que HORA B), NO la Fecha de la nota: todas las filas llevan la
  misma fecha, la del día en que se corrió. Antes llevaba la Fecha
  de cada nota (v1.9). HORA B no cambia (corte 13, 1:00 p.m. /
  6:00 p.m.), confirmado por el usuario 2026-10-31.
- Defensoría no se toca (salvo el motor compartido, que es idéntico).
