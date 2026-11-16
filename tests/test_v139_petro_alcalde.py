import analyzer_tono_tema as a
import pipeline

VOC = ['Carlos Fernando Galán', 'Galán']
REGLAS = {'aspirantes': 'Aspirantes Alcaldía de Bogotá', 'petro': 'Entorno Gustavo Petro'}


def test_titulares_petro_alcalde():
    for t in ['Así fue la alcaldía de Gustavo Petro en Bogotá',
              'Cuando Petro era alcalde de la ciudad, el metro elevado',
              'El legado de Petro en Bogotá: basuras y metro',
              'Petro y la crisis de las basuras de 2012',
              'Exmandatario Petro y su paso por el Palacio Liévano']:
        assert a.es_nota_petro_alcalde(t), t


def test_no_petro_alcalde():
    for t in ['Petro anuncia reforma tributaria', 'Petro en Bogotá: marcha por la reforma',
              'Petro critica a la alcaldesa de Medellín']:
        assert not a.es_nota_petro_alcalde(t), t


def test_entrada_sin_petro_en_titular():
    h = 'En 2012, cuando Gustavo Petro era alcalde, la ciudad vivió la crisis de las basuras.'
    assert a.es_nota_petro_alcalde('Diez años de la crisis de las basuras', h, voceros=VOC)
    assert not a.es_nota_petro_alcalde('Galán anuncia nuevo modelo de aseo', h, voceros=VOC)
    assert not a.es_nota_petro_alcalde('Diez años de la crisis de las basuras',
                                       'La crisis de las basuras afectó a la ciudad.', voceros=VOC)


def test_opinion_no_cambia_tipo_politico():
    rows = [{'Título': 'Columna: la alcaldía de Gustavo Petro', 'Tono_IA': 'Negativo',
             'TIPO': 'Gestión', 'GÉNERO': 'Noticia', 'Sección - Programa': 'Opinión',
             'Subtema_IA': 'x'}]
    km = {'titulo': 'Título', 'resumen': 'Resumen'}
    out = a.aplicar_subtemas_politicos(rows, km, REGLAS, voceros=VOC)
    assert out['petro'] == 1
    pipeline.aplicar_opinion_haiku(rows, 'Alcaldía de Bogotá', [], VOC)
    r = rows[0]
    assert r['GÉNERO'] == 'Opinión'
    assert r['TIPO'] == 'Información general'
    assert r['Tono_IA'] == 'Neutro' and r['Subtema_IA'] == 'Entorno Gustavo Petro'
