"""v1.52 (regla del usuario 2026-11-25): operativos, allanamientos, capturas,
incautaciones, recuperación del espacio público y respuesta con acción del
Distrito = Positivo; las restricciones puras siguen Neutro."""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az
import contexto_cliente as cc
import motor_haiku as mh

VOC = ['Carlos Fernando Galán', 'Galán', 'el alcalde']
DET = cc.Detector('Secretaría General de la Alcaldía de Bogotá', ['Alcaldía de Bogotá'], VOC, distrito=True)


def _pos(tit, ctx):
    return az.gestion_distrito_positiva(tit, ctx, det=DET, terminos_neutros=['Petro'], voceros=VOC)


def test_operativos_y_acciones_son_positivo():
    assert _pos('Operativo en Bosa revela red de falsificación de bebidas: incautan productos y capturan a un implicado',
                'De acuerdo con información compartida por la Alcaldía de Bogotá, las autoridades ubicaron dos inmuebles.')
    assert _pos('Allanamientos en Kennedy dejan cinco capturados',
                'La Secretaría de Seguridad y la Policía realizaron 12 allanamientos en Kennedy.')
    assert _pos('Bogotá refuerza la atención a mujeres víctimas de violencia con una nueva ruta de apoyo',
                'La Secretaría Distrital de la Mujer refuerza las rutas de atención.')
    assert _pos('Las obras inconclusas de Usaquén vuelven a generar polémica: el IDU reclama 7.500 millones al contratista',
                'El Instituto de Desarrollo Urbano mantiene un procedimiento sancionador contra el consorcio responsable.')
    assert _pos('Recuperan espacio público en Los Mártires',
                'La Alcaldía Local de Los Mártires realizó un operativo de recuperación del espacio público.')


def test_restricciones_siguen_neutro():
    assert not _pos('Pico y placa en Bogotá para este miércoles 25 de noviembre',
                    'Según el calendario de la Secretaría Distrital de Movilidad, la medida se aplica por placa.')
    assert not _pos('Cortes de agua en varios barrios de Bogotá por obras del Acueducto',
                    'La Empresa de Acueducto de Bogotá programó cortes de agua.')
    # Un operativo de otra ciudad sin el cliente no sube.
    assert not _pos('Operativo en Medellín deja tres capturados', 'La Policía de Medellín capturó a tres personas.')


def test_rubrica_y_perfil_dicen_que_los_operativos_son_positivo():
    assert 'allanamientos' in mh.RUBRICA_TONO and 'operativos de control o de espacio público) son referencial' not in mh.RUBRICA_TONO
    import json
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'clientes', 'secretaria_general_de_la_alcaldia_de_bogota.json')
    crit = json.load(open(p, encoding='utf-8'))['criterio_custom']
    assert 'allanamientos' in crit and 'NO son medidas restrictivas' in crit
