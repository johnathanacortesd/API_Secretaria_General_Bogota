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

## Motor Claude Haiku

En la pestaña estándar, «Motor de clasificación» ofrece dos opciones:

- **OpenAI (actual)**: el motor de siempre (gpt-6-luna + Jev + PKL). Es el valor por defecto y no cambia.
- **Claude Haiku (agente + revisor)**: un agente Claude Haiku (`motor_haiku.py`, Claude Agent SDK) clasifica Tono_IA, Subtema_IA y, si se pide, Tema_IA (de la lista de Temas cuando se elige una). Al final un subagente `revisor-subtemas` revisa la consistencia. La limpieza, el Contexto analizado, el agrupamiento, las guardas deterministas de tono y subtema y el layout del Excel son los mismos. No usa PKL ni Jev.

Con el perfil de la Secretaría (`clasificar_tipo_genero`), el motor Haiku también llena **TIPO** (Institucional, Información general, Programas y proyectos, Opinión de terceros, Ranking) y **GÉNERO** (Noticia, Reportaje, Opinión, Entrevista, Editorial), en las mismas columnas que OpenAI. El agente recibe Sección - Programa, Tipo de Medio, Medio y si la Web Ext contiene "opinion"; los duplicados heredan. Después corren las mismas reglas deterministas del camino OpenAI (guardia de Entrevista, Sección, URL, Ranking, TIPO por actor) y una regla final propia de Haiku que gana sobre el modelo: Web Ext o Sección con opinión/columna/columnistas da GÉNERO Opinión y TIPO Opinión de terceros (salvo Ranking o autor de la entidad); "editorial" da Editorial; laopinion y desopinion no cuentan.

El motor Haiku se factura a la clave de Claude Platform. Agrega en los Secrets de Streamlit:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

Sin esa clave, elegir Claude Haiku muestra un error y el motor OpenAI sigue funcionando.

## Archivos

- `app.py` — interfaz (Grill v4.67 + sección Resumen, versión visible v1.17)
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

## Novedades v1.16 (2026-10-31, PUSH HECHO, solo Secretaría)

- FECHA INFORME es la fecha de procesamiento (Bogotá, mismo instante
  que HORA B), NO la Fecha de la nota: todas las filas llevan la
  misma fecha, la del día en que se corrió. Antes llevaba la Fecha
  de cada nota (v1.9). HORA B no cambia (corte 13, 1:00 p.m. /
  6:00 p.m.), confirmado por el usuario 2026-10-31.
- Defensoría no se toca (salvo el motor compartido, que es idéntico).

## Novedades v1.17 (2026-10-31, pendiente de push; solo Secretaría)

- Columna "ENLACE" como texto plano: el enlace se escribe tal cual,
  sin hipervínculo (con write_string: write() lo convertiría en
  hipervínculo solo). Aplica a cualquier capitalización (ENLACE,
  Enlace, enlace). Link Nota, Link Ext, Web Ext y Audio no cambian
  (siguen como hipervínculos).
- Defensoría no se toca (salvo el motor compartido, que es idéntico).

## Novedades v1.29 (2026-11-02; solo Secretaría)

Coherencia de subtema y tono: noticias iguales o similares = mismo
subtema y mismo tono; el subtema siempre corresponde a su noticia.

- Causas encontradas: (1) los lotes de etiquetado corren en paralelo y
  no se ven entre sí, y la unificación LLM previa solo veía la lista de
  subtemas, sin la noticia, y no fusionaba nada si había un Negativo;
  (2) los pases finales por fila (fidelidad, anti-copia, título-final)
  reescribían subtemas DESPUÉS de unificar el tono, así que el mismo
  subtema podía salir con tonos distintos; (3) los ejemplos del prompt
  enseñaban dos subtemas distintos para la misma noticia (PAE, Canal
  del Dique); (4) el perfil no traía guía de subtemas para Bogotá.
- Consolidación por hecho (`consolidar_hechos_llm`): el modelo ve todas
  las noticias (titular + entrada + subtema propuesto) y agrupa las que
  cuentan el mismo hecho con un solo subtema. Cada agrupación se valida
  en código: el subtema debe ser fiel (nombres propios + asunto) a CADA
  noticia del hecho y bien formado (sin copia del titular); si no, no se
  agrupa. Hechos distintos que solo comparten al alcalde, la ciudad o la
  entidad no se unen. También corrige un subtema que no corresponde a su
  noticia, solo si el actual falla el cotejo de fidelidad. Si la llamada
  falla, se usa la unificación anterior.
- Garantía final (`garantizar_coherencia_hecho`), último pase antes de
  volcar: misma noticia (mismo grupo, mismo hecho consolidado o mismo
  titular) => mismo subtema, si hay un rótulo fiel a todas; mismo
  subtema final => mismo tono (mayoría por número de notas; empate =>
  Neutro).
- Prompt: regla explícita de coherencia (mismo hecho => mismo subtema y
  tono; no agrupar por agrupar; cada subtema describe su grupo) y
  ejemplos contradictorios corregidos.
- Perfil: `guia_subtema` con el enfoque Alcaldía de Bogotá / alcalde
  Galán / Secretaría General (hecho concreto, no la entidad; ejemplos).
- Corrección: `volcar_analisis_en_filas` usaba `km` sin recibirlo
  (NameError en el respaldo de subtema vacío).

## Novedades v1.30 (2026-11-02; solo Secretaría)

Precisión de tema (Subtema_IA), tono, TIPO y columna texto, según la
especificación del usuario.

- **Tema (Subtema_IA)**: indica de qué habla la nota. Si trata de un
  proyecto, programa u obra con nombre propio, es ese nombre ("Metro de
  Bogotá", "Regiotram del Norte", "Línea 137"); si no, el asunto concreto.
  El mismo tema lleva el mismo rótulo. El validador acepta nombres propios
  de 2+ palabras aunque estén en el titular (antes "Línea 137" se
  rechazaba por corto y por copia).
- **Agrupación**: puede haber noticias sin agrupar. Solo se agrupan las
  que el modelo ve como el mismo hecho y cuyo rótulo común corresponde al
  titular y al **Contexto analizado** de cada una.
- **Tono por hecho, no por tema**: la misma noticia lleva un solo tono,
  pero dos noticias distintas del mismo tema (avance del metro vs.
  críticas por sobrecostos del metro) conservan cada una el suyo.
- **Tono enfocado en marca, alias y voceros**: criterio del perfil con
  la definición del usuario (Positivo = destaca gestión o labor;
  Negativo = críticas o funcionarios en corrupción; Neutro = mención
  referencial). Corrección: las reglas que detectan "crítica dirigida a
  la marca" ignoraban a los voceros, así que una crítica al alcalde
  Galán o al secretario Miguel Silva bajaba de Negativo a Neutro; y
  "cuestionan a la Alcaldía de Bogotá" no coincidía por el artículo.
  La pestaña personalizada usa el criterio del perfil si no se escribe
  otro.
- **TIPO**: reglas reescritas con las definiciones del usuario
  (Institucional = nombramientos, presupuesto, ampliación, sede…;
  Proyectos y programas = gestión, programas, subsidios, jornadas, aunque
  los anuncie el alcalde; Opinión de terceros; Ranking; Información
  general). Antes, la sola intervención del vocero hacía Institucional
  cualquier nota. La misma noticia lleva el mismo TIPO (mayoría clara).
- **texto**: más de 15 palabras. Si el texto derivado del Contexto
  analizado es más corto, se completa con oraciones completas y literales
  del Resumen - Aclaracion (sin palabras que no estén ahí; sin el
  titular). Si el resumen no alcanza, queda lo que haya.

## Novedades v1.31 (2026-11-02; solo Secretaría)

Agrupación lógica y estricta: solo se agrupan noticias iguales o muy
parecidas; las notas específicas conservan su propio subtema.

- **Agrupación estricta** (`agrupacion_estricta: true` en el perfil): dos
  noticias comparten subtema SOLO con evidencia: título igual o muy
  parecido (ratio/token_sort >= 85 % sobre palabras de contenido),
  Contexto analizado con pasajes literales compartidos (>= 50 % de
  5-gramas) o CuerpoEs igual o muy parecido (>= 50 %). Se omiten las
  uniones por parecido del rótulo (canonización, unificación por
  similitud, rótulos finales) y por "ancla" temática (misma historia de
  riesgo, mismo evento, ancla de persona). Los pases finales por título
  usan el mismo umbral estricto (antes token_set 60-70, que unía
  titulares que solo compartían palabras).
- **Guía de subtema**: precisa por nota; usa el nombre del proyecto
  solo si la nota trata de él; no forzar una nota a un tema ajeno.
- **Más ágil con el mismo modelo**: la consolidación ya no envía todo el
  dossier al modelo; solo los grupos con evidencia, y sin llamada si uno
  de sus subtemas ya es fiel a todos. La auditoría de tono Jev corre en
  paralelo con el etiquetado (antes esperaba a que terminara).
- **Tono, correcciones**:
  - El patrón de "crítica" no exigía inicio de palabra: "atac"
    coincidía dentro de "contratación", y cualquier nota de contratación
    del distrito se trataba como crítica (Positivo bajaba a Neutro).
  - Cuando la marca o su vocero es sujeto de una gestión ("la Alcaldía
    presentó…", "el alcalde entregó…"), el Positivo ya no baja a Neutro
    por tener una sola mención.
  - Empates de tono dentro de la misma noticia: se deciden con la
    evidencia del texto (gestión de la marca => Positivo; crítica
    dirigida => Negativo) en vez de ir siempre a Neutro.

## Novedades v1.32 (2026-11-02; solo Secretaría)

- Se quita la sección "📝 Resumen para informe" (pedido del usuario) y su
  módulo `resumen_informe.py`. Las secciones anteriores de este README que
  la describen quedan como historial.

## Novedades v1.33 (2026-11-02; solo Secretaría)

Correcciones a partir de la evaluación de un dossier real (189 notas, boletín
1 p.m. del 2026-11-02): 107 de 176 notas salían Positivas y 0 Negativas; más
de 60 Positivos eran menciones referenciales.

- **Tono solo por gestión** (flag `tono_solo_gestion` en el perfil):
  - Que el alcalde o la entidad *hable* (dijo, señaló, recordó) o firme una
    columna ya no sube a Positivo: el Positivo exige gestión o labor.
  - Menciones que no son de la marca se ignoran para el tono: el cargo
    ("aspirante/candidato a la Alcaldía de Bogotá", "cuando Petro era
    alcalde", "durante la administración de Petro", "sucesor del alcalde"),
    otros alcaldes ("el alcalde Cristian Portilla", "el alcalde de Cali") y
    homónimos del vocero ("Juan Manuel Galán").
  - Condolencias, homenajes y reacciones del alcalde en noticias de
    fallecimiento o despedida => Neutro (69 notas sobre Navarro Wolff salían
    Positivas), salvo que la Alcaldía ejecute una gestión (anuncia, entrega…).
  - Opinión de terceros con preocupación o crítica sobre la marca no puede
    ser Positivo, y la regla del distrito no la sube.
  - Criterio del perfil: sin "declaración que los deja bien" y con la lista
    explícita de casos Neutros.
  - Repetición sin conexión sobre el dossier: Positivos 107 -> 30.
- **Variantes del mismo rótulo** (con agrupación estricta): "Fallecimiento de
  Antonio Navarro" = "...Wolff" = "Muerte de Antonio Navarro Wolff" se unen
  si el rótulo elegido corresponde a cada nota (Navarro: 18 -> 14 subtemas;
  los ángulos distintos, como trayectoria o relación con Petro, quedan
  aparte).
- **Columna texto**: si el texto es un crédito al final del Resumen
  ("Fuente: Alcaldía de Bogotá."), se completa con las oraciones
  anteriores, literales (13 notas tenían 4 a 11 palabras).

### v1.33, segunda parte: calibración con 132 notas etiquetadas a mano

Con el archivo de etiquetas manuales del usuario (IMPACTO, TEMA, TIPO,
GÉNERO) se midió el acierto real y se calibraron las reglas:

| | v1.32 | v1.33 |
|---|---|---|
| Tono | 34 % | 93 % |
| TIPO | 43 % | 75 % |
| GÉNERO | 100 % | 100 % |
| Subtemas distintos (manual: 27) | 57 | 35 |
| Navarro Wolff (71 notas) | 19 subtemas | 3 |

- **Tono** (con `tono_solo_gestion`):
  - Medidas restrictivas del Distrito en el titular (pico y placa,
    restricciones, decretos, calendario) => Neutro.
  - Regla del usuario: Alcaldía solo como crédito => Neutro, pero si una
    secretaría distrital, una entidad del Distrito o un funcionario
    ejecuta la gestión => Positivo. También es Positivo el titular con
    "Bogotá" o la Alcaldía como sujeto de una gestión ("Bogotá nombra",
    "Bogotá abre convocatoria").
  - Nombramientos, convocatorias, aperturas, inversiones y capturas
    cuentan como gestión.
  - Crítica de un tercero que nombra a la marca o a su vocero => Negativo
    (si no la nombra, Neutro).
- **TIPO** (flag `tipo_por_actor`): medida normativa del Distrito =>
  Institucional; sin mención válida de la marca (solo el cargo,
  administraciones pasadas, otros alcaldes u homónimos) => Información
  general; Información general en que el alcalde, el secretario o la
  entidad habla o actúa oficialmente => Institucional.
- **Subtema: un solo subtema por evento grande** (regla del usuario, en
  agrupación estricta): las notas cuyos titulares comparten una frase
  distintiva repetida en al menos 3 titulares ("navarro wolff", "pico
  placa", "plan retorno") toman el subtema más frecuente del bloque, si
  corresponde a cada nota (titular + Contexto analizado + inicio del
  cuerpo).

## Novedades v1.34 (2026-11-02; Secretaría y Defensoría)

Forma del subtema (pedido del usuario: casos reales "Días dejan cinco muertos
en el suroccidente" y "Ellos, una bebé de dos meses"):

- Un subtema **jamás** lleva comas ni puntos (salvo comas de un nombre
  propio de programa, como "Bogotá, mi Ciudad, mi Casa", y cifras como
  "$42,7"), **jamás** empieza con pronombre ("Ellos", "Esto", "Su"…) y
  **jamás** es una oración "sujeto + verbo" ("Días dejan…", "Ministerio
  anunció…").
- Causa: el respaldo que arma un subtema con el titular o una oración del
  cuerpo se usaba en pases que corren después de la puerta anti-copia. Ahora:
  el validador marca estos problemas (la puerta anti-copia los manda a
  reformular), el respaldo no devuelve rótulos así (los repara sin inventar:
  "Cinco muertos en el suroccidente", "Bebé de dos meses") y una revisión
  final obligatoria antes de exportar prefiere el subtema del grupo.
- La guarda de fidelidad ya no cambia un subtema con relación con la nota por
  un respaldo peor (copia del titular o con verbo), como en Defensoría v1.28.

## Novedades v1.35 (2026-11-02; port de Grill v4.70)

Tema y subtema coherentes con el TEXTO de la noticia (pedido del usuario:
noticias iguales o similares no quedaban con el mismo subtema, y se ponían
subtemas a noticias que no tenían que ver, "agrupando por agrupar").

- **Similitud por texto** (`coherencia_texto.py`, compartido con Grill):
  TF-IDF sobre Título + Contexto analizado + CuerpoEs, sin tildes, sin
  palabras vacías y sin los tokens de marca/alias/voceros. Calibración: la
  misma noticia reescrita ≈ 0.55-0.70; hechos distintos del mismo asunto ≈
  0.15-0.20; notas ajenas ≈ 0.00-0.05.
- **Agrupación**: las uniones solo por parecido del titular se vetan si los
  dos CuerpoEs (250+ caracteres) no se parecen (coseno < 0.20). Aplica
  también con `agrupacion_estricta`.
- **Coherencia de subtemas** (`coherencia_subtemas_por_texto`), tras las
  unificaciones/consolidación y antes de los subtemas fijos, del tono y del
  tema: separa las notas sin relación textual con el subtema que recibieron
  (recuperan su subtema propio si es fiel o reciben uno nuevo) y une la
  misma noticia (similitud ≥ 0.45) bajo el rótulo de la mayoría si es fiel
  a todas. La puerta anti-copia no puede devolver un subtema rechazado.
- **Tema**: las familias de subtemas se separan si sus Contexto analizado no
  tienen relación y se unen si son muy parecidos (≥ 0.30).
- **Contexto analizado** desde el CuerpoEs cuando trae marca/alias/vocero;
  voceros también por nombre + primer apellido (expansión automática).
- **Columna texto**: quita el Título aunque difiera en forma (comillas,
  espacios, entidades); conserva el mínimo de 15 palabras de v1.30.
- `Link Ext` ya salía como texto plano desde v1.17; sin cambios.
- Rótulo de emergencia: nominaliza el verbo del titular («Secretaría General
  lanza ventanilla…» → «Lanzamiento de ventanilla…»).
