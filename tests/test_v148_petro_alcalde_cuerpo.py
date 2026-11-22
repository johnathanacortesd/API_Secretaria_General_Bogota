"""v1.48: Petro y su alcaldía = «Entorno Gustavo Petro», Neutro, Información
general, aunque el pasaje esté en medio del cuerpo y el titular no nombre a
Petro.

Caso real (2026-11-22): una nota sobre procuradores que han enfrentado a
mandatarios. El único pasaje con la Alcaldía es «En diciembre de 2013 […]
Ordóñez destituyó e inhabilitó por quince años al entonces alcalde de Bogotá,
Gustavo Petro […]», lejos de la entrada. La regla solo leía los primeros 600
caracteres y el Contexto analizado, y la nota salía con otro subtema.
"""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az
import perfil_cliente

P = perfil_cliente.cargar_perfil('secretaria_general_de_la_alcaldia_de_bogota')
V = az.expandir_voceros(P['voceros'])
DET = az.detector_cliente(P['brand'], P['aliases'], V, distrito=True)
KM = {'titulo': 'Título'}
REGLAS = {'aspirantes': 'Aspirantes Alcaldía de Bogotá', 'petro': 'Entorno Gustavo Petro'}

INTRO = ('El procurador Gregorio Eljach abrió una indagación disciplinaria que volvió a poner '
         'a la Procuraduría en el centro del debate. No es la primera vez: varios procuradores '
         'han tenido choques con mandatarios en la historia reciente del país, y estos son los '
         'casos más recordados por la opinión pública nacional y por los analistas. ') * 2
ORDONEZ = ('El primero fue Alejandro Ordóñez Maldonado . En diciembre de 2013, cuando ejercía '
           'como procurador general de la Nación, Ordóñez destituyó e inhabilitó por quince años '
           'al entonces alcalde de Bogotá, Gustavo Petro, por presuntas irregularidades '
           'relacionadas con la implementación del nuevo esquema de recolección de basuras. Su '
           'principal cuestionamiento se concentraba en la improvisación administrativa, las '
           'deficiencias de planeación y las decisiones que, a su juicio, habían puesto en riesgo '
           'la prestación de un servicio público esencial.')


def _cuerpo(tit, txt):
    return az.es_nota_petro_alcalde_cuerpo(tit, txt, det=DET, voceros=V)


def test_pasaje_ordonez_en_medio_del_cuerpo():
    assert len(INTRO) > 600
    assert _cuerpo('Los procuradores que se han enfrentado a Petro', INTRO + ORDONEZ)
    assert _cuerpo('Los procuradores más polémicos del país', INTRO + ORDONEZ)
    # Otra ciudad en otra oración no lo impide.
    assert _cuerpo('Eljach abre indagación contra Petro', INTRO + ORDONEZ
                   + ' Margarita Cabello suspendió al alcalde de Medellín, Daniel Quintero.')


def test_no_si_la_alcaldia_actual_aparece():
    assert not _cuerpo('Galán responde a la Procuraduría', INTRO + ORDONEZ)
    assert not _cuerpo('Procuraduría y Petro', INTRO + ORDONEZ
                       + ' Por su parte, la Alcaldía de Bogotá anunció nuevos camiones de basura.')
    assert not _cuerpo('Petro critica el metro elevado',
                       'Petro dijo que el metro elevado es un error. La Alcaldía de Bogotá '
                       'respondió que las obras avanzan.')
    assert not _cuerpo('Metro de Bogotá llega al 70 %',
                       'El metro avanza. El proyecto lo propuso Petro cuando era alcalde. '
                       'La Empresa Metro informó el avance.')
    assert not _cuerpo('Petro habla de la paz', 'Petro habló de la paz total en el Cauca.')


def test_aplicar_subtemas_politicos_fija_entorno_petro():
    rows = [{'Título': 'Los procuradores más polémicos del país', 'CuerpoEs': INTRO + ORDONEZ,
             'Contexto analizado': 'Varios procuradores han tenido choques con mandatarios.',
             'Tono_IA': 'Negativo', 'Subtema_IA': 'Destitución de Petro por Ordóñez',
             'TIPO': 'Noticia'}]
    out = az.aplicar_subtemas_politicos(rows, KM, REGLAS, voceros=V, con_tipo=True, det=DET)
    assert out['petro'] == 1
    r = rows[0]
    assert (r['Subtema_IA'], r['Tono_IA'], r['TIPO']) == \
        ('Entorno Gustavo Petro', 'Neutro', 'Información general')
