"""v1.53 (dossier 2026-11-25 17:23): ningún subtema de una palabra suelta
(«Militarización») ni extracto del titular («Siglo siendo la casa del
Congreso») llega al Excel: se reconstruye desde el texto de la nota."""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
import analyzer_tono_tema as az

KM = {'titulo': 'Título'}
CTX_CAP = ('Al cumplir cien años de estar sirviendo de sede de la democracia colombiana, el '
           'Congreso de la República sesiona hoy para conmemorar el centenario del Capitolio Nacional.')
CTX_ORD = ('El alcalde de Bogotá, Carlos Fernando Galán, ha puesto el acento en la coordinación entre '
           'autoridades y el respaldo a la Fuerza Pública para mantener el orden público.')


def _rows():
    return [
        {'Título': 'BALANCE DEL ORDEN PÚBLICO EN COLOMBIA', 'Subtema_IA': 'Militarización',
         'Contexto analizado': CTX_ORD},
        {'Título': 'BALANCE DEL ORDEN PÚBLICO EN COLOMBIA', 'Subtema_IA': 'Militarización',
         'Contexto analizado': CTX_ORD},
        {'Título': 'El Capitolio Nacional un siglo siendo la casa del Congreso',
         'Subtema_IA': 'Siglo siendo la casa del Congreso', 'Contexto analizado': CTX_CAP},
        {'Título': 'Novedades en el caso de Miguel Uribe Turbay', 'Subtema_IA': 'Entorno político',
         '_subtema_politico': 'petro_general'},
        {'Título': 'Marchas 25N en Bogotá: prográmese, habrá afectaciones en la movilidad',
         'Subtema_IA': 'Marchas del 25N con afectaciones viales'},
        {'Título': 'Monserrate tendrá más de 25 actividades', 'Subtema_IA': 'Navidad Andina en Monserrate'},
    ]


def test_detecta_palabra_suelta_y_extracto_del_titulo():
    assert az.problemas_subtema_construido('Militarización', 'BALANCE DEL ORDEN PÚBLICO EN COLOMBIA')
    assert az.problemas_subtema_construido(
        'Siglo siendo la casa del Congreso', 'El Capitolio Nacional un siglo siendo la casa del Congreso')
    assert not az.problemas_subtema_construido('Marchas del 25N con afectaciones viales', 'Marchas 25N')
    assert not az.problemas_subtema_construido('Entorno político', 'x', permitidos=['entorno politico'])


def test_reconstruye_desde_el_texto_y_conserva_lo_valido():
    rows = _rows()
    pedidos = []

    def fake(lote):
        pedidos.append(lote)
        out = {}
        for f in lote:
            if 'Militar' in f['sub_tema']:
                out[f['id']] = 'Llamado de Galán a reforzar el orden público'
            else:
                out[f['id']] = 'Centenario del Capitolio como sede del Congreso'
        return out
    r = az.guarda_final_subtema_construido(rows, KM, {'motor': 'haiku'}, reformular_fn=fake)
    assert len(pedidos) == 1 and len(pedidos[0]) == 2          # un pedido por rótulo malo
    assert rows[0]['Subtema_IA'] == rows[1]['Subtema_IA'] == 'Llamado de Galán a reforzar el orden público'
    assert rows[2]['Subtema_IA'] == 'Centenario del Capitolio como sede del Congreso'
    assert rows[3]['Subtema_IA'] == 'Entorno político'
    assert rows[4]['Subtema_IA'] == 'Marchas del 25N con afectaciones viales'
    assert rows[5]['Subtema_IA'] == 'Navidad Andina en Monserrate'
    assert r['reconstruidos'] == 3 and not r['sobrevivientes']


def test_reintenta_si_la_propuesta_vuelve_a_ser_mala():
    rows = _rows()[2:3]
    llamadas = []

    def fake(lote):
        llamadas.append(lote)
        return {lote[0]['id']: 'Congreso' if len(llamadas) == 1
                else 'Centenario del Capitolio como sede del Congreso'}
    az.guarda_final_subtema_construido(rows, KM, {'motor': 'haiku'}, reformular_fn=fake)
    assert len(llamadas) == 2
    assert any('se rechazó' in p for p in llamadas[1][0]['problemas'])
    assert rows[0]['Subtema_IA'] == 'Centenario del Capitolio como sede del Congreso'


def test_sin_respuesta_no_inventa_y_reporta():
    rows = _rows()[:1]
    r = az.guarda_final_subtema_construido(rows, KM, {'motor': 'openai'}, reformular_fn=lambda l: {})
    assert rows[0]['Subtema_IA'] == 'Militarización'
    assert r['sobrevivientes'] == [{'fila': 0, 'subtema': 'Militarización'}]
