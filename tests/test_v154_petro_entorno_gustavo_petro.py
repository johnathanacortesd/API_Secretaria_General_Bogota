"""v1.54 (dossier 2026-11-25 17:23, nota 62163985): «Crítica al expresidente
Gustavo Petro» venía de la hoja del boletín de la 1:00 p.m. (leída como
corrección manual) y la regla de Petro no la tocaba. Debe quedar «Entorno
Gustavo Petro», igual que el resto de subtemas sobre Petro."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import analyzer_tono_tema as az

KM = {'titulo': 'Título'}
VOC = ['Carlos Fernando Galán', 'Galán', 'el alcalde']
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_perfil_usa_entorno_gustavo_petro():
    with open(os.path.join(RAIZ, 'clientes', 'secretaria_general_de_la_alcaldia_de_bogota.json'),
              encoding='utf-8') as f:
        sp = json.load(f)['subtemas_politicos']
    assert sp['petro_general'] == 'Entorno Gustavo Petro'


def test_correccion_de_la_hoja_sobre_petro_pasa_a_entorno_gustavo_petro():
    rows = [{'Título': 'La vocación guerrillera del expresidente Gustavo Petro',
             'Subtema_IA': 'Crítica al expresidente Gustavo Petro', 'Tono_IA': 'Negativo',
             'TIPO': 'Opinión de terceros', '_correccion_manual': True, '_tono_manual': True},
            {'Título': 'Galán responde a Petro por el metro', '_correccion_manual': True,
             'Subtema_IA': 'Respuesta de Galán a Petro por el metro', 'Tono_IA': 'Neutro'}]
    assert az.aplicar_entorno_petro(rows, KM, 'Entorno Gustavo Petro', voceros=VOC, con_tipo=True) == [0]
    assert (rows[0]['Subtema_IA'], rows[0]['Tono_IA'], rows[0]['TIPO']) == \
        ('Entorno Gustavo Petro', 'Neutro', 'Información general')
    assert rows[1]['Subtema_IA'] == 'Respuesta de Galán a Petro por el metro'
