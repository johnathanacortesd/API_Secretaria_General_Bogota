# -*- coding: utf-8 -*-
"""TIPO y GÉNERO en modo Claude Haiku (flag clasificar_tipo_genero), $0 con query falso."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_openai_stub = types.ModuleType('openai')
_openai_stub.OpenAI = object
sys.modules.setdefault('openai', _openai_stub)

from claude_agent_sdk import ResultMessage  # noqa: E402

import analyzer_tono_tema as az  # noqa: E402
import motor_haiku as mh  # noqa: E402
import pipeline  # noqa: E402

VISTO: dict = {}


async def fake_query(prompt, options):
    VISTO['options'] = options
    desde = 0
    while desde is not None:
        pag = json.loads((await mh._leer_noticias({'desde': desde}))['content'][0]['text'])
        filas = []
        for n in pag['noticias']:
            VISTO.setdefault('noticias', []).append(n)
            if 'igual_a' in n:
                continue
            filas.append({'id': n['id'], 'subtema': 'Hecho %s' % n['id'], 'tono': 'Neutro',
                          'tipo': 'Programas y proyectos', 'genero': 'Noticia'})
        await mh._guardar_clasificacion({'filas_json': json.dumps(filas)})
        desde = pag['siguiente']
    yield ResultMessage(subtype='success', duration_ms=1, duration_api_ms=1, is_error=False,
                        num_turns=3, session_id='f', total_cost_usd=0.0)


def _items():
    return [
        {'id': '1', 'titulo': 'Alcaldía entrega colegio', 'contexto': 'c1', 'seccion': 'Bogotá',
         'tipo_medio': 'Internet', 'medio': 'El Tiempo', 'url_opinion': True},
        {'id': '2', 'titulo': 'Alcaldía entrega colegio', 'contexto': 'c2'},
        {'id': '3', 'titulo': 'Otra', 'contexto': 'c3'},
        {'id': '4', 'titulo': 'copia', 'contexto': '-', 'duplicado_de': '3'},
    ]


class TestMotorTipoGenero(unittest.TestCase):
    def setUp(self):
        VISTO.clear()

    def test_filas_validas_y_duplicados_heredan(self):
        r = mh.clasificar_con_haiku(_items(), 'Alcaldía', query_fn=fake_query,
                                    clasificar_tipo_genero=True)
        et = r['etiquetas']
        self.assertEqual(set(et), {'1', '2', '3', '4'})
        for v in et.values():
            self.assertIn(v['tipo'], mh.TIPOS)
            self.assertIn(v['genero'], mh.GENEROS)
        self.assertEqual(et['2'], et['1'])
        self.assertEqual(et['4'], et['3'])
        self.assertEqual(r['faltan'], 0)
        n1 = next(n for n in VISTO['noticias'] if n['id'] == '1')
        self.assertEqual(n1['seccion_programa'], 'Bogotá')
        self.assertEqual(n1['medio'], 'El Tiempo')
        self.assertTrue(n1['url_contiene_opinion'])
        self.assertIn('<tipo_y_genero>', VISTO['options'].system_prompt)
        self.assertIn('Programas y proyectos: la gestión de la entidad', VISTO['options'].system_prompt)

    def test_sin_flag_no_pide_tipo_genero(self):
        r = mh.clasificar_con_haiku(_items(), 'Alcaldía', query_fn=fake_query)
        self.assertNotIn('tipo', r['etiquetas']['1'])
        self.assertNotIn('seccion_programa', VISTO['noticias'][0])
        self.assertNotIn('<tipo_y_genero>', VISTO['options'].system_prompt)

    def test_categorias_invalidas_rechazadas(self):
        mh.preparar_estado(_items(), incluir_tema=False, con_tipo_genero=True)
        g = lambda f: asyncio.run(mh._guardar_clasificacion({'filas_json': json.dumps([f])}))
        base = {'id': '1', 'subtema': 's', 'tono': 'Neutro'}
        self.assertTrue(g(dict(base, tipo='Proyectos', genero='Noticia')).get('is_error'))
        self.assertTrue(g(dict(base, tipo='institucional', genero='Noticia')).get('is_error'))
        self.assertTrue(g(dict(base, tipo='Ranking', genero='Columna')).get('is_error'))
        self.assertTrue(g(dict(base, tipo='Ranking', genero='Opinion')).get('is_error'))
        ok = g(dict(base, tipo='Ranking', genero='Opinión'))
        self.assertFalse(ok.get('is_error'))
        # sin tipo/genero la fila sigue faltando
        self.assertIn('Faltan por clasificar: 1', g({'id': '3', 'subtema': 's', 'tono': 'Neutro'})['content'][0]['text'])
        # una corrección sin tipo/genero los conserva
        g({'id': '1', 'subtema': 'otro', 'tono': 'Positivo'})
        self.assertEqual(mh._ESTADO['res']['1']['tipo'], 'Ranking')


class TestEnrichHaikuTipoGenero(unittest.TestCase):
    def test_enrich_llena_tipo_genero_canonico(self):
        real = mh.clasificar_con_haiku
        rows = [{'Título': 'La marca entrega un colegio en Bosa',
                 'CuerpoEs': 'La marca entrega un colegio nuevo a la comunidad de Bosa.'},
                {'Título': 'Concejo debate el presupuesto distrital',
                 'CuerpoEs': 'El Concejo debatió el presupuesto y la marca presentó cifras.'}]
        with patch.object(mh, 'clasificar_con_haiku',
                          side_effect=lambda *a, **k: real(*a, query_fn=fake_query, **k)), \
             patch.object(az, 'etiquetar_grupos', side_effect=AssertionError('OpenAI no')), \
             patch.object(az, 'llamar_llm', side_effect=AssertionError('OpenAI no')):
            out = az.enrich_rows_with_ai(
                rows, {'titulo': 'Título'}, brand='Marca', aliases=[], api_key='k',
                extra={'motor': 'haiku', 'incluir_tema': False, 'voceros': [],
                       'clasificar_tipo_genero': True},
                progress_callback=lambda p, m: None)
        for r in out:
            self.assertIn(r['TIPO'], az.TIPOS_VALIDOS)
            self.assertIn(r['GÉNERO'], az.GENEROS_VALIDOS)
        # literal publicado de siempre (mismo que OpenAI)
        self.assertEqual(out[0]['TIPO'], 'Proyectos y programas')


def _fila(url='', sec='', genero='Noticia', tipo='Institucional', autor=''):
    return {'Tipo de Medio': 'Internet', 'URL Nota': url, 'Sección - Programa': sec,
            'GÉNERO': genero, 'TIPO': tipo, 'Autor - Conductor': autor}


class TestReglaOpinionHaiku(unittest.TestCase):
    def test_url_opinion_gana_al_modelo(self):
        r = _fila('https://www.eltiempo.com/opinion/columnistas/x', genero='Reportaje')
        pipeline.aplicar_opinion_haiku([r], 'Secretaría General')
        self.assertEqual(r['GÉNERO'], 'Opinión')
        self.assertEqual(r['TIPO'], 'Opinión de terceros')

    def test_laopinion_y_desopinion_no_son_opinion(self):
        for url in ('https://www.laopinion.com/bogota/nota', 'https://laopinion.co/x',
                    'https://desopinion.com/nota'):
            r = _fila(url)
            pipeline.aplicar_opinion_haiku([r])
            self.assertEqual(r['GÉNERO'], 'Noticia', url)
            r2 = _fila(url)
            pipeline.aplicar_genero_por_url([r2])
            self.assertEqual(r2['GÉNERO'], 'Noticia', url)

    def test_seccion_columnistas_y_opinion(self):
        for sec in ('Columnistas', 'Opinión', 'Columna'):
            r = _fila(sec=sec, genero='Entrevista')
            pipeline.aplicar_opinion_haiku([r])
            self.assertEqual(r['GÉNERO'], 'Opinión', sec)
        r = _fila(sec='La Opinión')
        pipeline.aplicar_opinion_haiku([r])
        self.assertEqual(r['GÉNERO'], 'Noticia')

    def test_autor_de_la_entidad_y_ranking_conservan_tipo(self):
        r = _fila(sec='Opinión', autor='Secretaría General')
        pipeline.aplicar_opinion_haiku([r], 'Secretaría General')
        self.assertEqual((r['GÉNERO'], r['TIPO']), ('Opinión', 'Institucional'))
        r = _fila(sec='Opinión', tipo='Ranking')
        pipeline.aplicar_opinion_haiku([r])
        self.assertEqual(r['TIPO'], 'Ranking')

    def test_duplicadas_no_se_tocan(self):
        r = _fila('https://x.com/opinion/a', genero='-', tipo='-')
        r['is_duplicate'] = True
        pipeline.aplicar_opinion_haiku([r])
        self.assertEqual((r['GÉNERO'], r['TIPO']), ('-', '-'))

    def test_seccion_columnistas_en_rescate_comun(self):
        e = {1: {'genero': 'Noticia'}}
        az.aplicar_genero_por_seccion([{'Sección - Programa': 'Columnistas'}], {0: 1}, e, {})
        self.assertEqual(e[1]['genero'], 'Opinión')


if __name__ == '__main__':
    unittest.main()
