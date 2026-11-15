# -*- coding: utf-8 -*-
"""v1.37: subtemas políticos fijos y memoria de subtemas del boletín."""
import analyzer_tono_tema as a
import memoria_cliente as m

VOC = ['Carlos Fernando Galán', 'Galán', 'Miguel Silva']
REGLAS = {'aspirantes': 'Aspirantes Alcaldía de Bogotá', 'petro': 'Entorno Gustavo Petro'}


def _fila(titulo, sub='Otro', tono='Positivo', tipo='Institucional', genero='Opinión'):
    return {'Título': titulo, 'CuerpoEs': titulo + '. Texto de la nota.', 'Subtema_IA': sub,
            'Tono_IA': tono, 'TIPO': tipo, 'GÉNERO': genero}


def test_aspirantes():
    for t in ["Juan Daniel Oviedo confirma que será candidato a la Alcaldía de Bogotá",
              "Encuesta: así va la intención de voto para la Alcaldía de Bogotá",
              "Gustavo Bolívar se lanza a la Alcaldía",
              "¿Quién será el próximo alcalde de Bogotá?"]:
        assert a.es_nota_aspirantes_alcaldia(t, '', VOC), t
    for t in ["Candidatos a la Alcaldía de Medellín debaten",
              "Alcalde Galán inaugura colegio en Bosa",
              "Petro anuncia reforma tributaria"]:
        assert not a.es_nota_aspirantes_alcaldia(t, '', VOC), t


def test_petro_alcalde():
    assert a.es_nota_petro_alcalde("¿Uribe ve a Petro candidato a la Alcaldía de Bogotá?")
    assert a.es_nota_petro_alcalde("Cuando Petro era alcalde: la crisis de las basuras")
    assert not a.es_nota_petro_alcalde("Petro anuncia reforma tributaria")


def test_aplicar_fija_subtema_tono_tipo_y_conserva_genero():
    rows = [_fila("Oviedo será candidato a la Alcaldía de Bogotá"),
            _fila("¿Uribe ve a Petro candidato a la Alcaldía de Bogotá?", tono='Negativo',
                  genero='Entrevista'),
            _fila("Galán inaugura colegio en Bosa", sub='Colegio en Bosa')]
    out = a.aplicar_subtemas_politicos(rows, {}, REGLAS, voceros=VOC)
    assert out['aspirantes'] == 1 and out['petro'] == 1
    assert rows[0]['Subtema_IA'] == 'Aspirantes Alcaldía de Bogotá'
    assert rows[0]['Tono_IA'] == 'Neutro' and rows[0]['TIPO'] == 'Información general'
    assert rows[0]['GÉNERO'] == 'Opinión'
    assert rows[1]['Subtema_IA'] == 'Entorno Gustavo Petro' and rows[1]['Tono_IA'] == 'Neutro'
    assert rows[1]['GÉNERO'] == 'Entrevista'
    assert rows[2]['Subtema_IA'] == 'Colegio en Bosa' and rows[2]['Tono_IA'] == 'Positivo'


def test_sin_reglas_no_toca():
    rows = [_fila("Oviedo será candidato a la Alcaldía de Bogotá")]
    a.aplicar_subtemas_politicos(rows, {}, {}, voceros=VOC)
    assert rows[0]['Subtema_IA'] == 'Otro'


def test_memoria_subtemas_similar(tmp_path):
    extra = {'historial_dir': str(tmp_path)}
    m.guardar_subtemas('Cliente', [
        m._entrada("Galán anuncia nuevas obras del metro en la Avenida 68", "", "Obras del metro en la Avenida 68"),
        m._entrada("Hurto en Kennedy deja un herido", "", "Hurto en Kennedy")], extra)
    ent = m.cargar_subtemas('Cliente', extra)
    assert m.buscar_subtema(ent, "Galán anuncia las nuevas obras del metro en la Avenida 68") \
        == "Obras del metro en la Avenida 68"
    assert m.buscar_subtema(ent, "HURTO EN KENNEDY DEJA UN HERIDO") == "Hurto en Kennedy"
    # mismo molde, otro lugar: no es la misma noticia
    assert m.buscar_subtema(ent, "Hurto en Suba deja un herido") is None


def test_anclar_por_noticia(tmp_path):
    ent = [m._entrada("Galán anuncia nuevas obras del metro en la Avenida 68", "", "Obras del metro en la Avenida 68")]
    rows = [_fila("Galán anuncia las nuevas obras del metro en la Avenida 68", sub='Metro Avenida 68'),
            _fila("Obras del metro llegan a la 68", sub='Metro Avenida 68'),
            _fila("Hurto en Suba deja un herido", sub='Hurto en Suba')]
    n = a.anclar_subtemas_previos(rows, {}, ent)
    assert n == 2
    assert rows[0]['Subtema_IA'] == rows[1]['Subtema_IA'] == "Obras del metro en la Avenida 68"
    assert rows[2]['Subtema_IA'] == 'Hurto en Suba'
