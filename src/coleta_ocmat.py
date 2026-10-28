"""Premiados da OCMAT (Olimpíada Capixaba de Matemática), edição 2025.

Fonte: https://matematicanarede.sedu.es.gov.br/ocmat/2025 (Sedu-ES / Ufes / Fapes). Os resultados são 12 PDFs no Google Drive
(níveis 1 a 4 x ouro/prata/bronze), baixados uma única vez para data/raw/ocmat/2025/nivel<N>_<Medalha>.bin. A OCMAT teve a 1ª
edição em 2025; a de 2026 ainda não tem medalhistas. Por isso só há 2025 (não existem 10 edições).

Níveis (regulamento): 1 = 6º e 7º ano EF; 2 = 8º e 9º ano EF; 3 = 1ª série EM; 4 = 2ª e 3ª séries EM.
Os PDFs trazem ESTUDANTE | MUNICÍPIO | ESCOLA | NÍVEL | PREMIAÇÃO, com células de várias linhas: as palavras são lidas com
coordenadas (pdftotext -bbox) e cada uma vai para a linha da tabela (âncora Ouro/Prata/Bronze) mais próxima na vertical.

Saída: data/interim/ocmat_premiados.parquet (mesmas colunas de medalhistas.parquet).
"""
import html
import re
import subprocess
from pathlib import Path

import pandas as pd

from caminhos import RAIZ

RAW = RAIZ / "data/raw/ocmat"
SAIDA = RAIZ / "data/interim/ocmat_premiados.parquet"
ANOS = [2025]
MEDALHAS = {"Ouro", "Prata", "Bronze"}
PALAVRA = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>')
PAGINA = re.compile(r"<page [^>]*>(.*?)</page>", re.S)


def palavras_por_pagina(pdf: Path):
    xml = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    for pg in PAGINA.findall(xml):
        yield [(float(a), float(b), float(c), float(d), html.unescape(t)) for a, b, c, d, t in PALAVRA.findall(pg)]


def geometria(palavras):
    """(y do cabeçalho, [(coluna, x central)]) de uma página com cabeçalho; None se a página não tem."""
    # O cabeçalho é a linha de "ESTUDANTE" e "PREMIAÇÃO"; "ESCOLA" e "MUNICÍPIO" também aparecem dentro dos nomes de escola.
    ancora = [(y1, (x0 + x1) / 2) for x0, y0, x1, y1, t in palavras if t == "ESTUDANTE"]
    if not ancora or not any(t == "PREMIAÇÃO" for *_, t in palavras):
        return None
    y_cab = min(y for y, _ in ancora)
    cab = {t: ((x0 + x1) / 2, y1) for x0, y0, x1, y1, t in palavras
           if t in ("ESTUDANTE", "MUNICÍPIO", "ESCOLA", "PREMIAÇÃO") and abs(y1 - y_cab) < 6}
    if len(cab) < 4:
        return None
    # Coluna NÍVEL: palavra "NÍVEL" da linha de cabeçalho (a do título "NÍVEL 3" fica acima).
    niv = [(x0 + x1) / 2 for x0, y0, x1, y1, t in palavras if t == "NÍVEL" and abs(y1 - y_cab) < 6]
    centros = [("estudante", cab["ESTUDANTE"][0]), ("municipio", cab["MUNICÍPIO"][0]), ("escola", cab["ESCOLA"][0]),
               ("nivel", niv[0] if niv else cab["PREMIAÇÃO"][0] - 40), ("premiacao", cab["PREMIAÇÃO"][0])]
    return y_cab, sorted(centros, key=lambda c: c[1])


def linhas_da_pagina(palavras, geo):
    """Devolve [(estudante, municipio, escola, nivel, premiacao)] de uma página (as seguintes à primeira não repetem o cabeçalho)."""
    g = geometria(palavras)
    y_cab, centros = g if g else (-1.0, geo[1])
    limites = [(centros[i][1] + centros[i + 1][1]) / 2 for i in range(len(centros) - 1)]

    def coluna(x):
        return centros[sum(x > l for l in limites)][0]

    corpo = [(x0, y0, x1, y1, t) for x0, y0, x1, y1, t in palavras if y0 > y_cab]
    ancoras = sorted((y0 + y1) / 2 for x0, y0, x1, y1, t in corpo if t in MEDALHAS and coluna((x0 + x1) / 2) == "premiacao")
    if not ancoras:
        return []
    linhas = [{c: [] for c, _ in centros} for _ in ancoras]
    for x0, y0, x1, y1, t in sorted(corpo, key=lambda w: (round(w[1]), w[0])):
        ym = (y0 + y1) / 2
        i = min(range(len(ancoras)), key=lambda k: abs(ancoras[k] - ym))
        col = coluna((x0 + x1) / 2)
        # Nome de escola longo invade as colunas vizinhas: só dígito vale como nível e só Ouro/Prata/Bronze como premiação.
        if (col == "nivel" and not t.isdigit()) or (col == "premiacao" and t not in MEDALHAS):
            col = "escola"
        linhas[i][col].append(t)
    return [tuple(" ".join(l[c]).strip() for c in ("estudante", "municipio", "escola", "nivel", "premiacao")) for l in linhas]


SUFIXOS_NOME = {"FILHO", "JUNIOR", "JÚNIOR", "NETO", "SOBRINHO", "NETTO"}


def corrigir_bordas(estudante, municipio):
    """Sufixo do nome ("FILHO") que caiu na coluna do município volta para o nome; o distrito entre parênteses sai do município."""
    partes = municipio.split()
    if len(partes) > 1 and partes[0].upper() in SUFIXOS_NOME:
        estudante, municipio = estudante + " " + partes[0], " ".join(partes[1:])
    return estudante, re.sub(r"\s*\(.*?\)\s*", " ", municipio).strip()


def main() -> None:
    registros = []
    for ano in ANOS:
        for pdf in sorted((RAW / str(ano)).glob("nivel*_*.bin")):
            nivel, medalha = re.match(r"nivel(\d)_(\w+)\.bin", pdf.name).groups()
            n = 0
            paginas = list(palavras_por_pagina(pdf))
            geo = next(g for g in map(geometria, paginas) if g)
            for palavras in paginas:
                for est, mun, esc, niv, prem in linhas_da_pagina(palavras, geo):
                    assert prem == medalha and niv == nivel, (pdf.name, est, niv, prem)
                    est, mun = corrigir_bordas(est, mun)
                    registros.append({"olimpiada": "OCMAT", "ano": ano, "nivel": nivel, "modalidade": None, "medalha": medalha,
                                      "nome": est, "escola_nome": esc, "rede": "E", "municipio_nome": mun, "uf": "ES", "posicao": pd.NA})
                    n += 1
            print(pdf.name, n)
    df = pd.DataFrame(registros)
    df["ano"] = df["ano"].astype("int16")
    df["posicao"] = df["posicao"].astype("Int16")
    vazios = (df[["nome", "municipio_nome", "escola_nome"]] == "").sum().to_dict()
    df.to_parquet(SAIDA, index=False)
    print(len(df), "premiados ->", SAIDA, "| campos vazios:", vazios)
    print(df.groupby(["nivel", "medalha"]).size().unstack())


if __name__ == "__main__":
    main()
