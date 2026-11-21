import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az
import perfil_cliente

P = perfil_cliente.cargar_perfil('secretaria_general_de_la_alcaldia_de_bogota')
B, A, V = P['brand'], P['aliases'], P['voceros']
ACT = [B] + A + V
KM = {'titulo': 'Título'}

# Caso real 2026-11-21 (salía Positivo).
MORRIS = ('El periodista pidió el restablecimiento del servicio y una respuesta de la Alcaldía y del '
          'Grupo Energía Bogotá sobre la duración y el origen de la interrupción Hollman Morrris y el '
          'alcalde de Bogotá, Carlos Fernando Galán (Redes sociales) El periodista Hollman Morris pidió '
          'explicaciones al alcalde de Bogotá, Carlos Fernando Galán, y al Grupo Energía Bogotá (GEB) por '
          'un corte de electricidad que, según denunció, mantuvo sin servicio a los barrios Galerías y San '
          'Luis, en la localidad de Teusaquillo, desde la noche del 20 de noviembre de 2026. […] Hasta el '
          'momento de la publicación, no se incluyó una respuesta oficial de la Alcaldía de Bogotá ni del '
          'Grupo Energía Bogotá sobre el corte denunciado.')
TITULOS = ['Hollman Morris pide explicaciones a Galán por corte de luz en Teusaquillo',
           'Corte de luz en Teusaquillo: Hollman Morris pide restablecer el servicio',
           'Hollman Morris le reclama a Galán por apagón en Galerías y San Luis']


def _tono(fn, tit, ctx, tono, **kw):
    g = {'grupo': 1, 'titulo': tit, 'contexto': ctx, 'texto': ctx}
    e = {1: {'tono': tono, 'tipo': 'Gestión', 'genero': 'Noticia'}}
    fn([g], e, B, A, voceros=V, **kw)
    return e[1]['tono']


def test_caso_morris_es_negativo():
    for t in TITULOS:
        assert az._reclamo_sin_respuesta(t, MORRIS, ACT), t
        # La regla del Distrito ya no lo sube a Positivo.
        assert _tono(az.aplicar_regla_distrito, t, MORRIS, 'Neutro') == 'Neutro', t
        for t0 in ('Positivo', 'Neutro'):
            assert _tono(az.aplicar_regla_reclamo_sin_respuesta, t, MORRIS, t0) == 'Negativo', t
        rows = [{'Título': t, 'CuerpoEs': MORRIS, 'Tono_IA': 'Positivo', 'TIPO': 'Gestión'}]
        assert az.aplicar_reclamo_sin_respuesta_final(rows, KM, B, A, voceros=V) == [0]
        assert rows[0]['Tono_IA'] == 'Negativo'


def test_con_respuesta_de_la_alcaldia_no_aplica():
    ctx = ('Hollman Morris pidió explicaciones al alcalde Galán por un corte de electricidad en '
           'Teusaquillo. La Alcaldía respondió que el servicio se restableció en la madrugada y '
           'que el GEB revisa la causa.')
    assert not az._reclamo_sin_respuesta('Hollman Morris pide explicaciones a Galán por corte de luz', ctx, ACT)


def test_pedidos_sin_problema_y_otras_ciudades_no_aplican():
    casos = [('Artistas piden al alcalde Galán apoyo para el festival de jazz',
              'Los artistas pidieron al alcalde Galán apoyo para el festival de jazz de diciembre.'),
             ('Concejales de Medellín critican al alcalde por cortes de agua',
              'Los concejales cuestionaron al alcalde de Medellín por los cortes de agua en Belén.'),
             ('Galán entrega 300 viviendas en Bosa',
              'El alcalde Galán entregó 300 viviendas. Hasta el momento de la publicación no hubo incidentes.')]
    for t, c in casos:
        assert not az._reclamo_sin_respuesta(t, c, ACT), t


def test_publicacion_ya_no_es_hecho_bueno():
    assert not az._hecho_bueno_distrito(az.nz('Hasta el momento de la publicación no hubo respuesta'))
    assert not az._hecho_bueno_distrito(az.nz('Robos en el transporte público de la ciudad'))
    assert az._hecho_bueno_distrito(az.nz('La Alcaldía entregó 300 viviendas'))


def test_manual_y_politica_mandan():
    rows = [{'Título': TITULOS[0], 'CuerpoEs': MORRIS, 'Tono_IA': 'Neutro', '_correccion_manual': True},
            {'Título': TITULOS[0], 'CuerpoEs': MORRIS, 'Tono_IA': 'Neutro', '_subtema_politico': 'petro'}]
    assert az.aplicar_reclamo_sin_respuesta_final(rows, KM, B, A, voceros=V) == []


def test_silencio_de_otro_actor_no_cuenta():
    # «no se pronunció» es de un homónimo (Juan Manuel Galán), no del alcalde,
    # y el alcalde sí responde («reconoce»).
    t = 'Galán reconoce afectaciones al cronograma del metro'
    c = ('Un concejal cuestionó a la Alcaldía de Bogotá por los retrasos del metro. El alcalde '
         'Carlos Fernando Galán reconoce que hay afectaciones. Juan Manuel Galán, director del '
         'Nuevo Liberalismo, no se pronunció.')
    assert not az._reclamo_sin_respuesta(t, c, ACT)


def test_gestion_mas_critica_sigue_neutro():
    c = ('La Alcaldía de Bogotá inauguró el parque, pero vecinos cuestionaron a la Alcaldía de '
         'Bogotá por los retrasos de la obra.')
    assert not az._reclamo_sin_respuesta('Alcaldía de Bogotá inaugura parque', c, ACT)
