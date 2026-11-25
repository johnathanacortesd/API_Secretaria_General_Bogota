"""v1.51 (dossier 2026-11-25 14:49): subtema sobre Petro => Neutro / Entorno
político / Información general; la acción del alcalde en el cuerpo de una
nota con titular de otra ciudad sube a Positivo."""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az
import contexto_cliente as cc
import perfil_cliente as pc

KM = {'titulo': 'Título'}
VOC = ['Carlos Fernando Galán', 'Galán', 'el alcalde']


def test_subtema_de_petro_pasa_a_entorno_politico():
    rows = [{'Título': 'Gustavo Petro sale en defensa de la representante Verónica Estrada',
             'Subtema_IA': 'Defensa de Petro a congresista Estrada', 'Tono_IA': 'Negativo',
             'TIPO': 'Opinión de terceros'},
            {'Título': 'La vocación guerrillera del expresidente Gustavo Petro',
             'Subtema_IA': 'Crítica al expresidente Gustavo Petro', 'Tono_IA': 'Neutro', 'TIPO': 'Opinión de terceros'},
            {'Título': 'Galán responde a Petro por el metro',
             'Subtema_IA': 'Respuesta de Galán a Petro por el metro', 'Tono_IA': 'Neutro'},
            {'Título': 'Petro fue alcalde', 'Subtema_IA': 'Petro como exalcalde', 'Tono_IA': 'Neutro',
             '_correccion_manual': True},
            {'Título': 'Petro alcalde', 'Subtema_IA': 'Entorno Gustavo Petro', 'Tono_IA': 'Neutro',
             '_subtema_politico': 'petro'}]
    cambios = az.aplicar_entorno_petro(rows, KM, 'Entorno Gustavo Petro', voceros=VOC, con_tipo=True)
    # v1.54: la corrección manual (fila 3) ya no exime un subtema sobre Petro.
    assert cambios == [0, 1, 3]
    for r in rows[:2]:
        assert (r['Tono_IA'], r['Subtema_IA'], r['TIPO']) == ('Neutro', 'Entorno Gustavo Petro',
                                                              'Información general')
    assert rows[2]['Subtema_IA'] == 'Respuesta de Galán a Petro por el metro'
    assert rows[3]['Subtema_IA'] == 'Entorno Gustavo Petro'
    assert rows[4]['Subtema_IA'] == 'Entorno Gustavo Petro'


def test_perfil_conserva_petro_general():
    d = pc.normalizar_perfil({'nombre': 'x', 'subtemas_politicos': {'petro': 'Entorno Gustavo Petro',
                                                                    'petro_general': 'Entorno político'}}) \
        if hasattr(pc, 'normalizar_perfil') else None
    if d is not None:
        assert d['subtemas_politicos']['petro_general'] == 'Entorno político'


def test_red_hospitalaria_con_titular_de_otra_ciudad_es_positivo():
    det = cc.Detector('Secretaría General de la Alcaldía de Bogotá', ['Alcaldía de Bogotá'], VOC, distrito=True)
    tit = 'Gobernadores de Colombia cierran filas con el Meta tras el atentado en Villavicencio'
    ctx = ('Entre las iniciativas de colaboración destaca la ofrecida por el alcalde de Bogotá, Carlos '
           'Fernando Galán, quien manifestó su solidaridad con Villavicencio y puso a disposición la red '
           'pública hospitalaria de la capital para atender a las personas que necesitaran ser trasladadas.')
    assert az.gestion_distrito_positiva(tit, ctx, det=det, terminos_neutros=['Petro'], voceros=VOC)
    # La «Alcaldía» suelta en una nota de otra ciudad no es el cliente.
    otra = 'La Alcaldía dispuso albergues para las familias afectadas por la explosión.'
    assert not az.gestion_distrito_positiva(tit, otra, det=det, terminos_neutros=['Petro'], voceros=VOC)
