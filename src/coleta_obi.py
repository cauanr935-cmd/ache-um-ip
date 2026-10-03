"""T1.9 - Coleta dos quadros de medalhas da OBI (2016-2025).

Fluxo: /passadas/ -> pagina de cada edicao (OBIaaaa) -> links de "Quadro de Medalhas"
(qmerito = Iniciacao/Programacao, cfqmerito = Competicao Feminina) -> HTML bruto (uma vez) -> parsing.
URLs vem dos links das paginas, nunca montadas de memoria. Mesmas regras de rede da OBMEP.
Esquema de saida (nivel e texto; modalidade so existe na OBI): ver SAIDA_COLS.
"""
import re
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd

from coleta_obmep import ANOS, baixar, sopa

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
RAW = RAIZ / "data/raw/olimpiadas/obi/html"
URL_INDICE = "https://olimpiada.ic.unicamp.br/passadas/"
SAIDA_COLS = ["olimpiada", "ano", "nivel", "modalidade", "medalha", "nome", "escola_nome", "rede",
              "municipio_nome", "uf", "posicao"]
RE_EDICAO = re.compile(r"/passadas/OBI(\d{4})/$")
RE_QUADRO = re.compile(r"/(cf)?qmerito/([^/]+)/$")
MEDALHAS = {"ouro": "Ouro", "prata": "Prata", "bronze": "Bronze"}


def descobrir_edicoes(html_indice: str) -> dict[int, str]:
    edicoes = {}
    for a in sopa(html_indice).find_all("a", href=True):
        url = urljoin(URL_INDICE, a["href"])
        m = RE_EDICAO.search(url)
        if m and int(m.group(1)) in ANOS:
            edicoes[int(m.group(1))] = url
    return edicoes


def quadros_da_edicao(html: str, url: str) -> list[tuple[str, str]]:
    """(url, rotulo do link) dos quadros de medalhas listados na pagina da edicao."""
    vistos, saida = set(), []
    for a in sopa(html).find_all("a", href=True):
        u = urljoin(url, a["href"])
        if RE_QUADRO.search(u) and u not in vistos:
            vistos.add(u)
            saida.append((u, _txt(a)))
    return saida


def arquivo_local(ano: int, url: str) -> Path:
    resto = url.split(f"/OBI{ano}/", 1)[1].strip("/").replace("/", "_")
    return RAW / str(ano) / f"{resto}.htm"


def _txt(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def parsear_quadro(arquivo: Path, ano: int, url: str, rotulo: str = "") -> list[dict]:
    s = sopa(arquivo.read_bytes().decode("utf-8", errors="replace"))
    # o titulo varia: "Quadro de Medalhas - Modalidade X Nivel Y" (recente) ou h2 + h3 separados (antigo)
    heads = [_txt(h) for h in s.find_all(["h1", "h2", "h3", "h4"])]
    titulo = rotulo if rotulo.startswith("Modalidade") else None  # rotulo do link (cobre a Competicao Feminina)
    titulo = titulo or next((h for h in heads if h.startswith("Quadro de Medalhas") and "Modalidade" in h), None)
    if titulo is None:
        titulo = next((h for h in heads if h.startswith("Modalidade") or "Competição Feminina" in h), "")
    mt = re.search(r"(?:Quadro de Medalhas\s*-\s*)?(?:Modalidade\s+)?(.*?)(?:\s+N[ií]vel\s+(.+))?$", titulo)
    if not titulo or not mt or not mt.group(1):
        raise ValueError(f"titulo inesperado: {heads[:4]!r}")
    modalidade = mt.group(1).strip()
    nivel = (mt.group(2) or "").strip()
    if RE_QUADRO.search(url).group(1):  # cfqmerito
        modalidade = f"CF-OBI {modalidade}".strip()
    tabela = s.find("table")
    if tabela is None:
        raise ValueError("sem tabela")
    linhas = []
    for tr in tabela.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) != 7:
            continue
        img = tds[0].find("img")
        if img is not None:
            chave = next((v for k, v in MEDALHAS.items() if k in img.get("src", "")), None)
            if chave is None:
                raise ValueError(f"medalha desconhecida: {img.get('src')}")
            medalha = chave
        elif _txt(tds[0]) == "HM":
            medalha = "Menção Honrosa"  # "Honra ao Merito" da OBI
        else:
            continue  # cabecalho
        pos, _nota, nome, escola, cidade, uf = (_txt(t) for t in tds[1:])
        if not nome:
            continue
        linhas.append({"olimpiada": "OBI", "ano": ano, "nivel": nivel or None, "modalidade": modalidade,
                       "medalha": medalha, "nome": nome, "escola_nome": escola or None, "rede": None,
                       "municipio_nome": cidade or None, "uf": uf or None,
                       "posicao": int(pos) if pos.isdigit() else None})
    if not linhas:
        raise ValueError("nenhuma linha extraida")
    return linhas


def coletar_e_parsear(log: list[dict]) -> pd.DataFrame:
    html_indice = baixar(URL_INDICE, RAW / "passadas.htm")
    edicoes = descobrir_edicoes(html_indice)
    linhas = []
    for ano in ANOS:
        if ano not in edicoes:
            log.append({"ano": ano, "msg": "edição não listada em /passadas/"})
            continue
        try:
            html_ed = baixar(edicoes[ano], RAW / str(ano) / "_edicao.htm")
            quadros = quadros_da_edicao(html_ed, edicoes[ano])
            if not quadros:
                raise RuntimeError("página da edição sem links de Quadro de Medalhas")
        except Exception as e:  # noqa: BLE001
            log.append({"ano": ano, "msg": f"edição: {e}"})
            continue
        n_ok = 0
        for url, rotulo in quadros:
            try:
                destino = arquivo_local(ano, url)
                baixar(url, destino)
                linhas += parsear_quadro(destino, ano, url, rotulo)
                n_ok += 1
            except Exception as e:  # noqa: BLE001
                log.append({"ano": ano, "msg": f"{url}: {e}"})
        print(f"OBI {ano}: {n_ok}/{len(quadros)} quadros", flush=True)
    return pd.DataFrame(linhas, columns=SAIDA_COLS)
