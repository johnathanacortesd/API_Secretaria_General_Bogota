"""v1.46: la misma nota en impreso y web del mismo medio, o reproducida por
otro medio, lleva el mismo subtema (portado de Defensoría v1.33)."""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az

KM = {'titulo': 'Título', 'resumen': 'Resumen - Aclaracion', 'medio': 'Medio'}
PASAJE = ('El alcalde Carlos Fernando Galán anunció que la Alcaldía de Bogotá destinará 120.000 '
          'millones de pesos para la segunda fase del programa de mantenimiento de la malla vial '
          'local en Kennedy, Bosa y Suba, que comenzará en enero y durará diez meses.')


def _f(medio, tit, sub, ctx, **kw):
    return dict({'Medio': medio, 'Título': tit, 'Subtema_IA': sub, 'Contexto analizado': ctx,
                 'Tono_IA': 'Positivo'}, **kw)


def test_impreso_y_web_del_mismo_medio():
    rows = [_f('El Tiempo', 'Más recursos para las vías de barrio', 'Inversión en malla vial local',
               'En la presentación del plan, ' + PASAJE),
            _f('Eltiempo.com', 'Así será la segunda fase del arreglo de vías en Kennedy, Bosa y Suba',
               'Mantenimiento de vías en Kennedy, Bosa y Suba', 'Publicidad ' + PASAJE)]
    salida = []
    assert az.unificar_misma_nota_final(rows, KM, salida_noticias=salida) == 1
    assert rows[0]['Subtema_IA'] == rows[1]['Subtema_IA']
    assert salida == [[0, 1]]


def test_frase_corta_compartida_no_une():
    frase = 'La Alcaldía de Bogotá informó que la medida rige desde el lunes.'
    rows = [_f('El Tiempo', 'Pico y placa en diciembre', 'Pico y placa en diciembre', 'Movilidad: ' + frase),
            _f('Eltiempo.com', 'Restricción de parrillero en Kennedy', 'Restricción de parrillero en Kennedy',
               'Seguridad: ' + frase)]
    assert az.unificar_misma_nota_final(rows, KM) == 0


def test_correccion_manual_manda_sobre_la_gemela():
    rows = [_f('El Tiempo', 'Más recursos para las vías de barrio', 'Malla vial local 2027',
               PASAJE, _correccion_manual=True),
            _f('Eltiempo.com', 'Segunda fase del arreglo de vías', 'Mantenimiento de vías', PASAJE)]
    az.unificar_misma_nota_final(rows, KM)
    assert [r['Subtema_IA'] for r in rows] == ['Malla vial local 2027'] * 2
