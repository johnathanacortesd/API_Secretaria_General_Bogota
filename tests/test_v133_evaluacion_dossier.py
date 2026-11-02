# -*- coding: utf-8 -*-
"""v1.33: correcciones salidas de la evaluación de un dossier real de
Secretaría (189 notas, 2026-11-02)."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_openai_stub = types.ModuleType('openai')
_openai_stub.OpenAI = object
sys.modules.setdefault('openai', _openai_stub)

import analyzer_tono_tema as az
import perfil_cliente
from pipeline import texto_con_minimo

P = perfil_cliente.cargar_perfil('secretaria_general_de_la_alcaldia_de_bogota')
B, A, V = P['brand'], P['aliases'], P['voceros']


class TestTextoCreditoAlFinal(unittest.TestCase):
    RES = ('Decretan restricciones. Las autoridades imponen medidas transitorias para regular el '
           'tránsito nocturno. De este modo, las instituciones del Estado garantizan la protección '
           'de la vida y el orden en las vías públicas. Fuente: Alcaldía de Bogotá.')

    def test_toma_oraciones_anteriores_literales(self):
        out = texto_con_minimo('Fuente: Alcaldía de Bogotá', self.RES)
        self.assertGreater(len(out.split()), 15)
        self.assertTrue(out.endswith('Fuente: Alcaldía de Bogotá'))
        self.assertIn('De este modo, las instituciones del Estado', out)
        self.assertTrue(set(out.split()) <= set(self.RES.split()) | {'Bogotá'})


class TestEnmascarado(unittest.TestCase):
    def _m(self, t):
        return az._enmascarar_menciones_ajenas(t, V)

    def test_cargo_y_candidaturas(self):
        for t in ('posible aspirante a la Alcaldía de Bogotá',
                  'buscó ser candidato de su partido a la Alcaldía de Bogotá',
                  'cuando Petro era alcalde de Bogotá',
                  'durante la administración de Gustavo Petro en la Alcaldía de Bogotá',
                  'se elija al sucesor del alcalde Galán'):
            self.assertIn('XAJENAX', self._m(t), t)
            self.assertNotIn('Alcaldía de Bogotá', self._m(t).replace('XAJENAX', ''), t)

    def test_otros_alcaldes_y_homonimos(self):
        self.assertIn('XAJENAX', self._m('En Bucaramanga, el alcalde Cristian Portilla reportó'))
        self.assertIn('XAJENAX', self._m('el alcalde de Medellín anunció'))
        self.assertIn('XAJENAX', self._m('Juan Manuel Galán envió condolencias'))

    def test_vocero_real_no_se_toca(self):
        for t in ('El alcalde Carlos Fernando Galán entregó buses', 'Según Galán, la obra avanza',
                  'la Alcaldía de Bogotá presentó el plan', 'el alcalde de Bogotá anunció'):
            self.assertNotIn('XAJENAX', self._m(t), t)


def _g(tit, ctx, texto=''):
    return {'grupo': 1, 'titulo': tit, 'contexto': ctx, 'texto': texto or ctx}


class TestReglasSoloGestion(unittest.TestCase):
    def test_condolencias_del_alcalde_son_neutro(self):
        g = _g('Muere Antonio Navarro Wolff a los 78 años',
               'El alcalde de Bogotá, Carlos Fernando Galán, lo recordó como un ejemplo de '
               'reconciliación. Galán afirmó que fue un referente.')
        et = {1: {'tono': 'Positivo', 'sub_tema': 'x'}}
        az.aplicar_regla_protocolaria([g], et, B, A, voceros=V)
        self.assertEqual(et[1]['tono'], 'Neutro')

    def test_gestion_en_noticia_de_duelo_sigue_positiva(self):
        g = _g('Bogotá decreta duelo por la muerte de Navarro',
               'El alcalde Carlos Fernando Galán anunció un homenaje y la entrega de una placa.')
        et = {1: {'tono': 'Positivo', 'sub_tema': 'x'}}
        az.aplicar_regla_protocolaria([g], et, B, A, voceros=V)
        self.assertEqual(et[1]['tono'], 'Positivo')

    def test_declaracion_no_sube_con_solo_gestion(self):
        g = _g('Galán opina sobre el clima', 'El alcalde Carlos Fernando Galán dijo que el clima es agradable.')
        et = {1: {'tono': 'Neutro', 'sub_tema': 'x'}}
        az.aplicar_guarda_positiva([g], et, B, A, voceros=V, solo_gestion=True)
        self.assertEqual(et[1]['tono'], 'Neutro')

    def test_opinion_de_terceros_con_preocupacion_no_es_positivo(self):
        # Sin la marca en la oración crítica: Neutro (con la marca: Negativo,
        # ver TestReglasEtiquetasManuales).
        g = _g('Edil: preocupa el futuro de la URI de Suba',
               'La Alcaldía de Bogotá construye la URI. El cabildante dijo que preocupan los retrasos.')
        et = {1: {'tono': 'Positivo', 'sub_tema': 'x', 'tipo': 'Opinión de terceros'}}
        az.aplicar_regla_opinion_terceros([g], et, B, A, voceros=V)
        self.assertEqual(et[1]['tono'], 'Neutro')

    def test_distrito_no_sube_opinion_de_terceros(self):
        g = _g('Edil habla del proyecto de la URI',
               'La Alcaldía de Bogotá ejecuta el proyecto de la URI en Suba, dijo el edil.')
        et = {1: {'tono': 'Neutro', 'sub_tema': 'x', 'tipo': 'Opinión de terceros'}}
        az.aplicar_regla_distrito([g], et, B, A, voceros=V)
        self.assertEqual(et[1]['tono'], 'Neutro')


class TestVariantesRotulo(unittest.TestCase):
    def test_variantes_del_mismo_hecho_se_unen(self):
        ctx = 'Murió Antonio Navarro Wolff, dijo el alcalde Galán.'
        rows = [{'Título': 'Muere Antonio Navarro Wolff', 'CuerpoEs': ctx, 'Contexto analizado': ctx},
                {'Título': 'Fallece Antonio Navarro Wolff a los 78', 'CuerpoEs': ctx, 'Contexto analizado': ctx},
                {'Título': 'Adiós a Navarro Wolff', 'CuerpoEs': ctx, 'Contexto analizado': ctx}]
        mapa = {0: 1, 1: 2, 2: 3}
        et = {1: {'sub_tema': 'Fallecimiento de Antonio Navarro Wolff'},
              2: {'sub_tema': 'Fallecimiento de Antonio Navarro Wolff'},
              3: {'sub_tema': 'Fallecimiento de Antonio Navarro'}}
        aj = az.unificar_variantes_rotulo_estricto(rows, mapa, et, {}, {'titulo': 'Título'},
                                                   brand=B, aliases=A)
        self.assertEqual(aj.get(2), 'Fallecimiento de Antonio Navarro Wolff')

    def test_rotulos_distintos_no_se_unen(self):
        rows = [{'Título': 'Pico y placa festivo', 'CuerpoEs': 'pico y placa', 'Contexto analizado': 'pico y placa regional'},
                {'Título': 'Noche de Museos', 'CuerpoEs': 'museos', 'Contexto analizado': 'noche de museos gratis'}]
        et = {1: {'sub_tema': 'Pico y placa festivo'}, 2: {'sub_tema': 'Noche de Museos gratis'}}
        self.assertEqual(az.unificar_variantes_rotulo_estricto(rows, {0: 1, 1: 2}, et, {}, {'titulo': 'Título'},
                                                               brand=B, aliases=A), {})


class TestReglasEtiquetasManuales(unittest.TestCase):
    """Calibradas con 132 notas etiquetadas a mano por el usuario."""

    def test_medida_restrictiva_es_neutro(self):
        g = _g('Pico y placa regional en Bogotá este lunes',
               'De acuerdo con la información publicada por la Alcaldía de Bogotá, rige la medida.')
        et = {1: {'tono': 'Positivo', 'sub_tema': 'x'}}
        az.aplicar_regla_medida_restrictiva([g], et)
        self.assertEqual(et[1]['tono'], 'Neutro')

    def test_secretaria_distrital_que_gestiona_es_positivo(self):
        g = _g('Nuevo programa para mujeres emprendedoras',
               'Fuente: Alcaldía de Bogotá. La Secretaría Distrital de la Mujer lanzó un programa de becas.')
        et = {1: {'tono': 'Neutro', 'sub_tema': 'x'}}
        az.aplicar_regla_secretarias_distritales([g], et, B, A, voceros=V)
        self.assertEqual(et[1]['tono'], 'Positivo')

    def test_solo_credito_sigue_neutro(self):
        g = _g('Corredor pedagógico con material reutilizado', 'Fuente: Alcaldía de Bogotá')
        et = {1: {'tono': 'Neutro', 'sub_tema': 'x'}}
        az.aplicar_regla_secretarias_distritales([g], et, B, A, voceros=V)
        self.assertEqual(et[1]['tono'], 'Neutro')

    def test_cargo_historico_de_secretario_no_cuenta(self):
        g = _g('¿Quién era Antonio Navarro?',
               'Fue secretario de Gobierno de Gustavo Petro y luego presentó su candidatura al Senado.')
        et = {1: {'tono': 'Neutro', 'sub_tema': 'x'}}
        az.aplicar_regla_secretarias_distritales([g], et, B, A, voceros=V)
        self.assertEqual(et[1]['tono'], 'Neutro')

    def test_titular_bogota_nombra_es_positivo(self):
        g = _g('Bogotá nombra nueva líder social', 'Juliana Sánchez será la nueva funcionaria.')
        et = {1: {'tono': 'Neutro', 'sub_tema': 'x'}}
        az.aplicar_regla_secretarias_distritales([g], et, B, A, voceros=V)
        self.assertEqual(et[1]['tono'], 'Positivo')

    def test_critica_de_tercero_a_la_marca_es_negativo(self):
        g = _g('Edil: preocupa el futuro de la URI de Suba',
               'El cabildante señaló que la responsabilidad recae en el gobierno del alcalde Galán.')
        et = {1: {'tono': 'Positivo', 'sub_tema': 'x', 'tipo': 'Opinión de terceros'}}
        az.aplicar_regla_opinion_terceros([g], et, B, A, voceros=V)
        self.assertEqual(et[1]['tono'], 'Negativo')

    def test_tipo_por_actor(self):
        gs = [_g('Plan retorno en Bogotá hoy', 'Miles de vehículos ingresarán.'),
              _g('Muere Navarro', 'El alcalde de Bogotá, Carlos Fernando Galán, envió un mensaje de condolencia.'),
              _g('Quién era Navarro', 'En 2012, cuando Petro llegó a la Alcaldía de Bogotá, nombró a Navarro.')]
        for k, g in enumerate(gs, 1):
            g['grupo'] = k
        et = {1: {'tipo': 'Proyectos y programas'}, 2: {'tipo': 'Información general'},
              3: {'tipo': 'Institucional'}}
        az.aplicar_tipo_por_actor(gs, et, B, A, voceros=V)
        self.assertEqual([et[k]['tipo'] for k in (1, 2, 3)],
                         ['Institucional', 'Institucional', 'Información general'])

    def test_un_subtema_por_evento_grande(self):
        titulos = ['Murió Antonio Navarro Wolff a los 78 años', '¿Quién era Antonio Navarro Wolff?',
                   'Así despiden a Antonio Navarro Wolff', 'Antonio Navarro Wolff: su legado']
        subs = ['Muerte de Antonio Navarro Wolff', 'Trayectoria política de Antonio Navarro',
                'Muerte de Antonio Navarro Wolff', 'Legado de Navarro Wolff']
        ctx = 'Antonio Navarro Wolff murió; su muerte conmovió al país.'
        rows = [{'Título': t, 'CuerpoEs': ctx, 'Contexto analizado': ctx} for t in titulos]
        et = {i + 1: {'sub_tema': s_} for i, s_ in enumerate(subs)}
        aj = az.unificar_por_asunto_titular(rows, {i: i + 1 for i in range(4)}, et, {},
                                            {'titulo': 'Título'}, brand=B, aliases=A, voceros=V)
        finales = {aj.get(i) or subs[i] for i in range(4)}
        self.assertEqual(finales, {'Muerte de Antonio Navarro Wolff'})

    def test_asuntos_distintos_no_se_mezclan(self):
        titulos = ['Pico y placa regional este lunes', 'Pico y placa regional: horarios',
                   'Pico y placa regional y reversible', 'Noche de Museos abre gratis']
        subs = ['Pico y placa festivo', 'Pico y placa festivo', 'Horarios del pico y placa', 'Noche de Museos gratis']
        rows = [{'Título': t, 'CuerpoEs': t, 'Contexto analizado': t} for t in titulos]
        et = {i + 1: {'sub_tema': s_} for i, s_ in enumerate(subs)}
        aj = az.unificar_por_asunto_titular(rows, {i: i + 1 for i in range(4)}, et, {},
                                            {'titulo': 'Título'}, brand=B, aliases=A, voceros=V)
        self.assertNotIn(3, aj)


class TestPerfil(unittest.TestCase):
    def test_flag_y_criterio(self):
        self.assertTrue(P['tono_solo_gestion'])
        self.assertTrue(P['tipo_por_actor'])
        self.assertNotIn('declaración que los deja bien', P['criterio_custom'])
        self.assertIn('condolencias', P['criterio_custom'])
        self.assertEqual(perfil_cliente.validar_perfil(P), [])


if __name__ == '__main__':
    unittest.main()
