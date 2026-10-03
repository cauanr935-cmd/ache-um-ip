"""Raiz do projeto (pasta que contem data/, config/, docs/). Configuravel para o Colab/Drive.

Ordem: variavel de ambiente ACHE_RAIZ > pasta pai de src/. Defina ANTES de importar os modulos
(pipeline.configurar(raiz) faz isso e limpa os modulos ja importados).
"""
import os
from pathlib import Path

RAIZ = Path(os.environ.get("ACHE_RAIZ") or Path(__file__).resolve().parent.parent).expanduser().resolve()
