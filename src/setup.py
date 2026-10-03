"""T0.3 - Setup reproduzivel: cria a arvore de pastas e confere as dependencias.

Uso: python src/setup.py   (ou `from setup import preparar` no notebook)
No Colab, antes: `pip install -r requirements.txt`.
"""
import importlib.metadata as md
import sys
from pathlib import Path

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
PASTAS = ["data/raw", "data/interim", "data/processed", "src", "notebooks", "docs", "config"]


def preparar() -> None:
    for p in PASTAS:
        (RAIZ / p).mkdir(parents=True, exist_ok=True)
    faltando = []
    for linha in (RAIZ / "requirements.txt").read_text().splitlines():
        if "==" not in linha:
            continue
        pacote, versao = linha.strip().split("==")
        try:
            instalada = md.version(pacote)
        except md.PackageNotFoundError:
            faltando.append(f"{pacote} (ausente)")
            continue
        if instalada != versao:
            print(f"aviso: {pacote} {instalada} instalado, requirements pede {versao}")
    if faltando:
        sys.exit("Dependencias faltando: " + ", ".join(faltando) + "\nRode: pip install -r requirements.txt")
    print("ambiente ok:", RAIZ)


if __name__ == "__main__":
    preparar()
