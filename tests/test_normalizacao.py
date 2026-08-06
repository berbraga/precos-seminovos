import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml_coleta import CASOS_TESTE, descartar_outliers, normalizar


def test_casos_titulo():
    for titulo, modelo_esperado, storage_esperado in CASOS_TESTE:
        modelo, storage = normalizar(titulo)
        assert (modelo, storage) == (modelo_esperado, storage_esperado), titulo


def test_descartar_outliers():
    amostra = [1000, 1100, 1050, 1080, 120, 9000]
    assert descartar_outliers(amostra) == [1000, 1100, 1050, 1080]


def test_descartar_outliers_mantem_original_se_zerar():
    amostra = [10, 10, 10, 10000]
    resultado = descartar_outliers(amostra)
    assert len(resultado) >= 1
