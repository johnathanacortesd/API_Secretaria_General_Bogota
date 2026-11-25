"""v1.49 (dossier real 2026-11-25): columnas texto/Resumen intercambiadas en
el boletín, extracto del cliente sin menciones ajenas ni restos del título, y
notas del mismo hecho con subtemas distintos llegan juntas al evaluador."""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az
import contexto_cliente as cc
import evaluador_agrupacion as ev
from coherencia_texto import texto_sin_titulo
from pipeline import BOLETIN_COLUMNAS

DET = az.detector_cliente('Secretaría General de la Alcaldía de Bogotá',
                          ['Secretaría General', 'Alcaldía de Bogotá', 'Alcaldía Mayor de Bogotá'],
                          ['Carlos Fernando Galán', 'Galán', 'el alcalde'], distrito=True)


def test_boletin_texto_y_resumen_intercambiados():
    c = BOLETIN_COLUMNAS
    assert c.index('Resumen - Aclaracion') == c.index('Link Nota') + 1
    assert c.index('texto') == c.index('Contexto analizado') + 1
    assert len(c) == len(set(c)) == 26


def test_menciones_ajenas_no_son_del_cliente():
    ajenas = ['el secretario general de las Naciones Unidas reconoció los avances',
              'estuvieron implicados el alcalde mayor Samuel Moreno , su hermano',
              'tras haber sido destituido como alcalde de Bogotá.',
              'En 2013, cuando fungía como alcalde de Bogotá, fue destituido',
              'que llegó a convertirse en alcalde de Bogotá y luego en presidente',
              'Juan Carlos Losada, excongresista liberal que suena para la alcaldía de Bogotá.',
              'había sido el asesor jurídico de Petro en la Alcaldia de Bogotá',
              'congresistas, el alcalde (Samuel Moreno), el gobernador (Álvaro Cruz)']
    for t in ajenas:
        assert not DET.menciones(t), t
    propias = ['El alcalde Mayor de Bogotá , Carlos Fernando Galán, hizo un llamado',
               'el alcalde mayor Carlos Fernando Galán anunció',
               'la Consejería de Relaciones Internacionales de la Secretaría General de la ciudad',
               'La Alcaldía de Bogotá anunció la firma de contratos']
    for t in propias:
        assert DET.menciones(t), t


def test_texto_sin_cierre_suelto_del_titulo():
    tit = '¿1.500 trabajadores chinos para terminar el Metro de Bogotá? ¿Quién responde'
    ctx = tit + '? Es importante exigirle al alcalde Galán que explique los atrasos.'
    assert texto_sin_titulo(ctx, tit).startswith('Es importante')


def test_oracion_repetida_entra_una_vez():
    o = ('Recuerda que los usuarios que quieran ser exentos del pico y placa pueden registrarse '
         'en la página de la Secretaría Distrital de Movilidad.')
    cuerpo = o + ' Hoy circulan las placas impares en toda la ciudad. ' + o
    meta = cc.construir(cuerpo, 'Pico y placa', DET)
    assert meta['contexto'].count('Recuerda que los usuarios') == 1


def test_mismo_asunto_con_subtemas_distintos_es_candidato():
    rows = [{'Título': 'Bogotá firma contratos por diez años con EPM y ETB',
             'Contexto analizado': 'La Alcaldía firmó con EPM la operación del alumbrado público.'},
            {'Título': 'Bogota to Modernize Public Lighting With Medellin EPM',
             'Contexto analizado': 'Mayor Carlos Fernando Galan announced the EPM partnership.'},
            {'Título': 'Pico y placa para este miércoles',
             'Contexto analizado': 'Circulan las placas impares.'},
            {'Título': 'Crítica al pico y placa solidario',
             'Contexto analizado': 'El columnista critica el pico y placa solidario.'}]
    rows += [{'Título': 'Nota %d sobre otro tema' % k, 'Contexto analizado': 'Texto %d distinto.' % k}
             for k in range(20)]
    mapa = {i: i + 1 for i in range(len(rows))}
    etq = {1: {'sub_tema': 'Nuevo modelo de alumbrado público'},
           2: {'sub_tema': 'Nuevo operador del alumbrado público'},
           3: {'sub_tema': 'Pico y placa del 25 de noviembre'},
           4: {'sub_tema': 'Reclamo por cierre de vías'}}
    sin = ev.construir_candidatos(rows, mapa, {'titulo': 'Título'})
    con = ev.construir_candidatos(rows, mapa, {'titulo': 'Título'}, etiquetas=etq)
    assert [0, 1] not in sin['comps'] and [0, 1] in con['comps']
    # Un solo núcleo compartido no basta («pico» y «placa» con «cierre de vías»: nada).
    assert not any(2 in c and 3 in c for c in con['comps'])


# ─── v1.50: compilación de titulares (City TV «Titulares», 2026-11-25) ──────
TITULARES = (
    '1. Once horas completa la toma de rehenes en un almacén Éxito de Cartagena. Hombres armados '
    'retuvieron a cerca de 30 personas.\n\n'
    '2. A esta hora, unidades élite de la Policía Nacional mantienen rodeado el almacén. Dos '
    'negociadores están cara a cara con los delincuentes para buscar una salida segura.\n\n'
    '3. A diez años de la firma del Acuerdo de Paz, el secretario general de las Naciones Unidas '
    'reconoció los avances alcanzados.\n\n'
    '4. Más de 63.000 usuarios de TransMilenio resultaron afectados por las protestas en la avenida '
    'Caracas. El portal estuvo cerrado durante varios minutos.\n\n'
    '5. La reina de Dinamarca se encuentra en Bogotá, donde se reunió con el alcalde Carlos Fernando '
    'Galán y el vicepresidente José Manuel Restrepo. La monarca continuará su recorrido por el país '
    'con una agenda de cooperación en salud, energía y medio ambiente.\n\n'
    '6. Shakira anunció una millonaria donación destinada a la educación de los niños.')
REINA = ('La reina de Dinamarca se encuentra en Bogotá, donde se reunió con el alcalde Carlos Fernando '
         'Galán y el vicepresidente José Manuel Restrepo. La monarca continuará su recorrido por el país '
         'con una agenda de cooperación en salud, energía y medio ambiente.')


def test_titulares_solo_el_punto_del_cliente_completo():
    km = {'titulo': 'Título', 'resumen': 'Resumen - Aclaracion', 'tipodemedio': 'Tipo de Medio'}
    row = {'Título': 'Titulares', 'CuerpoEs': TITULARES, 'Resumen - Aclaracion': TITULARES,
           'Tipo de Medio': 'Televisión'}
    ctx, meta = az.contexto_por_segmentos(row, km, DET)
    assert texto_sin_titulo(ctx, 'Titulares') == REINA
    # Ese punto es el cuerpo con el que se compara, agrupa y valora la nota.
    assert az._texto_fila(row, km) == REINA


def test_lista_dentro_de_una_noticia_no_es_compilacion():
    nota = ('La Alcaldía de Bogotá anunció tres medidas para el puente festivo: 1. Pico y placa '
            'regional en las salidas. 2. Más agentes de tránsito en los peajes. 3. Cierre de la '
            'carrera Séptima el domingo.')
    assert cc.partir_compilacion(nota, 'Medidas para el puente festivo') == []
    assert len(cc.partir_compilacion(TITULARES, 'Titulares')) == 6
    # Un titular de compilación con párrafos sin numerar también se parte.
    sin_num = '\n\n'.join(x.split('. ', 1)[1] for x in TITULARES.split('\n\n'))
    assert len(cc.partir_compilacion(sin_num, 'Titulares')) == 6
    assert cc.partir_compilacion(sin_num, 'La reina de Dinamarca visitó Bogotá') == []
