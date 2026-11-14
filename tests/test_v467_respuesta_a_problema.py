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
