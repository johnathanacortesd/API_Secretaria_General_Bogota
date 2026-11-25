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
