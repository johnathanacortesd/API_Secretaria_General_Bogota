# -*- coding: utf-8 -*-
"""2026-11-14 (pedido del usuario): Contexto analizado por segmentos del
CuerpoEs y tono «respuesta» ($0, sin red).

- El Contexto analizado reúne TODOS los segmentos del cuerpo donde aparecen
  la Secretaría General, la Alcaldía, el alcalde (por nombre o por cargo),
  los voceros y las secretarías y entidades adscritas; no cuentan candidatos
  a la Alcaldía, homónimos ni entidades de otra ciudad.
- Que la nota nombre al alcalde no la hace Positiva: «Galán reconoce
  afectaciones al cronograma del metro por obras en la estación 16 y
  traslado de redes» es Neutro.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_agent_sdk import ResultMessage  # noqa: E402
from openpyxl import Workbook  # noqa: E402

import analyzer_tono_tema as az  # noqa: E402
import contexto_cliente as cc  # noqa: E402
import motor_haiku as mh  # noqa: E402
import pipeline  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(RAIZ, 'clientes', 'secretaria_general_de_la_alcaldia_de_bogota.json'),
          encoding='utf-8') as _f:
    PERFIL = json.load(_f)
B, A = PERFIL['brand'], PERFIL['aliases']
V = az.expandir_voceros(PERFIL['voceros'])
KM = {'titulo': 'Título'}

TIT_METRO = ('Galán reconoce afectaciones al cronograma del metro por obras en la estación 16 '
             'y traslado de redes')
METRO = (
    'La primera línea del metro de Bogotá completó esta semana 72 % de avance, según el más '
    'reciente informe de la interventoría. Sin embargo, el frente de la estación 16, en la avenida '
    'Caracas con calle 72, registra demoras por el traslado de redes de acueducto y gas.\n'
    'El concesionario advirtió que las obras en ese punto llevan cuatro meses de atraso. Vecinos '
    'del sector se quejan por el ruido y los cierres viales. Los comerciantes aseguran que sus '
    'ventas cayeron 40 %.\n'
    'Frente a esto, el alcalde Carlos Fernando Galán reconoció que el cronograma presenta '
    'afectaciones. "Hay un impacto en la estación 16 y en el traslado de redes, no lo vamos a '
    'negar", dijo. El mandatario agregó que la meta de iniciar operación en marzo de 2028 se '
    'mantiene.\n'
    'El concejal Juan Daniel Oviedo cuestionó a la Alcaldía de Bogotá por no haber informado antes '
    'sobre los retrasos. En el Concejo se citará a debate de control político.\n'
    'Por su parte, el gerente de la Empresa Metro explicó que se habilitaron turnos nocturnos '
    'para recuperar tiempos. La Secretaría de Movilidad anunció un plan de manejo de tráfico.\n'
    'Juan Manuel Galán, director del Nuevo Liberalismo, no se pronunció. El candidato a la '
    'Alcaldía de Bogotá Fulano de Tal dijo que revisará el contrato. La Secretaría de Salud de '
    'Cundinamarca no tiene relación con el caso.\n'
    'El clima en la capital seguirá lluvioso durante el fin de semana, informó el Ideam.')


def _det(distrito=True):
    return az.detector_cliente(B, A, V, distrito=distrito)


# ─── Contexto analizado por segmentos ─────────────────────────────────────

def test_contexto_reune_todos_los_segmentos_del_cliente():
    ctx, meta = az.contexto_por_segmentos({'Título': TIT_METRO, 'CuerpoEs': METRO}, KM, _det())
    assert ctx.startswith(TIT_METRO)                       # el título nombra al alcalde
    for trozo in ('el alcalde Carlos Fernando Galán reconoció que el cronograma presenta afectaciones',
                  'no lo vamos a negar',                   # la cita que sigue a la mención
                  'El mandatario agregó',                  # continúa el mismo sujeto
                  'cuestionó a la Alcaldía de Bogotá',      # la crítica de un tercero
                  'el gerente de la Empresa Metro explicó',  # entidad adscrita
                  'La Secretaría de Movilidad anunció'):
        assert trozo in ctx, trozo
    # La oración anterior a «Frente a esto…» entra para que se entienda.
    assert 'Los comerciantes aseguran' in ctx
    assert cc.SEPARADOR in ctx                             # segmentos no contiguos
    assert len(ctx) >= az.MIN_CONTEXTO_CARACTERES
    assert meta['oraciones_con_mencion'] >= 5
    assert {'vocero', 'marca', 'adscrita'} <= set(meta['categorias'])
    assert meta['mencion_cliente'] is True


def test_menciones_ajenas_no_entran_al_contexto():
    ctx, _ = az.contexto_por_segmentos({'Título': TIT_METRO, 'CuerpoEs': METRO}, KM, _det())
    for ajeno in ('Juan Manuel Galán', 'candidato a la Alcaldía', 'Cundinamarca', 'Ideam'):
        assert ajeno not in ctx, ajeno
    d = _det()
    assert not d.menciona('Juan Manuel Galán, director del Nuevo Liberalismo, no se pronunció.')
    assert not d.menciona('El candidato a la Alcaldía de Bogotá dijo que revisará el contrato.')
    assert not d.menciona('La Secretaría de Salud de Cundinamarca entregó vacunas.')
    assert not d.menciona('La Alcaldía de Soacha anunció un nuevo colegio.')
    assert not d.menciona('La avenida Luis Carlos Galán amaneció con trancón.')


def test_cargo_y_entidades_adscritas_cuentan_como_cliente():
    d = _det()
    for texto in ('El mandatario distrital visitó la obra.',
                  'El alcalde mayor entregó el parque.',
                  'La administración distrital destinó recursos.',
                  'El secretario de Seguridad presentó el balance.',
                  'La Secretaría Distrital de Integración Social abrió cupos.',
                  'El IDU reparó la malla vial.', 'TransMilenio amplió su flota.',
                  'La UAESP recogió escombros.', 'El Distrito abrió la convocatoria.'):
        assert d.menciona(texto), texto
    # Sin el perfil del Distrito solo cuentan marca, alias y voceros.
    assert not _det(distrito=False).menciona('El IDU reparó la malla vial.')
    assert _det(distrito=False).menciona('La Alcaldía de Bogotá reparó la malla vial.')


def test_mencion_solo_en_entidad_adscrita_ya_no_queda_sin_contexto():
    cuerpo = ('La Policía Metropolitana capturó a seis personas señaladas de integrar la banda Los '
              'Rápidos. Los detenidos fueron enviados a la cárcel por un juez. Según cifras de la '
              'Secretaría de Seguridad, el hurto de celulares bajó 8 % este año. Las autoridades '
              'invitan a denunciar por la línea 123 cualquier caso que se presente en la localidad.')
    ctx, meta = az.contexto_por_segmentos(
        {'Título': 'Capturan a banda dedicada al hurto de celulares en Kennedy', 'CuerpoEs': cuerpo},
        KM, _det())
    assert 'Secretaría de Seguridad' in ctx and meta['categorias'] == ['adscrita']
    assert meta['menciones'] == ['secretaria de seguridad (entidad adscrita)']
    assert not ctx.startswith('Capturan a banda')          # el título no nombra al cliente


def test_sin_mencion_real_usa_la_entrada_y_lo_marca():
    cuerpo = ('El expresidente Álvaro Uribe dijo que Gustavo Petro podría ser candidato a la '
              'Alcaldía de Bogotá en 2027. Cuando Petro era alcalde, recordó, hubo crisis de '
              'basuras. El Centro Democrático definirá su candidato en marzo.')
    ctx, meta = az.contexto_por_segmentos(
        {'Título': '¿Uribe ve a Petro candidato a la Alcaldía de Bogotá?', 'CuerpoEs': cuerpo},
        KM, _det())
    assert meta['mencion_cliente'] is False and meta['menciones'] == []
    assert ctx.startswith('El expresidente Álvaro Uribe')


def test_transcript_sin_puntuacion_se_acota_a_la_mencion():
    cuerpo = ('buenos dias oyentes hoy hablamos de movilidad ' * 40
              + 'y el alcalde galan dijo que el pico y placa no cambia por ahora '
              + 'seguimos con mas noticias de la manana ' * 40)
    ctx, _ = az.contexto_por_segmentos(
        {'Título': 'Noticiero de la mañana', 'CuerpoEs': cuerpo, 'Tipo de Medio': 'Radio'}, KM, _det())
    assert 'el alcalde galan dijo que el pico y placa no cambia' in ctx
    assert len(ctx) < 900


def test_oraciones_no_se_parten_en_abreviaturas_ni_decimales():
    o = cc.partir_oraciones('La obra costó 12.500 millones. Abre a las 5:30 a. m. del lunes. '
                            'El Dr. Pérez la entregó.')
    assert o == ['La obra costó 12.500 millones.', 'Abre a las 5:30 a. m. del lunes.',
                 'El Dr. Pérez la entregó.']


# ─── Tono: responder por algo adverso es Neutro ───────────────────────────

CASOS_TONO = [
    (TIT_METRO, 'El alcalde Carlos Fernando Galán reconoció que el cronograma de la primera línea '
     'del metro de Bogotá presenta afectaciones por las obras de la estación 16 y el traslado de '
     'redes. "Hay un impacto, no lo vamos a negar", dijo Galán.', 'Neutro'),
    ('Alcalde Galán admite retrasos en la entrega de colegios',
     'El alcalde Carlos Fernando Galán admitió que hay retrasos en la entrega de tres colegios '
     'por problemas con el contratista.', 'Neutro'),
    ('Galán responde a críticas por aumento de hurtos en Bogotá',
     'El alcalde Galán respondió a las críticas del Concejo por el aumento de hurtos. Dijo que '
     'la Alcaldía de Bogotá trabaja con la Policía.', 'Neutro'),
    ('Secretaría de Movilidad explica trancones por obras de la avenida 68',
     'La Secretaría de Movilidad explicó que los trancones se deben a las obras de la avenida 68.',
     'Neutro'),
    ('Alcaldía de Bogotá entregó 300 viviendas en Bosa',
     'La Alcaldía de Bogotá entregó 300 viviendas de interés social a familias de Bosa.', 'Positivo'),
    ('Distrito atiende emergencia por lluvias en Usme',
     'La Alcaldía de Bogotá atendió a 120 familias afectadas por las lluvias en Usme y entregó '
     'ayudas humanitarias.', 'Positivo'),
    ('Galán anuncia que el metro de Bogotá llega al 70 % de avance',
     'El alcalde Carlos Fernando Galán anunció que las obras del metro de Bogotá alcanzaron el '
     '70 % de avance y destacó el cumplimiento del cronograma.', 'Positivo'),
]


def _reglas(titulo, ctx, tono_modelo):
    """Las reglas de tono del flujo, en su orden, sobre un grupo."""
    g = [{'grupo': 1, 'titulo': titulo, 'contexto': ctx, 'contexto_marca': ctx, 'texto': ctx,
          'idxs': [0]}]
    e = {1: {'tono': tono_modelo, 'sub_tema': 'x', 'tipo': 'Institucional', 'genero': 'Noticia'}}
    az.aplicar_guarda_tono(g, e, B, A, voceros=V)
    az.aplicar_regla_critica_con_respuesta(g, e, B, A, voceros=V)
    az.aplicar_regla_negativo_sin_blanco(g, e, B, A, voceros=V)
    az.aplicar_guarda_positiva(g, e, B, A, voceros=V, solo_gestion=True)
    pegajosos = az.aplicar_regla_positivo_incidental(g, e, B, A, voceros=V, solo_gestion=True)
    az.aplicar_regla_respuesta_a_problema(g, e, B, A, voceros=V, det=_det())
    pegajosos += az.aplicar_regla_protocolaria(g, e, B, A, voceros=V)
    for gid in pegajosos:
        e[gid].setdefault('flags', {})['neutro_pegajoso'] = True
    az.aplicar_regla_secretarias_distritales(g, e, B, A, voceros=V)
    az.aplicar_regla_decreto(g, e)
    az.aplicar_regla_distrito(g, e, B, A, voceros=V)
    return e[1]['tono']


def test_responder_por_algo_adverso_es_neutro_diga_lo_que_diga_el_modelo():
    for titulo, ctx, esperado in CASOS_TONO:
        for tono_modelo in ('Neutro', 'Positivo'):
            assert _reglas(titulo, ctx, tono_modelo) == esperado, (titulo, tono_modelo)
    # El alcalde reconoce el problema y nadie lo señala: tampoco es Negativo.
    assert _reglas(*CASOS_TONO[0][:2], 'Negativo') == 'Neutro'


def test_critica_dirigida_de_terceros_sigue_negativa():
    titulo = 'Concejales denuncian sobrecostos en contrato de la Alcaldía de Bogotá'
    ctx = 'Concejales denunciaron a la Alcaldía de Bogotá por sobrecostos en un contrato.'
    assert _reglas(titulo, ctx, 'Negativo') == 'Negativo'
    assert _reglas(titulo, ctx, 'Positivo') == 'Neutro'    # un titular adverso nunca es Positivo


def test_titulo_adverso_sin_gestion():
    si = [TIT_METRO, 'Obras del metro completan cuatro meses de atraso',
          'Alcalde Galán admite retrasos en la entrega de colegios',
          'Crece la polémica por el contrato de aseo']
    no = ['Alcaldía de Bogotá entregó 300 viviendas en Bosa', 'Distrito atiende emergencia en Usme',
          'Bogotá supera la crisis de basuras', 'Yamid Amat continúa en estado crítico en una UCI',
          'Alcaldía reconoce a los mejores docentes del año']
    for t in si:
        assert az.titulo_adverso_sin_gestion(t), t
    for t in no:
        assert not az.titulo_adverso_sin_gestion(t), t


def test_donde_no_es_un_hecho_bueno_del_distrito():
    assert not az._hecho_bueno_distrito(az.nz('La calle donde ocurrió el choque sigue cerrada'))
    assert az._hecho_bueno_distrito(az.nz('La Alcaldía donó 200 computadores'))


# ─── Motor Haiku: rol «respuesta», hecho y menciones ──────────────────────

def test_rol_respuesta_es_neutro_y_esta_en_los_prompts():
    assert mh.ROLES['respuesta'] == 'Neutro'
    for p in (mh.SYSTEM_PROMPT, mh.PROMPT_AUDITOR_TONO, mh.PROMPT_REVISOR):
        assert 'respuesta' in p and 'no la hace Positiva' in p
    assert 'reconoce afectaciones al cronograma del metro' in mh.SYSTEM_PROMPT
    assert '"rol":"gestion|logro|critica|afectacion|respuesta|equilibrada|referencial"' in mh.SYSTEM_PROMPT


def _txt(r):
    return r['content'][0]['text']


def test_leer_noticias_trae_hecho_y_menciones_y_guarda_rol_respuesta():
    ctx, meta = az.contexto_por_segmentos({'Título': TIT_METRO, 'CuerpoEs': METRO}, KM, _det())
    its = [{'id': '1', 'titulo': TIT_METRO, 'contexto': ctx, 'hecho': meta['lead'],
            'menciones': meta['menciones'], 'mencion_cliente': True},
           {'id': '2', 'titulo': 'Capturan a banda en Kennedy',
            'contexto': 'Según cifras de la Secretaría de Seguridad, el hurto bajó 8 %.',
            'hecho': 'La Policía capturó a seis personas de la banda Los Rápidos.',
            'menciones': ['secretaria de seguridad (entidad adscrita)'], 'mencion_cliente': True},
           {'id': '3', 'titulo': '¿Uribe ve a Petro candidato a la Alcaldía de Bogotá?',
            'contexto': 'Uribe dijo que Petro podría ser candidato a la Alcaldía de Bogotá.',
            'mencion_cliente': False}]
    mh.preparar_estado(its, False, terminos=mh.terminos_cliente(B, A, V))
    pag = {n['id']: n for n in json.loads(_txt(asyncio.run(mh._leer_noticias({'desde': 0}))))['noticias']}
    assert 'hecho' not in pag['1']                         # la entrada ya está en el contexto
    assert pag['2']['hecho'].startswith('La Policía capturó')
    assert pag['2']['menciones_cliente'] == ['secretaria de seguridad (entidad adscrita)']
    assert 'sin_mencion_literal' not in pag['2']           # la entidad adscrita cuenta
    assert pag['3'].get('sin_mencion_literal') is True     # el cargo como referencia no cuenta
    r = asyncio.run(mh._guardar_clasificacion({'filas_json': json.dumps([
        {'id': '1', 'subtema': 'Retrasos del metro por traslado de redes', 'rol': 'respuesta',
         'tono': 'Positivo'}])}))
    assert r.get('is_error') and "rol 'respuesta' corresponde a tono Neutro" in _txt(r)
    r = asyncio.run(mh._guardar_clasificacion({'filas_json': json.dumps([
        {'id': '1', 'subtema': 'Retrasos del metro por traslado de redes', 'rol': 'respuesta',
         'tono': 'Neutro'}])}))
    assert not r.get('is_error') and mh._ESTADO['res']['1']['rol'] == 'respuesta'


def test_auditor_revisa_los_positivos_con_titular_adverso():
    its = [{'id': '1', 'titulo': TIT_METRO, 'contexto': 'El alcalde Galán reconoció afectaciones.'},
           {'id': '2', 'titulo': 'Alcaldía de Bogotá entregó 300 viviendas en Bosa',
            'contexto': 'La Alcaldía de Bogotá entregó 300 viviendas.'}]
    mh.preparar_estado(its, False, terminos=mh.terminos_cliente(B, A, V))
    asyncio.run(mh._guardar_clasificacion({'filas_json': json.dumps([
        {'id': '1', 'subtema': 'Retrasos del metro por traslado de redes', 'rol': 'gestion',
         'tono': 'Positivo'},
        {'id': '2', 'subtema': 'Entrega de viviendas en Bosa', 'rol': 'gestion', 'tono': 'Positivo'}])}))
    cands = {c['id']: c['motivos'] for c in mh.candidatos_tono()}
    assert set(cands) == {'1'} and 'hecho adverso' in cands['1'][0]


# ─── De punta a punta: el dossier por el pipeline con un modelo que se equivoca ──

def _dossier():
    wb = Workbook()
    ws = wb.active
    ws.append(['ID Noticia', 'Título', 'Resumen - Aclaracion', 'Medio', 'Fecha', 'CuerpoEs'])
    ws.append(['201', TIT_METRO, 'El alcalde reconoció afectaciones.', 'Prensa A', '2026-11-12', METRO])
    ws.append(['202', 'Alcalde Galán reconoce afectaciones en el cronograma del metro por la estación 16',
               'El alcalde reconoció afectaciones.', 'Prensa B', '2026-11-12',
               METRO.replace('completó esta semana', 'alcanzó esta semana')])
    ws.append(['203', 'Alcaldía de Bogotá entregó 300 viviendas en Bosa',
               'Entrega de viviendas.', 'Radio C', '2026-11-12',
               'La Alcaldía de Bogotá entregó 300 viviendas de interés social a familias de Bosa. '
               'El alcalde Carlos Fernando Galán destacó la inversión de 45.000 millones de pesos.'])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _agente_que_todo_lo_ve_positivo(vistas):
    subs = {'metro': 'Retrasos del metro por traslado de redes', 'viviendas': 'Entrega de viviendas en Bosa'}

    async def q(prompt, options):
        if 'auditor-tono' in (options.system_prompt or ''):
            yield ResultMessage(subtype='success', duration_ms=1, duration_api_ms=1, is_error=False,
                                num_turns=1, session_id='f', total_cost_usd=0.0,
                                result='{"resultados":[]}')
            return
        if 'mcp__medios__leer_noticias' not in (options.allowed_tools or []):
            yield ResultMessage(subtype='success', duration_ms=1, duration_api_ms=1, is_error=False,
                                num_turns=1, session_id='f', total_cost_usd=0.0, result='{}')
            return
        pag = json.loads(_txt(await mh._leer_noticias({'desde': 0})))
        filas = []
        for n in pag['noticias']:
            vistas[n['id']] = n
            if 'igual_a' in n:
                continue
            clave = 'viviendas' if 'viviendas' in n['titulo_solo_para_agrupar'] else 'metro'
            filas.append({'id': n['id'], 'subtema': subs[clave], 'rol': 'gestion', 'tono': 'Positivo',
                          'tipo': 'Institucional', 'genero': 'Noticia'})
        await mh._guardar_clasificacion({'filas_json': json.dumps(filas)})
        yield ResultMessage(subtype='success', duration_ms=1, duration_api_ms=1, is_error=False,
                            num_turns=2, session_id='f', total_cost_usd=0.01, result='ok')
    return q


def test_dossier_completo_galan_reconoce_afectaciones_sale_neutro(tmp_path):
    vistas = {}
    real = mh.clasificar_con_haiku
    q = _agente_que_todo_lo_ve_positivo(vistas)
    cfg = {'enabled': True, 'brand': B, 'aliases': A, 'voceros': PERFIL['voceros'],
           'criterio': PERFIL['criterio'], 'criterio_texto': PERFIL['criterio_custom'],
           'guia_subtema': PERFIL['guia_subtema'], 'incluir_tema': False, 'motor': 'haiku',
           'api_key': None, 'tone_pkl_bytes': None, 'theme_pkl_bytes': None, 'memoria': False,
           'historial_dir': str(tmp_path),
           'tono_distrito_positivo': True, 'tono_solo_gestion': True, 'agrupacion_estricta': True,
           'tono_neutro_titulo': ['Petro']}
    with patch.object(mh, 'clasificar_con_haiku',
                      side_effect=lambda *a, **k: real(*a, query_fn=q, **k)), \
            patch.object(mh, 'QUERY_FN', q), \
            patch.object(az, 'llamar_llm', side_effect=AssertionError('OpenAI no')):
        res = pipeline.process_dossier(io.BytesIO(_dossier()), {}, {}, ai_config=cfg)
    vista = {f['ID']: f for f in res['vista']}
    # El modelo dijo Positivo en todo; el alcalde reconociendo un problema queda Neutro.
    assert vista['201']['Tono'] == vista['202']['Tono'] == 'Neutro'
    assert vista['203']['Tono'] == 'Positivo'
    # Las dos notas del mismo hecho comparten subtema; la de viviendas conserva el suyo.
    assert vista['201']['Subtema'] == vista['202']['Subtema'] != vista['203']['Subtema']
    # Lo que leyó el modelo: segmentos del cliente y menciones ubicadas.
    metro = next(n for n in vistas.values() if 'contexto' in n and 'reconoci' in n['contexto'])
    assert 'cuestionó a la Alcaldía de Bogotá' in metro['contexto']
    assert any('Carlos Fernando Galán' in m for m in metro['menciones_cliente'])
    seg = res['analisis']['contexto_segmentos']
    assert seg['filas'] == 3 and seg['con_mencion_en_cuerpo'] == 3 and seg['sin_mencion'] == 0
