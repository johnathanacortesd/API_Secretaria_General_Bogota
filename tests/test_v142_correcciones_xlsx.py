import io, os, sys, types, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_s = types.ModuleType('openai'); _s.OpenAI = object; sys.modules.setdefault('openai', _s)
from openpyxl import Workbook
import memoria_cliente as mc
import analyzer_tono_tema as az

BRAND = 'Secretaría General de la Alcaldía de Bogotá'
KM = {'titulo': 'Título'}
REGLAS = {'aspirantes': 'Aspirantes Alcaldía de Bogotá', 'petro': 'Entorno Gustavo Petro'}
TXT_A = ('La Empresa Metro de Bogotá abrió la licitación de la segunda línea del metro, que irá '
         'hacia Suba y Engativá y tendrá 15,5 kilómetros de longitud y once estaciones elevadas.')


def _xlsx(filas, cab=('ID Noticia', 'Título', 'Tono_IA', 'Subtema_IA', 'TIPO', 'texto')):
    wb = Workbook(); ws = wb.active
    ws.append(list(cab))
    for f in filas:
        ws.append(list(f))
    b = io.BytesIO(); wb.save(b); return b.getvalue()


def _extra(tmp_path):
    return {'historial_dir': str(tmp_path)}


def test_importa_y_retoma_subtema_y_tono(tmp_path):
    ex = _extra(tmp_path)
    x = _xlsx([(1, 'Abren licitación de la línea 2 del metro', 'Positivo',
                'Licitación de la línea 2 del metro', 'Gestión', TXT_A),
               (2, 'Nota duplicada', 'Duplicada', 'x', '', ''),
               (3, 'Sin subtema', 'Neutro', '', '', '')])
    assert mc.importar_correcciones_xlsx(BRAND, x, ex) == 1
    ent = mc.cargar_subtemas(BRAND, ex)
    assert ent[0]['manual'] and ent[0]['tono'] == 'Positivo'
    # Próxima corrida: la misma nota con otro titular (mismo texto) y otra igual.
    rows = [{'Título': 'Metro: arranca proceso para la segunda línea', 'CuerpoEs': TXT_A,
             'Tono_IA': 'Neutro', 'Subtema_IA': 'Metro de Bogotá'},
            {'Título': 'Abren licitación de la línea 2 del metro', 'CuerpoEs': 'otro',
             'Tono_IA': 'Neutro', 'Subtema_IA': 'Segunda línea'}]
    az.anclar_subtemas_previos(rows, KM, mc.cargar_subtemas(BRAND, ex))
    for r in rows:
        assert r['Subtema_IA'] == 'Licitación de la línea 2 del metro'
        assert r['Tono_IA'] == 'Positivo'
    # La corrida guarda su resultado: no pisa la corrección manual.
    mc.guardar_subtemas(BRAND, [mc._entrada('Abren licitación de la línea 2 del metro', TXT_A,
                                            'Otro rótulo')], ex)
    e = [e for e in mc.cargar_subtemas(BRAND, ex) if e['titulo'].startswith('Abren')][0]
    assert e['subtema'] == 'Licitación de la línea 2 del metro' and e['manual']


def test_manual_manda_sobre_reglas_posteriores(tmp_path):
    ex = _extra(tmp_path)
    tit = 'Cuando Petro era alcalde: la crisis de las basuras'
    mc.importar_correcciones_xlsx(BRAND, _xlsx([(1, tit, 'Negativo', 'Modelo de aseo', '', '')]), ex)
    rows = [{'Título': tit, 'Tono_IA': 'Neutro', 'Subtema_IA': 'x', 'TIPO': 'Gestión'}]
    az.anclar_subtemas_previos(rows, KM, mc.cargar_subtemas(BRAND, ex))
    az.aplicar_subtemas_politicos(rows, KM, REGLAS)
    az.aplicar_gestion_vocero_final(rows, KM, BRAND, voceros=['Galán'])
    assert (rows[0]['Subtema_IA'], rows[0]['Tono_IA']) == ('Modelo de aseo', 'Negativo')


def test_cabecera_subtema_y_sin_tono(tmp_path):
    ex = _extra(tmp_path)
    x = _xlsx([('Galán inaugura colegio en Bosa', 'Colegio en Bosa')], cab=('Título', 'Subtema'))
    assert mc.importar_correcciones_xlsx(BRAND, x, ex) == 1
    assert 'tono' not in mc.cargar_subtemas(BRAND, ex)[0]


def test_xlsx_sin_columnas(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        mc.importar_correcciones_xlsx(BRAND, _xlsx([('a',)], cab=('Medio',)), _extra(tmp_path))


def test_exportar_importar_conserva_manual(tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.mkdir(); b.mkdir()
    mc.importar_correcciones_xlsx(BRAND, _xlsx([(1, 'Titular uno de prueba', 'Negativo', 'Rótulo', '', '')]),
                                  _extra(a))
    data = mc.exportar_subtemas(BRAND, _extra(a))
    assert mc.importar_subtemas(BRAND, data, _extra(b)) == 1
    e = mc.cargar_subtemas(BRAND, _extra(b))[0]
    assert e['manual'] and e['tono'] == 'Negativo'


def test_correcciones_de_la_hoja_por_horario():
    from datetime import datetime, timedelta
    hoy = datetime.now().strftime('%d/%m/%Y')
    ayer = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
    viejo = (datetime.now() - timedelta(days=40)).strftime('%d/%m/%Y')
    cab = ['ID', 'Fecha', 'Medio', 'Título', 'Tono', 'Subtema', 'TIPO', 'texto',
           'FECHA INFORME', 'HORA B']
    T = 'Galán presentó obras de la autopista Norte'
    filas = [
        ['1', '', 'X', T, 'Neutro', 'Autopista Norte', '', '', ayer, '6:00 p.m.'],
        ['2', '', 'X', T, 'Positivo', 'Ampliación de la autopista Norte', '', '', hoy, '1:00 p.m.'],
        ['3', '', 'X', 'Nota de hace un mes', 'Neutro', 'Viejo', '', '', viejo, '1:00 p.m.'],
        ['4', '', 'X', 'Otra', 'Duplicada', 'x', '', '', hoy, '1:00 p.m.'],
        ['5', '', 'X', 'No aplica nota', 'No aplica', 'No aplica', '', '', hoy, '1:00 p.m.'],
        ['6', '', 'X', 'Sin tono', '', 'Metro de Bogotá', '', '', hoy, '1:00 p.m.'],
        ['7', '', 'X', 'Subtema no aplica', 'Neutro', 'No aplica', '', '', hoy, '1:00 p.m.'],
    ]
    corr = mc.correcciones_de_tabla(cab, filas)
    assert len(corr) == 1
    assert corr[0]['subtema'] == 'Ampliación de la autopista Norte' and corr[0]['tono'] == 'Positivo'
    assert corr[0]['fecha'].endswith('13:00:00')
    # La memoria automática pierde ante la hoja.
    auto = [dict(mc._entrada(T, '', 'Obras viales'), fecha=datetime.now().isoformat())]
    ent = mc.fusionar_correcciones(auto, corr)
    rows = [{'Título': T, 'Tono_IA': 'Neutro', 'Subtema_IA': 'Obras viales'}]
    az.anclar_subtemas_previos(rows, KM, ent)
    assert (rows[0]['Subtema_IA'], rows[0]['Tono_IA']) == ('Ampliación de la autopista Norte', 'Positivo')


def test_fecha_boletin():
    assert mc._fecha_boletin('2026-11-21', '6:00 p.m.') == '2026-11-21T18:00:00'
    assert mc._fecha_boletin('21/11/2026', '1:00 p.m.') == '2026-11-21T13:00:00'
    assert mc._fecha_boletin('', '1:00 p.m.') == ''
