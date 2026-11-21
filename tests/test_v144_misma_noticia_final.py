"""v1.44: la misma noticia no queda repartida entre subtemas distintos.

Casos reales del boletín del 2026-11-21 (revisión humana):
- «Alerta Fase 1»: la memoria de subtemas fijó el rótulo solo en las filas
  que coincidían con la referencia y en su grupo; las demás filas de la
  misma noticia quedaron con otro rótulo.
- La viuda de Miguel Uribe acusa a Petro: unas notas «Entorno Gustavo
  Petro», otras «Acusación contra Gustavo Petro por atentado».
- «Declaratoria alerta ambiental fase 1…» vs «…Fase 1…».
- «Bar Week 2026 en Bogotá» -> «Bar Week 2026».
- Metro Tinto: el «aseguró» de un trabajador volvía Institucional la nota.
- Columna en primera persona (pares.com.co) salía Noticia y Positivo.
"""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import memoria_cliente as mc
import analyzer_tono_tema as az
import pipeline
import perfil_cliente

P = perfil_cliente.cargar_perfil('secretaria_general_de_la_alcaldia_de_bogota')
B, A, V = P['brand'], P['aliases'], P['voceros']
KM = {'titulo': 'Título'}
REGLAS = {'aspirantes': 'Aspirantes Alcaldía de Bogotá', 'petro': 'Entorno Gustavo Petro'}

TXT_ALERTA = ('La Alcaldía de Bogotá, a través de la Secretaría de Ambiente, declaró Alerta Fase 1 '
              'por contaminación del aire en cuatro zonas del suroccidente de Bogotá, durante este '
              'sábado 21 de noviembre, tras 36 horas consecutivas de calidad del aire regular.')


# --- memoria: propaga por noticia, no solo por grupo -----------------------

def _fila(tit, sub, tono='Neutro', txt=''):
    return {'Título': tit, 'CuerpoEs': txt or tit, 'Tono_IA': tono, 'Subtema_IA': sub}


def test_memoria_propaga_a_toda_la_noticia():
    rows = [_fila('Bogotá declara alerta por contaminación del aire en cuatro zonas del suroccidente',
                  'Alerta Fase 1 por contaminación en suroccidente', txt=TXT_ALERTA),
            _fila('Secretaría de Ambiente declaró en Alerta Fase 1 cuatro zonas de Bogotá',
                  'Alerta Fase 1 por contaminación en suroccidente', txt='Otra redacción ' * 20),
            _fila('Alerta por aire en Kennedy y Puente Aranda: empresas paran equipos',
                  'Alerta Fase 1 por contaminación en suroccidente', txt='Tercera redacción ' * 20)]
    ent = [mc._entrada(rows[0]['Título'], TXT_ALERTA,
                       'Declaratoria alerta ambiental Fase 1 suroccidente')]
    mapa = {0: 1, 1: 2, 2: 3}                       # tres grupos distintos
    # Sin noticias (comportamiento v1.42): solo cambia la fila que coincide.
    r1 = [dict(r) for r in rows]
    az.anclar_subtemas_previos(r1, KM, ent, mapa=mapa)
    assert [r['Subtema_IA'] for r in r1].count('Declaratoria alerta ambiental Fase 1 suroccidente') == 1
    # Con la noticia del pase por noticia: las tres.
    r2 = [dict(r) for r in rows]
    az.anclar_subtemas_previos(r2, KM, ent, mapa=mapa, noticias=[[0, 1, 2]])
    assert {r['Subtema_IA'] for r in r2} == {'Declaratoria alerta ambiental Fase 1 suroccidente'}


def test_memoria_tono_manual_no_se_impone_a_otros_grupos():
    rows = [_fila('Bogotá declara alerta por contaminación del aire en cuatro zonas del suroccidente',
                  'Alerta', tono='Neutro', txt=TXT_ALERTA),
            _fila('Secretaría de Ambiente declaró en Alerta Fase 1 cuatro zonas de Bogotá',
                  'Alerta', tono='Neutro', txt='Otra redacción ' * 20)]
    ent = [dict(mc._entrada(rows[0]['Título'], TXT_ALERTA, 'Declaratoria alerta Fase 1'),
                manual=True, tono='Positivo')]
    az.anclar_subtemas_previos(rows, KM, ent, mapa={0: 1, 1: 2}, noticias=[[0, 1]])
    assert rows[0]['Tono_IA'] == 'Positivo'
    assert rows[1]['Tono_IA'] == 'Neutro'           # el tono no viaja a otro grupo
    assert rows[1]['Subtema_IA'] == 'Declaratoria alerta Fase 1'   # el subtema sí


def test_memoria_rotulos_mezclados_gana_el_mas_repetido():
    rows = [_fila('Alerta ambiental uno en el suroccidente de la ciudad hoy', 'x', txt='a ' * 80),
            _fila('Alerta ambiental dos en el suroccidente de la ciudad hoy', 'x', txt='b ' * 80),
            _fila('Alerta ambiental tres en el suroccidente de la ciudad hoy', 'x', txt='c ' * 80)]
    ent = [mc._entrada(rows[0]['Título'], 'a ' * 80, 'Rótulo A'),
           mc._entrada(rows[1]['Título'], 'b ' * 80, 'Rótulo A'),
           mc._entrada(rows[2]['Título'], 'c ' * 80, 'Rótulo B')]
    az.anclar_subtemas_previos(rows, KM, ent, mapa={0: 1, 1: 2, 2: 3}, noticias=[[0, 1, 2]])
    assert {r['Subtema_IA'] for r in rows} == {'Rótulo A'}


# --- Petro como alcalde: contexto y propagación por noticia ----------------

def test_petro_contexto_epoca():
    f = az.es_nota_petro_alcalde_contexto
    assert f('A Miguel lo mató Gustavo Petro: la acusación de María Claudia Tarazona',
             'Su señalamiento está relacionado con los enfrentamientos que comenzaron cuando su '
             'esposo era concejal de Bogotá y Petro ocupaba la Alcaldía de la ciudad.')
    assert f('Esposa de Miguel Uribe señala a Gustavo Petro de ordenar su muerte',
             'La mujer asegura que Miguel Uribe fue un férreo opositor de Petro desde el Concejo '
             'de Bogotá en 2012. En ese entonces, el expresidente era alcalde de Bogotá.')
    # Sin Petro en el titular: no basta el contexto.
    assert not f('Viuda de Miguel Uribe habla de la investigación',
                 'En ese entonces, el expresidente era alcalde de Bogotá.')
    # El alcalde actual responde a Petro: no es su época de alcalde.
    assert not f('Galán le responde a Petro por el metro',
                 'El alcalde Carlos Fernando Galán respondió a Petro sobre el metro elevado.')


def test_petro_propaga_en_la_noticia():
    ctx_si = ('Tarazona recordó que su esposo presentó una ponencia negativa sobre el POT impulsado '
              'por la Alcaldía de Petro.')
    rows = [{'Título': 'María Claudia Tarazona acusa a Gustavo Petro de ordenar el asesinato',
             'CuerpoEs': 'La viuda del senador habló con Semana. ' * 30,
             'Contexto analizado': ctx_si, 'Tono_IA': 'Neutro',
             'Subtema_IA': 'Acusación contra Gustavo Petro por atentado', 'TIPO': 'Información general'},
            {'Título': 'Viuda de Miguel Uribe Turbay acusa a Gustavo Petro de ordenar su asesinato',
             'CuerpoEs': 'Lo dijo en una entrevista con Vicky Dávila. ' * 30,
             'Contexto analizado': 'Lo dijo en una entrevista con Vicky Dávila.', 'Tono_IA': 'Neutro',
             'Subtema_IA': 'Acusación contra Gustavo Petro por atentado', 'TIPO': 'Información general'},
            {'Título': 'Petro llamó embustero a De la Espriella por la Autonorte',
             'CuerpoEs': 'Discusión por la obra de la Autopista Norte. ' * 30,
             'Contexto analizado': 'Discusión por la obra.', 'Tono_IA': 'Neutro',
             'Subtema_IA': 'Inicio de obras en Autopista Norte', 'TIPO': 'Información general'}]
    out = az.aplicar_subtemas_politicos(rows, KM, REGLAS, voceros=V, noticias=[[0, 1], [2]])
    assert rows[0]['Subtema_IA'] == rows[1]['Subtema_IA'] == 'Entorno Gustavo Petro'
    assert rows[2]['Subtema_IA'] == 'Inicio de obras en Autopista Norte'
    assert out['petro'] == 2


def test_petro_no_propaga_sin_noticias():
    rows = [{'Título': 'Viuda de Miguel Uribe Turbay acusa a Gustavo Petro de ordenar su asesinato',
             'CuerpoEs': 'Lo dijo en una entrevista. ' * 30, 'Contexto analizado': '',
             'Tono_IA': 'Neutro', 'Subtema_IA': 'Acusación', 'TIPO': 'Información general'}]
    az.aplicar_subtemas_politicos(rows, KM, REGLAS, voceros=V)
    assert rows[0]['Subtema_IA'] == 'Acusación'


# --- forma del subtema ------------------------------------------------------

def test_unifica_mayusculas_y_quita_en_bogota():
    rows = [{'Subtema_IA': 'Declaratoria alerta ambiental Fase 1 suroccidente'},
            {'Subtema_IA': 'Declaratoria alerta ambiental Fase 1 suroccidente'},
            {'Subtema_IA': 'Declaratoria alerta ambiental fase 1 suroccidente'},
            {'Subtema_IA': 'Bar Week 2026 en Bogotá'},
            {'Subtema_IA': 'Aspirantes Alcaldía de Bogotá', '_subtema_politico': 'aspirantes'},
            {'Subtema_IA': 'Obras en Bogotá'},
            {'Subtema_IA': '-', 'is_duplicate': True}]
    az.unificar_forma_subtemas(rows)
    assert rows[2]['Subtema_IA'] == 'Declaratoria alerta ambiental Fase 1 suroccidente'
    assert rows[3]['Subtema_IA'] == 'Bar Week 2026'
    assert rows[4]['Subtema_IA'] == 'Aspirantes Alcaldía de Bogotá'
    assert rows[5]['Subtema_IA'] == 'Obras en Bogotá'           # quedaría una sola palabra
    assert rows[6]['Subtema_IA'] == '-'


def test_forma_manual_gana():
    rows = [{'Subtema_IA': 'Alerta fase 1'}, {'Subtema_IA': 'Alerta fase 1'},
            {'Subtema_IA': 'Alerta Fase 1', '_correccion_manual': True}]
    az.unificar_forma_subtemas(rows)
    assert {r['Subtema_IA'] for r in rows} == {'Alerta Fase 1'}


# --- TIPO: el verbo de habla debe ser del actor -----------------------------

def test_actor_habla_cerca():
    act = [az.nz(x) for x in [B] + A + V if len(az.nz(x)) >= 4]
    assert not az._actor_habla_cerca(
        'Uno de ellos aseguró que, cuando llegan muy cansados, la señora les saca una sonrisa, en '
        'un emprendimiento que incluso ya visitó el alcalde de Bogotá, Carlos Fernando Galán.', act)
    assert az._actor_habla_cerca(
        'La medida es preventiva, señaló el alcalde Carlos Fernando Galán.', act)
    assert az._actor_habla_cerca(
        'Carlos Fernando Galán, en rueda de prensa, aseguró que habrá más controles.', act)


def test_metro_tinto_queda_informacion_general():
    tit = 'Metro Tinto, el emprendimiento que nació junto a las obras del metro de Bogotá'
    ctx = ('Alrededor de las obras del metro surgen historias de emprendimiento, como Metro Tinto. '
           'Uno de ellos aseguró que, cuando llegan muy cansados, la señora les saca una sonrisa, en '
           'un emprendimiento que incluso ya visitó el alcalde de Bogotá, Carlos Fernando Galán.')
    g = [{'grupo': 1, 'titulo': tit, 'contexto': ctx}]
    e = {1: {'tipo': 'Información general'}}
    az.aplicar_tipo_por_actor(g, e, B, A, V)
    assert e[1]['tipo'] == 'Información general'


# --- columna en primera persona ----------------------------------------------

COLUMNA = ('Hace seis meses compramos la boleta para ver a Gorillaz. Según la empresa que los '
           'vendía, se presentaría en el Movistar Arena. Al cabo de los meses sucedió lo que muchos '
           'temíamos, lo que no queremos que nos pase los que vamos a un evento. El MedPlus tiene '
           'evidentes problemas de conectividad. Algunos, como Carlos Fernando Galán, llegaron con '
           'la ambición de cambiarle la cara a la ciudad construyendo un metro.')
ENTREVISTA = ('La encuesta reveló una mejoría. Hoy, somos más optimistas, tenemos más orgullo por la '
              'ciudad. "Hoy las personas se sienten orgullosas", afirmó el director. Hemos observado '
              'un aumento. No estamos ante un cambio de tendencia. Empezamos a ver una recuperación '
              'que tuvimos en las alcaldías anteriores.')


def test_columna_primera_persona():
    assert pipeline.es_columna_primera_persona(COLUMNA, 'El peor lugar para ir a un concierto en Bogotá')
    assert not pipeline.es_columna_primera_persona(
        ENTREVISTA, "'Bogotá es una ciudad de oportunidades', afirma el director")
    assert not pipeline.es_columna_primera_persona(
        '«Creo que vamos bien, tenemos que seguir y debemos cumplir», dijo el alcalde.', 'Galán')


def test_aplicar_columna_primera_persona():
    rows = [{'Título': 'El peor lugar para ir a un concierto en Bogotá', 'CuerpoEs': COLUMNA,
             'Tipo de Medio': 'Internet', 'GÉNERO': 'Noticia', 'Tono_IA': 'Positivo',
             'TIPO': 'Información general'},
            {'Título': 'El peor lugar para ir a un concierto en Bogotá', 'CuerpoEs': COLUMNA,
             'Tipo de Medio': 'Internet', 'GÉNERO': '-', 'Tono_IA': 'Duplicada',
             'is_duplicate': True}]
    assert pipeline.aplicar_columna_primera_persona(rows) == 1
    assert rows[0]['GÉNERO'] == 'Opinión' and rows[0]['Tono_IA'] == 'Neutro'
    assert rows[0]['TIPO'] == 'Información general'
    assert rows[1]['GÉNERO'] == '-'
