"""Clausifier 2026-11-08 (Secretaría): Reportaje con evidencia fuerte, TIPO
Institucional por anuncio del vocero, alias Alcaldía Mayor de Bogotá."""
import json
import os

import analyzer_tono_tema as a
import motor_haiku as mh
import pipeline as p

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERFIL = json.load(open(os.path.join(REPO, 'clientes', 'secretaria_general_de_la_alcaldia_de_bogota.json'),
                        encoding='utf-8'))


def test_alias_alcaldia_mayor():
    assert 'Alcaldía Mayor de Bogotá' in PERFIL['aliases']


def test_url_reportaje_solo_por_segmento():
    assert p._url_es_reportaje('https://www.elespectador.com/especiales/archivo-de-bogota')
    assert p._url_es_reportaje('https://x.com/investigacion/contratos-2026')
    assert not p._url_es_reportaje('https://x.com/judicial/fiscalia-abre-investigacion-contra-hacker')
    assert not p._url_es_reportaje('https://x.com/paz/jurisdiccion-especial-para-la-paz')


def test_seccion_reportaje_palabra_completa():
    for s in ('Especiales', 'Investigación', 'Crónicas', 'Reportajes'):
        assert a.seccion_es_reportaje(s), s
    for s in ('Judicial e investigación', 'Educación especial', 'Bogotá', 'Nación'):
        assert not a.seccion_es_reportaje(s), s


def test_guardia_reportaje_baja_sin_evidencia():
    rows = [
        {'GÉNERO': 'Reportaje', 'Tipo de Medio': 'Internet', 'Sección - Programa': 'Judicial',
         'URL Nota': 'https://x.com/judicial/fiscalia-abre-investigacion-contra-hacker',
         'CuerpoEs': 'La Fiscalía abrió una investigación.'},
        {'GÉNERO': 'Reportaje', 'Tipo de Medio': 'Internet', 'Sección - Programa': 'Especiales',
         'URL Nota': 'https://x.com/especiales/archivo', 'CuerpoEs': 'Crónica.'},
        {'GÉNERO': 'Reportaje', 'Tipo de Medio': 'Internet', 'Sección - Programa': 'Bogotá',
         'URL Nota': 'https://x.com/bogota/nota', 'CuerpoEs': 'x' * 5000},
    ]
    assert p.aplicar_guardia_reportaje(rows) == 1
    assert [r['GÉNERO'] for r in rows] == ['Noticia', 'Reportaje', 'Reportaje']


def test_tipo_institucional_por_anuncio():
    gs = [{'grupo': 1, 'titulo': 'El alcalde Carlos Fernando Galán anunció cambios en el gabinete',
           'contexto': 'El alcalde Carlos Fernando Galán anunció cambios en su equipo de gobierno.'},
          {'grupo': 2, 'titulo': 'Galán anunció nueva jornada de vacunación',
           'contexto': 'La jornada será el sábado.'},
          {'grupo': 3, 'titulo': 'Concejo debate movilidad', 'contexto': 'Debate en el Concejo.'},
          {'grupo': 4, 'titulo': 'El alcalde Galán dijo mentiras', 'contexto': 'Columna.'}]
    e = {1: {'tipo': 'Información general'}, 2: {'tipo': 'Proyectos y programas'},
         3: {'tipo': 'Información general'}, 4: {'tipo': 'Opinión de terceros'}}
    out = a.aplicar_tipo_institucional_anuncio(gs, e, PERFIL['brand'], PERFIL['aliases'], PERFIL['voceros'])
    assert out == [1]
    assert e[2]['tipo'] == 'Proyectos y programas' and e[4]['tipo'] == 'Opinión de terceros'


def test_prompt_tipo_genero():
    sp = mh.system_prompt(True)
    assert 'Carlos Fernando Galán anunció' in sp and 'Ante la duda, Noticia' in sp
    assert 'Analiza la columna Contexto analizado completa' in sp


def test_alcaldia_mayor_sujeto_de_gestion():
    actores = [a.nz(x) for x in [PERFIL['brand']] + PERFIL['aliases'] + PERFIL['voceros']]
    assert a._marca_sujeto_de_gestion(
        'La Alcaldía Mayor de Bogotá recuperó 20 hectáreas de espacio público en Suba.', actores)
