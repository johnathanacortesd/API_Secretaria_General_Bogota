# -*- coding: utf-8 -*-
"""v1.38: GÉNERO por URL solo con la sección del enlace, no con el slug."""
import pipeline
from analyzer_tono_tema import genero_por_url, seccion_es_opinion, _campos_tipo_genero_haiku

MINUTO30 = ("https://www.minuto30.com/incendio-cerca-de-la-autopista-sur-genero-una-"
            "columna-de-humo-visible-desde-varios-sectores-de-bogota/1730716/")


def _fila(url, genero='Noticia', tipo='Información general', seccion=''):
    return {'URL Nota': url, 'Tipo de Medio': 'Internet', 'GÉNERO': genero, 'TIPO': tipo,
            'Sección - Programa': seccion, 'Autor - Conductor': ''}


def test_slug_con_columna_no_es_opinion():
    assert genero_por_url(MINUTO30) == ''
    assert genero_por_url("https://www.eltiempo.com/bogota/columna-vertebral-del-transporte-1234") == ''
    assert genero_por_url("https://www.pulzo.com/nacion/editorial-planeta-lanza-libro-PP123") == ''


def test_seccion_de_opinion_en_url_si_cuenta():
    assert genero_por_url("https://www.elespectador.com/opinion/columnistas/juan-perez/el-metro/") == 'Opinión'
    assert genero_por_url("https://opinion.eltiempo.com/x/y") == 'Opinión'
    assert genero_por_url("https://www.semana.com/columnistas/articulo/lo-que-no-dice/2025/") == 'Opinión'
    assert genero_por_url("https://www.eltiempo.com/opinion/editorial/el-pais-123") == 'Editorial'
    assert genero_por_url("https://www.laopinion.com/bogota/incendio-en-suba") == ''


def test_seccion_por_palabra_completa():
    assert seccion_es_opinion("Columnistas") and seccion_es_opinion("Opinión")
    assert not seccion_es_opinion("La Opinión") and not seccion_es_opinion("Bogotá")


def test_reglas_del_pipeline_no_suben_el_caso_minuto30():
    rows = [_fila(MINUTO30)]
    assert pipeline.aplicar_opinion_haiku(rows) == 0
    assert rows[0]['GÉNERO'] == 'Noticia' and rows[0]['TIPO'] == 'Información general'
    assert pipeline.aplicar_genero_por_url(rows) == 0 and rows[0]['GÉNERO'] == 'Noticia'
    assert _campos_tipo_genero_haiku(rows, [0], {})['url_opinion'] is False
    col = [_fila("https://www.elespectador.com/opinion/columnistas/juan-perez/el-metro/")]
    assert pipeline.aplicar_opinion_haiku(col) == 1 and col[0]['GÉNERO'] == 'Opinión'


TIT = "Incendio cerca de la Autopista Sur generó una columna de humo visible desde varios sectores de Bogotá"


def test_v139_guardia_baja_opinion_de_columna_de_humo():
    from analyzer_tono_tema import aplicar_guardia_columna_no_opinion
    rows = [dict(_fila(MINUTO30, genero='Opinión', tipo='Opinión de terceros'), **{'Título': TIT}),
            dict(_fila("https://x.com/bogota/nota-123", genero='Opinión'),
                 **{'Título': "Columna vertebral del transporte: la Primera de Mayo"}),
            # columna real: la Sección lo dice
            dict(_fila("https://x.com/bogota/nota-123", genero='Opinión', seccion='Columnistas'),
                 **{'Título': "La columna de humo que nadie quiere ver"}),
            # columna real sin «columna» física
            dict(_fila("https://x.com/a/b", genero='Opinión'), **{'Título': "El metro que no llega"})]
    assert aplicar_guardia_columna_no_opinion(rows) == 2
    assert rows[0]['GÉNERO'] == 'Noticia' and rows[0]['TIPO'] == 'Información general'
    assert rows[1]['GÉNERO'] == 'Noticia'
    assert rows[2]['GÉNERO'] == 'Opinión' and rows[3]['GÉNERO'] == 'Opinión'


def test_v139_huella_memoria_incluye_bloque_tipo_genero():
    import motor_haiku
    assert motor_haiku.system_prompt(True) != motor_haiku.SYSTEM_PROMPT
    assert 'columna de humo' in motor_haiku.system_prompt(True)
