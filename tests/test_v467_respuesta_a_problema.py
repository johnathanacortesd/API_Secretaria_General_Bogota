# -*- coding: utf-8 -*-
"""2026-11-14: reconocer o responder ante un problema es Neutro, no Positivo;
y el Contexto analizado incluye la continuación de lo que dijo el vocero."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analyzer_tono_tema as a  # noqa: E402

MARCA, ALIAS, VOC = 'Secretaría General', ['Alcaldía de Bogotá'], ['Galán', 'el alcalde']


def _tono(titulo, ctx=''):
    g = [{'grupo': 1, 'titulo': titulo, 'contexto': ctx}]
    e = {1: {'tono': 'Positivo'}}
    a.aplicar_regla_respuesta_a_problema(g, e, MARCA, ALIAS, VOC)
    return e[1]['tono']


def test_galan_reconoce_afectaciones_es_neutro():
    assert _tono('Galán reconoce afectaciones al cronograma del metro por obras en la '
                 'estación 16 y traslado de redes') == 'Neutro'


def test_alcalde_responde_a_criticas_es_neutro():
    assert _tono('Alcalde responde a críticas por aumento de hurtos') == 'Neutro'


def test_logro_concreto_sigue_positivo():
    assert _tono('Galán inaugura colegio en Usme') == 'Positivo'
    assert _tono('Galán reconoce críticas, pero entrega 300 viviendas') == 'Positivo'


def test_continuacion_del_habla_del_vocero():
    cuerpo = ('El metro avanza. El alcalde Carlos Fernando Galán dijo: "Hay afectaciones." '
              'Hay que trasladar redes. Agregó que se negocia con las empresas. Otro tema.')
    ctx = a._contexto_exacto_marca(cuerpo, 't', 'Alcaldía de Bogotá', [], ['Galán'])
    assert 'trasladar redes' in ctx and 'Agregó que se negocia' in ctx
    assert 'Otro tema' not in ctx and 'El metro avanza' not in ctx


# --- Regresión con el dossier revisado a mano (2026-11-14) -----------------
def _rule(regla, titulo, sub, tono, ctx='', tipo=''):
    g = [{'grupo': 1, 'titulo': titulo, 'contexto': ctx, 'texto': ''}]
    e = {1: {'tono': tono, 'sub_tema': sub, 'tipo': tipo}}
    regla(g, e, MARCA, ALIAS, VOC)
    return e[1]['tono']


def test_subtema_de_problema_baja_todo_el_subtema():
    sub = 'Retrasos en cronograma de la Línea 1'
    for t in ('Cimentación y redes públicas complican la recta final del Metro de Bogotá',
              'Alcalde Galán expone desafíos de la etapa final de la Línea 1 del Metro de Bogotá',
              'Línea 1 del metro de Bogotá alcanza un 84% de avance, pero su entrega enfrenta retrasos',
              'Retrasos y problemas técnicos afectan el cronograma del Metro de Bogotá'):
        assert _rule(a.aplicar_regla_respuesta_a_problema, t, sub, 'Positivo') == 'Neutro', t


def test_entrega_sustantivo_no_es_logro():
    assert _tono('Primera línea del Metro sufrirá retrasos en sus fechas de entrega: Galán lo reconoce') == 'Neutro'


def test_recopilaciones_son_neutras():
    assert _rule(a.aplicar_regla_respuesta_a_problema, 'Noticias del 14 de noviembre',
                 'Recopilación de noticias misceláneas diarias', 'Positivo') == 'Neutro'


def test_cofinanciacion_nacional_para_el_metro_es_positiva():
    ctx = ('El Gobierno Nacional cofinanciará el 50 % de los estudios de la línea 4. '
           'El alcalde de Bogotá, Carlos Fernando Galán, anunció la recta final de la línea 1.')
    assert _rule(a.aplicar_regla_aporte_al_distrito,
                 'Gobierno Nacional cofinanciará el 50 % de los estudios de la Línea 4 del Metro de Bogotá',
                 'Cofinanciación de estudios de la Línea 4', 'Neutro', ctx, 'Institucional') == 'Positivo'


def test_cofinanciacion_sin_la_alcaldia_o_en_opinion_no_sube():
    t = 'Gobierno cofinanciará estudios del Metro de Bogotá'
    assert _rule(a.aplicar_regla_aporte_al_distrito, t, 'x', 'Neutro', 'El Gobierno aportará recursos.') == 'Neutro'
    assert _rule(a.aplicar_regla_aporte_al_distrito, t, 'x', 'Neutro', 'El alcalde Galán.',
                 'Opinión de terceros') == 'Neutro'


def test_opinion_critica_contra_el_alcalde_sigue_negativa():
    texto = ('Alcaldes del calibre de Carlos Fernando Galán se la pasan buscando la forma de '
             'sacarnos más dinero como única solución a la corrupción y al despilfarro.')
    g = [{'grupo': 1, 'titulo': '¿Otra decepción?', 'contexto': texto, 'texto': texto}]
    e = {1: {'tono': 'Negativo', 'tipo': 'Opinión de terceros'}}
    a.aplicar_guarda_tono(g, e, MARCA, ALIAS, VOC)
    a.aplicar_regla_negativo_sin_blanco(g, e, MARCA, ALIAS, VOC)
    assert e[1]['tono'] == 'Negativo'


def test_alias_nuevos_en_el_perfil():
    import json
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'clientes',
                     'secretaria_general_de_la_alcaldia_de_bogota.json')
    c = json.load(open(p, encoding='utf-8'))
    assert 'mandatario capitalino' in c['voceros'] and 'Carlos Fernando Galán Pachón' in c['voceros']
    # Medidos contra el dossier revisado: sin efecto neto o con riesgo de otras ciudades.
    for x in ('Administración Distrital', 'Alcaldía Distrital', 'Gobierno Distrital'):
        assert x not in c['aliases']
    for x in ('alcalde mayor', 'alcalde mayor de Bogotá', 'alcalde de Bogotá'):
        assert x not in c['voceros']
    assert 'el mandatario' not in c['voceros']  # solo, también es el Presidente


def test_aporte_retirado_no_sube_a_positivo():
    ctx = 'El alcalde Galán lamentó que el Gobierno retire los recursos.'
    for t in ('Gobierno retira recursos de la Línea 4 del Metro de Bogotá',
              'Gobierno no financiará los estudios del Metro de Bogotá',
              'Gobierno congela aportes al Metro de Bogotá'):
        assert _rule(a.aplicar_regla_aporte_al_distrito, t, 'x', 'Neutro', ctx) == 'Neutro', t
