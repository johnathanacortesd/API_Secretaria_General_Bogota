"""v1.48 (caso real 2026-11-25, nota 62149319 de Pulzo): el encabezado fijo
de Pulzo («Bogotá cuenta con un espacio de información muy completo […]
principales noticias de la Administración Distrital») no es una alusión al
cliente ni parte de la noticia. Por él, seis notas distintas de Pulzo
(escombros, Salsa al Parque, ahorro de energía, Alerta Fase 1, concurso
navideño y cortes de luz) se unieron como «la misma nota» y el concurso
'Navidad en palabras e imágenes' quedó con el subtema «Declaratoria alerta
ambiental Fase 1 suroccidente»."""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az
import contexto_cliente as cc

KM = {'titulo': 'Título', 'resumen': 'Resumen - Aclaracion', 'medio': 'Medio', 'idnoticia': 'ID Noticia'}
PULZO = ('Bogotá cuenta con un espacio de información muy completo donde la ciudadanía, residentes '
         'y extranjeros pueden consultar la información que les interesa sobre Bogotá, su historia, '
         'sus localidades, la gestión y principales noticias de la Administración Distrital.')
NAVIDAD = ("Bogotá se prepara para celebrar la creatividad y el talento de niñas, niños y adolescentes "
           "con el lanzamiento del concurso 'Navidad en palabras e imágenes'. La Alcaldía Mayor de "
           "Bogotá, a través de la Secretaría de Cultura y BibloRed, organiza la convocatoria en Santa "
           "Fe, La Candelaria y Usaquén. Cada localidad tendrá seis ganadores que recibirán bonos para "
           "comprar libros.")
ALERTA = ("La Secretaría Distrital de Ambiente mantiene la Alerta Fase 1 por calidad del aire en el "
          "suroccidente de Bogotá, en Kennedy, Puente Aranda y Bosa, por la acumulación de material "
          "particulado. La Alcaldía de Bogotá hizo operativos de control a vehículos de carga.")
SALSA = ("La Alcaldía de Bogotá anunció Salsa al Parque 2026, festival gratuito que reunirá 15 "
         "agrupaciones en el Parque Simón Bolívar el fin de semana, con orquestas nacionales e "
         "internacionales.")


def _f(medio, tit, cuerpo, sub='', **kw):
    return dict({'Medio': medio, 'Título': tit, 'CuerpoEs': cuerpo, 'Resumen - Aclaracion': cuerpo,
                 'Subtema_IA': sub, 'Tono_IA': 'Positivo'}, **kw)


def test_plantilla_conocida_no_es_mencion_ni_contexto():
    det = az.detector_cliente('Secretaría General de la Alcaldía de Bogotá',
                              ['Alcaldía de Bogotá'], ['Carlos Fernando Galán'], distrito=True)
    row = _f('Pulzo.com', "Concurso 'Navidad en palabras e imágenes' impulsa la creatividad",
             PULZO + '\n\n' + NAVIDAD)
    ctx, meta = az.contexto_por_segmentos(row, KM, det)
    assert 'espacio de información muy completo' not in ctx
    assert 'Navidad en palabras' in ctx
    # Solo el encabezado nombra a la «Administración Distrital»: no es una mención.
    solo = _f('Pulzo.com', 'Clima de hoy', PULZO + '\n\nLloverá en la tarde y bajará la temperatura.')
    _ctx, meta = az.contexto_por_segmentos(solo, KM, det)
    assert not meta['oraciones_con_mencion']


def test_plantilla_detectada_en_el_dossier_y_gemelas_no():
    pie = 'Si tienes alguna sugerencia u observación sobre la nota publicada puedes escribir a la redacción del portal.'
    notas = [('portal', NAVIDAD + ' ' + pie), ('portal', ALERTA + ' ' + pie), ('portal', SALSA + ' ' + pie)]
    pl = cc.oraciones_plantilla(notas)
    assert cc.nz(pie) in pl
    # Impreso y web de la misma nota comparten pasajes enteros: no son plantilla.
    gemelas = [('eltiempo', 'Titular impreso. ' + ALERTA), ('eltiempo', 'Otro arranque web. ' + ALERTA)]
    assert not cc.oraciones_plantilla(gemelas)
    assert cc.quitar_plantillas(NAVIDAD + ' ' + pie, pl).strip() == NAVIDAD


def test_notas_distintas_del_mismo_medio_no_son_la_misma_nota():
    """Aunque el Contexto analizado traiga el encabezado (salidas viejas)."""
    rows = [_f('Pulzo.com', "Concurso 'Navidad en palabras e imágenes'", NAVIDAD, 'Concurso navideño de BibloRed',
               **{'Contexto analizado': PULZO + ' ' + NAVIDAD}),
            _f('Pulzo.com', 'Bogotá mantiene Alerta Fase 1', ALERTA, 'Declaratoria alerta ambiental Fase 1 suroccidente',
               **{'Contexto analizado': PULZO + ' ' + ALERTA}),
            _f('Pulzo.com', 'Bogotá anuncia Salsa al Parque 2026', SALSA, 'Festival Salsa al Parque 2026',
               **{'Contexto analizado': PULZO + ' ' + SALSA})]
    assert az.unificar_misma_nota_final(rows, KM) == 0
    assert [r['Subtema_IA'] for r in rows] == ['Concurso navideño de BibloRed',
                                               'Declaratoria alerta ambiental Fase 1 suroccidente',
                                               'Festival Salsa al Parque 2026']


def test_misma_nota_reproducida_sigue_unida():
    rows = [_f('Bogota.gov.co', "Participa en el concurso 'Navidad en palabras e imágenes'", NAVIDAD,
               'Concurso navideño de BibloRed', **{'Contexto analizado': NAVIDAD}),
            _f('Dxtcapital.com', "'NAVIDAD EN PALABRAS E IMÁGENES': BibloRed abre concurso", NAVIDAD,
               'Concurso infantil y juvenil de BibloRed', **{'Contexto analizado': NAVIDAD})]
    assert az.unificar_misma_nota_final(rows, KM) == 1
    assert rows[0]['Subtema_IA'] == rows[1]['Subtema_IA']


def test_guarda_final_restituye_subtema_ajeno():
    row = _f('Pulzo.com', "Concurso 'Navidad en palabras e imágenes' impulsa la creatividad infantil",
             NAVIDAD, 'Declaratoria alerta ambiental Fase 1 suroccidente',
             **{'Contexto analizado': NAVIDAD, '_sub_volcado': 'Concurso navideño de BibloRed',
                'ID Noticia': 62149319})
    fiel = _f('Pulzo.com', 'Bogotá mantiene Alerta Fase 1', ALERTA,
              'Declaratoria alerta ambiental Fase 1 suroccidente',
              **{'Contexto analizado': ALERTA, '_sub_volcado': 'Alerta Fase 1 por calidad del aire'})
    manual = dict(row, _correccion_manual=True)
    cambios = az.guarda_final_subtema_fiel([row, fiel, manual], KM)
    assert row['Subtema_IA'] == 'Concurso navideño de BibloRed'
    assert fiel['Subtema_IA'] == 'Declaratoria alerta ambiental Fase 1 suroccidente'
    assert manual['Subtema_IA'] == 'Declaratoria alerta ambiental Fase 1 suroccidente'
    assert [c['id'] for c in cambios] == [62149319]
