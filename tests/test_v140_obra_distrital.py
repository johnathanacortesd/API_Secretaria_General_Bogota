import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az
import perfil_cliente

P = perfil_cliente.cargar_perfil('secretaria_general_de_la_alcaldia_de_bogota')
B, A, V = P['brand'], P['aliases'], P['voceros']
CTX = ('El izaje de los 280 metros de infraestructura metálica del nuevo puente peatonal y '
       'ciclopeatonal de la avenida Boyacá con calle 86A finalizó con éxito durante este fin de '
       'semana festivo en Bogotá. Según el reporte del Instituto de Desarrollo Urbano (IDU), la obra '
       'ya registra un avance general superior al 87 % y, una vez entre en operación, beneficiará '
       'directamente a más de 57.000 ciclistas y 30.000 peatones que transitan diariamente por este '
       'corredor vial.')
TIT = 'Finaliza izaje del puente peatonal de la avenida Boyacá con calle 86A'


def _run(fn, tit, ctx, tono, **kw):
    g = {'grupo': 1, 'titulo': tit, 'contexto': ctx, 'texto': ctx}
    e = {1: {'tono': tono, 'tipo': 'Proyectos y programas', 'genero': 'Noticia'}}
    fn([g], e, B, A, voceros=V, **kw)
    return e[1]['tono']


def test_neutro_sube_a_positivo():
    assert _run(az.aplicar_regla_secretarias_distritales, TIT, CTX, 'Neutro') == 'Positivo'


def test_positivo_no_es_incidental():
    assert _run(az.aplicar_regla_positivo_incidental, TIT, CTX, 'Positivo',
                solo_gestion=True) == 'Positivo'


def test_casos_adversos_no_suben():
    for tit, ctx in [('Retrasos en el puente de la Boyacá con 86A', CTX),
                     ('Comunidad denuncia demoras en obra del IDU',
                      'Según el IDU, la obra registra un avance del 40 % y los vecinos critican el retraso.'),
                     ('Motociclista murió en la avenida Boyacá',
                      'El accidente ocurrió cerca de la obra del puente; según el IDU la vía estaba señalizada.')]:
        assert _run(az.aplicar_regla_secretarias_distritales, tit, ctx, 'Neutro') == 'Neutro', tit


def test_sin_entidad_distrital_no_cuenta():
    assert not az._obra_distrital_avanza('Puente en Medellín supera el 87 % de avance',
                                         'La obra registra un avance general superior al 87 %.')
