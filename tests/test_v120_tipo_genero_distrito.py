# -*- coding: utf-8 -*-
# Tests v1.20 Secretaría: TIPO/GÉNERO 3->5, rescate Ranking, tono del
# distrito y caso de regresión TransMilenio/Alcaldía (2026-11-01).
# Sin llamadas a API: JSON LLM simulado + filas sintéticas + llamadas
# directas a las reglas deterministas.
import unittest

import analyzer_tono_tema as A
from pipeline import aplicar_genero_por_url

BRAND = 'Secretaría General de la Alcaldía de Bogotá'
ALIASES = ['Secretaría General',
           'Secretaría General de la Alcaldía de Bogotá',
           'Alcaldía de Bogotá']
VOCEROS = ['Miguel Silva Moyano', 'Miguel Silva', 'Carlos Fernando Galán',
           'Galán', 'Carlos Galán', 'el alcalde']
ACTORES = [A.nz(x) for x in [BRAND] + ALIASES + VOCEROS]


def grupo(gid, titulo, texto, tono, tipo=None, genero=None, pegajoso=False):
    g = {'grupo': gid, 'titulo': titulo, 'texto': texto, 'contexto': texto,
         'titulos_alt': []}
    e = {'tono': tono}
    if tipo is not None:
        e['tipo'] = tipo
    if genero is not None:
        e['genero'] = genero
    if pegajoso:
        e['flags'] = {'neutro_pegajoso': True}
    return g, {gid: e}


def distrito(gid, titulo, texto, tono, pegajoso=False):
    g, et = grupo(gid, titulo, texto, tono, pegajoso=pegajoso)
    A.aplicar_regla_distrito([g], et, BRAND, ALIASES, voceros=VOCEROS)
    return et[gid]['tono']


FRAG_TRANSMILENIO = (
    'En este contexto, TransMilenio, junto a la Alcaldía de Bogotá anunció '
    'que acompañará a los asistentes antes y después del evento, con '
    'información sobre los servicios de transporte disponibles y '
    'alternativas para facilitar los desplazamientos por la capital. La '
    'entidad recomendó consultar los recorridos con anticipación y recargar '
    'la tarjeta TuLlave para evitar contratiempos al momento de ingresar '
    'al sistema.')


class TestTipoGeneroListas(unittest.TestCase):
    def test_listas_ampliadas(self):
        self.assertIn('Ranking', A.TIPOS_VALIDOS)
        self.assertIn('Opinión de terceros', A.TIPOS_VALIDOS)
        self.assertIn('Editorial', A.GENEROS_VALIDOS)
        self.assertIn('Reportaje', A.GENEROS_VALIDOS)
        self.assertEqual(A.TIPO_DEFECTO, 'Información general')
        self.assertEqual(A.GENERO_DEFECTO, 'Noticia')

    def test_canon_orden_invertido(self):
        self.assertEqual(
            A._canon_tipo_genero('Programas y proyectos', A.TIPOS_VALIDOS),
            'Proyectos y programas')
        self.assertEqual(
            A._canon_tipo_genero('Ranking', A.TIPOS_VALIDOS), 'Ranking')
        self.assertIsNone(
            A._canon_tipo_genero('Cosa inventada', A.TIPOS_VALIDOS))

    def test_normaliza_label_nuevos_valores(self):
        d = {'resultados': [{'id': 1, 'sub_tema': 'x', 'tono': 'Neutro',
                             'tipo': 'Ranking', 'genero': 'Reportaje'}]}
        out = A._normaliza_label(d, [1], con_tipo_genero=True)
        self.assertEqual(out[1]['tipo'], 'Ranking')
        self.assertEqual(out[1]['genero'], 'Reportaje')

    def test_voto_mayoria_nuevos_valores(self):
        p1 = {1: {'tono': 'Neutro', 'sub_tema': 'x', 'tipo': 'Ranking',
                  'genero': 'Reportaje'}}
        p2 = {1: {'tono': 'Neutro', 'sub_tema': 'x', 'tipo': 'Ranking',
                  'genero': 'Reportaje'}}
        out = A._voto_mayoria([p1, p2], [1])
        self.assertEqual(out[1]['tipo'], 'Ranking')
        self.assertEqual(out[1]['genero'], 'Reportaje')

    def test_voto_mayoria_empate_tipo_cae_a_default(self):
        p1 = {1: {'tono': 'Neutro', 'sub_tema': 'x', 'tipo': 'Ranking'}}
        p2 = {1: {'tono': 'Neutro', 'sub_tema': 'x',
                  'tipo': 'Información general'}}
        out = A._voto_mayoria([p1, p2], [1])
        self.assertEqual(out[1]['tipo'], 'Información general')


class TestRescateRanking(unittest.TestCase):
    def test_titulo_ranking_con_marca(self):
        rows = [{'Título': 'Bogotá sube en el ranking de ciudades',
                 'CuerpoEs': 'La Alcaldía de Bogotá celebra el puesto.'}]
        et = {1: {'tipo': 'Información general'}}
        n = A.aplicar_tipo_por_ranking(rows, {0: 1}, et, {}, BRAND, ALIASES)
        self.assertEqual(n, 1)
        self.assertEqual(et[1]['tipo'], 'Ranking')

    def test_ranking_no_pisa_institucional(self):
        rows = [{'Título': 'Ranking de ciudades: Bogotá primera',
                 'CuerpoEs': 'La Alcaldía de Bogotá celebra.'}]
        et = {1: {'tipo': 'Institucional'}}
        n = A.aplicar_tipo_por_ranking(rows, {0: 1}, et, {}, BRAND, ALIASES)
        self.assertEqual(n, 0)
        self.assertEqual(et[1]['tipo'], 'Institucional')

    def test_ranking_sin_marca_no_dispara(self):
        rows = [{'Título': 'Ranking de ciudades del mundo',
                 'CuerpoEs': 'Medellín lidera el listado.'}]
        et = {1: {'tipo': 'Información general'}}
        n = A.aplicar_tipo_por_ranking(rows, {0: 1}, et, {}, BRAND, ALIASES)
        self.assertEqual(n, 0)
        self.assertEqual(et[1]['tipo'], 'Información general')


class TestGeneroRescates(unittest.TestCase):
    def _seccion(self, sec, genero='Noticia'):
        rows = [{'Sección - Programa': sec}]
        et = {1: {'genero': genero}}
        A.aplicar_genero_por_seccion(
            rows, {0: 1}, et, {'seccion_programa': 'Sección - Programa'})
        return et[1]['genero']

    def _url(self, url, genero='Noticia'):
        rows = [{'GÉNERO': genero, 'Tipo de Medio': 'Internet',
                 'URL Nota': url}]
        aplicar_genero_por_url(rows)
        return rows[0]['GÉNERO']

    def test_url_editorial_ya_no_es_opinion(self):
        self.assertEqual(
            self._url('https://www.ejemplo.com/editorial/nota'), 'Editorial')

    def test_url_opinion_sigue(self):
        self.assertEqual(
            self._url('https://www.elpilon.com.co/opinion/columna'),
            'Opinión')

    def test_url_reportaje(self):
        self.assertEqual(
            self._url('https://www.ejemplo.com/reportaje/especial-x'),
            'Reportaje')
        self.assertEqual(
            self._url('https://www.ejemplo.com/especial/investigacion'),
            'Reportaje')

    def test_seccion_editorial_y_reportaje(self):
        self.assertEqual(self._seccion('Editorial'), 'Editorial')
        self.assertEqual(self._seccion('Reportaje especial'), 'Reportaje')
        self.assertEqual(self._seccion('Investigación'), 'Reportaje')

    def test_rescate_no_sobrescribe(self):
        self.assertEqual(self._seccion('Editorial', 'Entrevista'),
                         'Entrevista')
        self.assertEqual(
            self._url('https://www.ejemplo.com/editorial/nota', 'Opinión'),
            'Opinión')

    def test_guardia_entrevista_vigente(self):
        g, et = grupo(1, 'Charla con el secretario',
                      'El secretario habló del plan.', 'Neutro',
                      genero='Entrevista')
        A.aplicar_guardia_genero([g], et)
        self.assertEqual(et[1]['genero'], 'Noticia')


class TestTonoDistrito(unittest.TestCase):
    def test_plantacion_sin_critica_desde_neutro(self):
        self.assertEqual(distrito(
            1, 'Alcaldía de Bogotá siembra árboles',
            'La Alcaldía de Bogotá inició la plantación de árboles en el '
            'sur de la ciudad.', 'Neutro'), 'Positivo')

    def test_zonas_seguras_sin_critica(self):
        self.assertEqual(distrito(
            1, 'Alcaldía de Bogotá anuncia zonas seguras',
            'La Alcaldía de Bogotá anunció nuevas zonas seguras con '
            'acompañamiento policial.', 'Neutro'), 'Positivo')

    def test_hecho_bueno_mas_critica_baja_desde_positivo(self):
        self.assertEqual(distrito(
            1, 'Alcaldía de Bogotá inaugura parque',
            'La Alcaldía de Bogotá inauguró el parque, pero vecinos '
            'cuestionaron a la Alcaldía de Bogotá por los retrasos de '
            'la obra.', 'Positivo'), 'Neutro')

    def test_hecho_bueno_mas_critica_baja_desde_negativo(self):
        self.assertEqual(distrito(
            1, 'Alcaldía de Bogotá inaugura parque',
            'La Alcaldía de Bogotá inauguró el parque, pero vecinos '
            'denunciaron a la Alcaldía de Bogotá por sobrecostos.',
            'Negativo'), 'Neutro')

    def test_solo_criticas_sin_hecho_bueno_intacto(self):
        self.assertEqual(distrito(
            1, 'Demandas contra la Alcaldía de Bogotá',
            'Vecinos demandaron a la Alcaldía de Bogotá y la acusaron de '
            'incumplir sus promesas.', 'Negativo'), 'Negativo')

    def test_referencial_sin_protagonismo_intacto(self):
        # Hay hecho bueno ("programa") pero una sola mención: sin
        # protagonismo no se toca.
        self.assertEqual(distrito(
            1, 'Concierto en Bogotá',
            'El concierto se realizó en Bogotá. La Alcaldía de Bogotá '
            'aparece mencionada al pasar en una nota al pie sobre el '
            'programa de conciertos.', 'Neutro'), 'Neutro')

    def test_corrupcion_bloquea_subida(self):
        self.assertEqual(distrito(
            1, 'Alcaldía de Bogotá inaugura parque en el sur',
            'La Alcaldía de Bogotá inauguró un parque con zonas seguras '
            'para los niños. El evento se realizó sin contratiempos. En '
            'otro tema, la Fiscalía investiga un caso de corrupción en '
            'una entidad nacional, sin relación con la ciudad.',
            'Negativo'), 'Negativo')

    def test_tragedia_pegajosa_intacta(self):
        self.assertEqual(distrito(
            1, 'Alcaldía de Bogotá entrega ayudas',
            'La Alcaldía de Bogotá entregó ayudas tras la tragedia. El '
            'secretario anunció un programa de acompañamiento.',
            'Neutro', pegajoso=True), 'Neutro')

    def test_decreto_sin_beneficio_intacto(self):
        # Protagonismo sí, pero sin hecho bueno: no se toca.
        self.assertEqual(distrito(
            1, 'Alcaldía de Bogotá expide decreto de horarios',
            'La Alcaldía de Bogotá expidió el decreto que regula los '
            'horarios de los establecimientos.', 'Neutro'), 'Neutro')

    def test_decreto_beneficio_de_alcaldia_positivo(self):
        self.assertEqual(distrito(
            1, 'Decreto de la Alcaldía de Bogotá crea zonas seguras',
            'La Alcaldía de Bogotá expidió el decreto que crea zonas '
            'seguras en la ciudad.', 'Neutro'), 'Positivo')

    def test_decreto_beneficio_no_de_alcaldia_neutro(self):
        self.assertEqual(distrito(
            1, 'Decreto del Gobierno Nacional crea programa de subsidios',
            'El Gobierno Nacional expidió el decreto que crea un programa '
            'de subsidios para vivienda. La norma aplicará en todo el '
            'país desde enero. Por su parte, la Alcaldía de Bogotá '
            'informó que acompañará la implementación local del programa '
            'y destacó sus beneficios. La Alcaldía de Bogotá señaló que '
            'el programa es positivo.', 'Neutro'), 'Neutro')


class TestRegresionTransmilenio(unittest.TestCase):
    TITULO = 'TransMilenio y Alcaldía de Bogotá acompañarán a asistentes'

    def test_stems_acompan_facilit(self):
        nt = A.nz('acompañará a los asistentes para facilitar los '
                  'desplazamientos')
        self.assertTrue(A._hecho_bueno_distrito(nt))

    def test_fragmento_no_es_critica_dirigida(self):
        self.assertFalse(A._critica_dirigida(
            FRAG_TRANSMILENIO, BRAND, ALIASES))
        self.assertEqual(
            [m.group(0) for m in A.CRITICA_PAT.finditer(FRAG_TRANSMILENIO)],
            [])

    def test_desde_negativo_a_positivo(self):
        self.assertEqual(distrito(
            1, self.TITULO, FRAG_TRANSMILENIO, 'Negativo'), 'Positivo')

    def test_desde_neutro_a_positivo(self):
        self.assertEqual(distrito(
            1, self.TITULO, FRAG_TRANSMILENIO, 'Neutro'), 'Positivo')


class TestFlagsApagados(unittest.TestCase):
    def test_prompt_sin_flags_no_trae_distrito_ni_tipo_genero(self):
        cfg = {'brand': BRAND, 'voceros': VOCEROS, 'aliases': ALIASES}
        txt = A.prompt_sistema(cfg)
        self.assertNotIn('DISTRITO', txt)
        self.assertNotIn('REGLA DE TIPO Y GÉNERO', txt)

    def test_prompt_con_flag_distrito_si(self):
        cfg = {'brand': BRAND, 'voceros': VOCEROS, 'aliases': ALIASES,
               'tono_distrito_positivo': True}
        self.assertIn('DISTRITO', A.prompt_sistema(cfg))

    def test_rescates_no_tocan_filas_sin_genero(self):
        rows = [{'GÉNERO': '', 'Tipo de Medio': 'Internet',
                 'URL Nota': 'https://www.ejemplo.com/editorial/nota'}]
        aplicar_genero_por_url(rows)
        self.assertEqual(rows[0]['GÉNERO'], '')
        rows2 = [{'Sección - Programa': 'Editorial'}]
        et = {1: {}}
        A.aplicar_genero_por_seccion(
            rows2, {0: 1}, et, {'seccion_programa': 'Sección - Programa'})
        self.assertNotIn('genero', et[1])
        rows3 = [{'Título': 'Ranking de ciudades',
                  'CuerpoEs': 'La Alcaldía de Bogotá celebra.'}]
        et3 = {1: {}}
        n = A.aplicar_tipo_por_ranking(rows3, {0: 1}, et3, {}, BRAND, ALIASES)
        self.assertEqual(n, 0)


if __name__ == '__main__':
    unittest.main()
