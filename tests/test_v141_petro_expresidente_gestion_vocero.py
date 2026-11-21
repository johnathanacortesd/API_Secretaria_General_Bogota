import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az
import perfil_cliente

P = perfil_cliente.cargar_perfil('secretaria_general_de_la_alcaldia_de_bogota')
B, A, V = P['brand'], P['aliases'], P['voceros']
KM = {'titulo': 'Título'}
REGLAS = P['subtemas_politicos']

AUTOPISTA = (
    'Durante el evento, el alcalde destacó la importancia de haber destrabado el proyecto para '
    'darle una nueva cara al principal acceso de Bogotá por el norte. "En nuestra administración '
    'logramos destrabar lo que nos correspondía y el presidente Abelardo De La Espriella, desde su '
    'llegada, se comprometió con esta obra y trabajó para que el proyecto avanzara, por eso hoy '
    'presentamos las obras que permitirán ampliar la autopista Norte de seis a 12 carriles", '
    'señaló Galán.')


def _fila(tit, txt, tono='Negativo'):
    return {'Título': tit, 'CuerpoEs': txt, 'Tono_IA': tono, 'TIPO': 'Gestión',
            'GÉNERO': 'Noticia', 'Subtema_IA': 'x'}


def test_expresidente_petro_cuando_era_alcalde():
    casos = [
        ('Polémica por el metro de Bogotá',
         'El expresidente Gustavo Petro, cuando era alcalde de la ciudad, propuso un metro subterráneo.'),
        ('Expresidente Petro critica obras de la autopista Norte',
         'Petro, quien fue alcalde de Bogotá entre 2012 y 2015, dijo que dejó los diseños.'),
        ('Durante la alcaldía del hoy expresidente Petro se firmó el contrato', ''),
        ('El expresidente Petro y las basuras',
         'Cuando el expresidente Gustavo Petro era alcalde, cambió el modelo de aseo.'),
    ]
    for tit, h in casos:
        assert az.es_nota_petro_alcalde(tit, h, voceros=V), tit
        rows = [_fila(tit, h)]
        az.aplicar_subtemas_politicos(rows, KM, REGLAS, voceros=V)
        r = rows[0]
        assert (r['Tono_IA'], r['Subtema_IA'], r['TIPO']) == \
            ('Neutro', 'Entorno Gustavo Petro', 'Información general'), tit


def test_petro_presidente_no_es_alcalde():
    for tit, h in [('Polémica por el metro',
                    'El gobierno de Petro firmó el convenio del metro cuando era presidente.'),
                   ('Cuando Petro era presidente', 'Cuando Gustavo Petro era presidente, la reforma...'),
                   ('Galán anuncia metro', 'El expresidente Gustavo Petro, cuando era alcalde, propuso un metro.')]:
        assert not az.es_nota_petro_alcalde(tit, h, voceros=V), tit


def test_galan_reivindica_obra_autopista_positivo():
    rows = [_fila('Arrancan las obras de ampliación de la autopista Norte', AUTOPISTA, tono='Neutro')]
    assert az.aplicar_gestion_vocero_final(rows, KM, B, A, voceros=V) == [0]
    assert rows[0]['Tono_IA'] == 'Positivo'
    g = {'grupo': 1, 'titulo': 'Arrancan las obras de ampliación de la autopista Norte',
         'contexto': AUTOPISTA, 'texto': AUTOPISTA}
    e = {1: {'tono': 'Neutro', 'tipo': 'Proyectos y programas', 'genero': 'Noticia'}}
    az.aplicar_regla_secretarias_distritales([g], e, B, A, voceros=V)
    assert e[1]['tono'] == 'Positivo'
    e = {1: {'tono': 'Positivo', 'tipo': 'Proyectos y programas', 'genero': 'Noticia'}}
    az.aplicar_regla_positivo_incidental([g], e, B, A, voceros=V, solo_gestion=True)
    assert e[1]['tono'] == 'Positivo'


def test_gestion_vocero_no_sube_adversos():
    for tit, txt in [
            ('Galán reconoce retrasos en la autopista Norte',
             '"Logramos destrabar parte, pero hay retrasos en las obras", señaló Galán.'),
            ('Concejales critican a Galán por obras de la autopista Norte',
             'Los concejales criticaron al alcalde Galán por el retraso. "Logramos destrabar el '
             'proyecto", respondió Galán.'),
            ('Presidente dice que logramos destrabar', 'El presidente dijo "logramos destrabar el proyecto".'),
            ('Alcalde de Medellín inaugura obra',
             'El alcalde de Medellín dijo: "inauguramos la obra del puente".')]:
        rows = [_fila(tit, txt, tono='Neutro')]
        assert az.aplicar_gestion_vocero_final(rows, KM, B, A, voceros=V) == [], tit


def test_petro_manda_sobre_gestion():
    rows = [_fila('Petro: cuando fui alcalde logramos destrabar el metro',
                  '"Logramos destrabar el proyecto del metro", dijo Petro.', tono='Neutro')]
    az.aplicar_subtemas_politicos(rows, KM, REGLAS, voceros=V)
    assert az.aplicar_gestion_vocero_final(rows, KM, B, A, voceros=V) == []
    assert rows[0]['Tono_IA'] == 'Neutro'
