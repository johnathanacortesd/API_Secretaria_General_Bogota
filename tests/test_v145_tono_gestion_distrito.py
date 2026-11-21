"""v1.45: gestión, anuncio o respuesta con acción del Distrito = Positivo.

Criterio del usuario (2026-11-21): las acciones, gestiones, ayudas,
programas y anuncios de la Alcaldía, el alcalde, la Secretaría General y las
entidades adscritas son Positivo; una respuesta solo es Positiva si trae una
acción concreta; medidas, alertas y restricciones siguen Neutro.
Calibración: 431 titulares revisados a mano (13-21 nov 2026).
"""
import csv, os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az
import contexto_cliente as cc
import perfil_cliente

P = perfil_cliente.cargar_perfil('secretaria_general_de_la_alcaldia_de_bogota')
B, A, V = P['brand'], P['aliases'], P['voceros']
NEUTROS = P.get('tono_neutro_titulo') or ['Petro']
DET = cc.Detector(B, A, V, distrito=True)
KM = {'titulo': 'Título'}
BANCO = os.path.join(os.path.dirname(__file__), 'data', 'tono_titulares_revisados_2026-11.csv')


def _pos(tit, ctx='', det=None):
    return az.gestion_distrito_positiva(tit, ctx, det=det, terminos_neutros=NEUTROS, voceros=V)


def test_precision_en_titulares_revisados():
    with open(BANCO, encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    disparos = [r for r in filas if _pos(r['titulo'])]
    aciertos = sum(1 for r in disparos if r['tono'] == 'Positivo')
    assert len(disparos) >= 120
    assert aciertos / len(disparos) >= 0.90
    # Nunca sube un Negativo revisado.
    assert not [r for r in disparos if r['tono'] == 'Negativo']


def test_gestion_y_anuncios():
    assert _pos('Galán habilitó el primer tramo del nuevo corredor de la carrera Séptima')
    assert _pos('IDU conectó el nuevo puente de la Boyacá con 86')
    assert _pos('Bogotá tendrá tres bazares prenavideños con 60 emprendimientos liderados por mujeres')
    assert _pos('Convocatoria Jóvenes a la E: 3.000 becas para bachilleres en universidades privadas')
    assert _pos('Línea 1 del Metro de Bogotá ya tiene 20 kilómetros de viaducto construidos')
    assert _pos('En Bogotá fueron capturadas 492 personas durante la segunda semana de noviembre')


def test_medidas_alertas_y_respuestas_sin_accion_siguen_neutro():
    assert not _pos('Bogotá declara Alerta Fase 1 por calidad del aire en el suroccidente')
    assert not _pos('Pico y placa regional y plan retorno para el lunes festivo')
    assert not _pos('Alcaldía de Bogotá anuncia cierre en la avenida Boyacá por obras del acueducto')
    assert not _pos('Galán reconoce afectaciones al cronograma del metro por obras en la estación 16')
    assert not _pos('Metro de Bogotá: Línea 4 avanza, pero obras de la Primera Línea tendrán retrasos')


def test_respuesta_con_accion_es_positiva():
    tit = 'Vecinos denuncian caos en el cruce de la calle 26 con carrera 50'
    assert not _pos(tit, 'Los vecinos denunciaron trancones diarios.', det=DET)
    assert _pos(tit, 'Ante las quejas, la Secretaría de Movilidad instaló semáforos en el cruce.', det=DET)


def test_guardas_politica_otra_ciudad_fuente_y_privados():
    assert not _pos('¡Choque por obra de la Autonorte! Petro llamó embustero a De la Espriella')
    assert not _pos('Militarizar Villavicencio, un debate frente a la inseguridad',
                    'En enero de 2024 la alcaldía instaló un batallón en la comuna 7.', det=DET)
    # La Alcaldía solo como fuente del dato.
    assert not _pos('Bogotá se prepara para el Bar Week 2026',
                    'Según la información proporcionada por la Alcaldía de Bogotá, el evento contará '
                    'con más de 50 establecimientos con una cobertura amplia.', det=DET)
    # Con detector: un privado que ofrece algo no basta si el cuerpo no trae al Distrito.
    assert not _pos('Bogotá Gourmet 2026: más de 80 restaurantes ofrecen menús para dos',
                    'Los restaurantes participantes ofrecen menús desde 89.000 pesos.', det=DET)


def test_pase_final_y_propagacion():
    rows = [{'Título': 'Bogotá abre convocatoria para 3.000 becas en universidades privadas',
             'Contexto analizado': 'La Secretaría de Educación abrió la convocatoria.',
             'Tono_IA': 'Neutro', 'TIPO': 'Proyectos y programas', 'GÉNERO': 'Noticia'},
            {'Título': 'Requisitos para aplicar: así funciona el programa',
             'Contexto analizado': 'Estos son los requisitos.', 'Tono_IA': 'Neutro',
             'TIPO': 'Proyectos y programas', 'GÉNERO': 'Noticia'},
            {'Título': 'Bogotá abre convocatoria para 3.000 becas', 'Contexto analizado': '',
             'Tono_IA': 'Neutro', 'TIPO': 'Opinión de terceros', 'GÉNERO': 'Opinión'},
            {'Título': 'Bogotá abre convocatoria de becas', 'Contexto analizado': '',
             'Tono_IA': 'Neutro', '_tono_manual': True},
            {'Título': 'Entrega de viviendas', 'Tono_IA': 'Negativo'}]
    out = az.aplicar_gestion_distrito_final(rows, KM, B, A, V, noticias=[[0, 1]],
                                            terminos_neutros=NEUTROS)
    assert out == [0, 1]
    assert [r['Tono_IA'] for r in rows] == ['Positivo', 'Positivo', 'Neutro', 'Neutro', 'Negativo']
