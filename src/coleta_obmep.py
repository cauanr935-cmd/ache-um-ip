"""T1.8 - Coleta dos premiados da OBMEP (2016-2025).

Fluxo: premiados.htm -> pagina-mapa de cada edicao -> listas (Ouro/Prata/Bronze/
Mencao Honrosa, publicas/privadas) -> HTML bruto (baixado uma unica vez) -> parquet.
Nenhuma URL e montada de memoria: todas vem de links extraidos das paginas.
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
RAW = RAIZ / "data/raw/olimpiadas/obmep/html"
SAIDA = RAIZ / "data/interim/obmep_premiados.parquet"
DOC_COBERTURA = RAIZ / "docs/cobertura_obmep.md"
DOC_LACUNAS = RAIZ / "docs/lacunas.md"
# Opcional: {rotulo da edicao no indice: ano} para edicoes cujas paginas nao informam o ano.
CONFIG_ANOS = RAIZ / "config/obmep_anos.yaml"

URL_INDICE = "https://www.obmep.org.br/premiados.htm"
ANOS = range(2016, 2026)  # RN 6: ultimos 10 anos
PAUSA = 1.5
TIMEOUT = 30
TENTATIVAS = 3
HEADERS = {"User-Agent": "ache-um-ip/1.0 (pesquisa academica)"}

_ultima_req = 0.0
OFFLINE = False  # True: nunca acessa a rede; so le o cache em data/raw (pipeline.run_coleta(baixar=False))


def baixar(url: str, destino: Path) -> str:
    """Baixa url para destino uma unica vez; se o arquivo existe, so le."""
    global _ultima_req
    if destino.exists() and destino.stat().st_size > 0:
        return destino.read_bytes().decode("utf-8", errors="replace")
    if OFFLINE:
        raise RuntimeError(f"modo offline e sem cache: {url}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    erro = None
    for t in range(1, TENTATIVAS + 1):
        espera = PAUSA - (time.monotonic() - _ultima_req)
        if espera > 0:
            time.sleep(espera)
        _ultima_req = time.monotonic()
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            destino.write_bytes(r.content)
            return r.content.decode("utf-8", errors="replace")
        except requests.RequestException as e:
            erro = e
            print(f"  tentativa {t}/{TENTATIVAS} falhou: {url}: {e}", file=sys.stderr)
    raise RuntimeError(f"falha ao baixar {url}: {erro}")


def sopa(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# ---------------------------------------------------------------- descoberta
RE_MEDALHA = re.compile(r"verRelatorioPremiados(Ouro|Prata|Bronze)(\.privada)?\.do\.htm$")
RE_MENCAO = re.compile(r"verRelatorioPremiadosMencao-([A-Z]{2})\.(\d)(\.privada)?\.do\.htm$")
RE_COMBO = re.compile(r"function comboUF\(goto\)\{var url='([^']*)'\+goto\.value\+'([^']*)'")
RE_ANO = re.compile(r"\b(20[0-2]\d)\b")


def slug(url: str) -> str:
    return re.sub(r"\W+", "_", url.split("://", 1)[-1]).strip("_")


def nome_arquivo(url: str) -> str:
    return url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]


def descobrir_mapas(html_indice: str) -> list[tuple[str, str]]:
    """(rotulo, url) de cada pagina-mapa listada em premiados.htm."""
    s = sopa(html_indice)
    mapas = []
    for a in s.find_all("a", href=True):
        url = urljoin(URL_INDICE, a["href"])
        if "premiacao.obmep.org.br" in url and re.search(r"mapa", url):
            mapas.append((a.get_text(" ", strip=True), url))
    return mapas


def listas_do_mapa(html_mapa: str, url_mapa: str) -> dict:
    """Links de medalhas e (se houver) o modelo de URL + UFs do menu de Mencao Honrosa."""
    s = sopa(html_mapa)
    medalhas = []  # (medalha, rede_pagina, url)
    for a in s.find_all("a", href=True):
        m = RE_MEDALHA.search(a["href"])
        if m:
            rede = "privada" if m.group(2) else "publica"
            medalhas.append((m.group(1), rede, urljoin(url_mapa, a["href"])))
    menu = None
    mc = RE_COMBO.search(html_mapa)
    for sel in s.find_all("select"):
        if mc and sel.get("onchange", "").strip() == "comboUF(this);":
            ufs = [o["value"] for o in sel.find_all("option") if o.get("value")]
            menu = (urljoin(url_mapa, mc.group(1)), mc.group(2), ufs)
            break
    return {"medalhas": medalhas, "menu": menu}


def ano_da_pagina(html: str) -> int | None:
    h1 = sopa(html).find("h1")
    m = RE_ANO.search(h1.get_text(" ", strip=True)) if h1 else None
    return int(m.group(1)) if m else None


def coletar(log: list[dict]) -> dict[int, list[dict]]:
    """Baixa mapas e listas. Retorna {ano: [{medalha, rede_pagina, nivel_url, arquivo}]}.

    `log` recebe ocorrencias (ano/edicao, mensagem) para docs/lacunas.md.
    """
    pasta_mapas = RAW / "_mapas"
    html_indice = baixar(URL_INDICE, RAW / "premiados.htm")
    edicoes: dict[int, list[dict]] = {}
    anos_config = (yaml.safe_load(CONFIG_ANOS.read_text(encoding="utf-8")) or {}) if CONFIG_ANOS.exists() else {}
    for rotulo, url_mapa in descobrir_mapas(html_indice):
        m_rot = RE_ANO.search(rotulo)
        if m_rot and int(m_rot.group(1)) not in ANOS:
            continue  # rotulo "OBMEP 2009" etc.: fora do periodo, nao baixa
        try:
            html_mapa = baixar(url_mapa, pasta_mapas / f"{slug(url_mapa)}.htm")
            info = listas_do_mapa(html_mapa, url_mapa)
            if not info["medalhas"]:
                raise RuntimeError("mapa sem links de medalhas")
            # ano: do titulo do mapa ("OBMEP 2019") ou do cabecalho da 1a lista ("20a OBMEP 2025")
            ano = None
            m = RE_ANO.search(rotulo)
            if m:
                ano = int(m.group(1))
            primeira = info["medalhas"][0][2]
            tmp = pasta_mapas / f"{slug(url_mapa)}__{nome_arquivo(primeira)}"
            ano_lista = ano_da_pagina(baixar(primeira, tmp))
            if ano_lista and ano and ano_lista != ano:
                raise RuntimeError(f"ano divergente: rotulo {ano} x lista {ano_lista}")
            ano = ano_lista or ano or anos_config.get(rotulo)
            if ano is None:
                raise RuntimeError("as paginas da edicao nao informam o ano (informe em config/obmep_anos.yaml)")
        except Exception as e:  # noqa: BLE001 - registra e segue
            log.append({"ano": None, "edicao": rotulo, "msg": f"mapa {url_mapa}: {e}"})
            continue
        if ano not in ANOS:
            continue
        if ano in edicoes:
            log.append({"ano": ano, "edicao": rotulo,
                        "msg": f"mais de um mapa para {ano}; mantido o primeiro, ignorado {url_mapa}"})
            continue
        arquivos = []
        pasta = RAW / str(ano)

        def pegar(url, medalha, rede, uf=None, nivel_mh=None):
            try:
                if url == primeira:
                    destino = pasta / nome_arquivo(url)
                    if not destino.exists():
                        destino.parent.mkdir(parents=True, exist_ok=True)
                        tmp.replace(destino)
                baixar(url, pasta / nome_arquivo(url))
                arquivos.append({"medalha": medalha, "rede_pagina": rede, "uf_menu": uf,
                                 "nivel_mh": nivel_mh, "arquivo": pasta / nome_arquivo(url)})
            except Exception as e:  # noqa: BLE001
                log.append({"ano": ano, "edicao": rotulo, "msg": f"{url}: {e}"})

        for medalha, rede, url in info["medalhas"]:
            pegar(url, medalha, rede)
        if info["menu"]:
            prefixo, sufixo, ufs = info["menu"]
            for uf in ufs:
                url_menu = f"{prefixo}{uf}{sufixo}"
                try:
                    html_menu = baixar(url_menu, pasta / nome_arquivo(url_menu))
                except Exception as e:  # noqa: BLE001
                    log.append({"ano": ano, "edicao": rotulo, "msg": f"menu MH {uf}: {e}"})
                    continue
                for a in sopa(html_menu).find_all("a", href=True):
                    m = RE_MENCAO.search(a["href"])
                    if m:
                        pegar(urljoin(url_menu, a["href"]), "Menção Honrosa",
                              "privada" if m.group(3) else "publica", m.group(1), int(m.group(2)))
        else:
            log.append({"ano": ano, "edicao": rotulo, "msg": "mapa sem menu de Menção Honrosa"})
        edicoes[ano] = arquivos
        print(f"{ano}: {len(arquivos)} listas", flush=True)
    for ano in ANOS:
        if ano not in edicoes:
            log.append({"ano": ano, "edicao": "-", "msg": "sem dados: nenhuma edição com este ano identificado em premiados.htm (as 16ª–18ª OBMEP existem mas suas páginas não informam o ano)"})
    return edicoes


# ------------------------------------------------------------------- parsing
COLUNAS = {"nome": "nome", "escola": "escola_nome", "tipo": "rede",
           "município": "municipio_nome", "uf": "uf", "medalha": "medalha", "menção": "medalha"}
SAIDA_COLS = ["olimpiada", "ano", "nivel", "medalha", "nome", "escola_nome", "rede",
              "municipio_nome", "uf", "posicao"]


def _txt(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def parsear_lista(arquivo: Path, ano: int, medalha: str) -> list[dict]:
    """Extrai as linhas de uma pagina de lista (uma tabela por nivel). Levanta erro se a estrutura diferir."""
    s = sopa(arquivo.read_bytes().decode("utf-8", errors="replace"))
    linhas = []
    for tabela in s.find_all("table"):
        ths = [_txt(th) for th in tabela.find_all("th")]
        nivel = next((int(m.group(1)) for t in ths if (m := re.fullmatch(r"N[ií]vel (\d)", t))), None)
        cab = [t for t in ths if not re.fullmatch(r"N[ií]vel \d", t)]
        if nivel is None or not cab:
            continue  # tabela sem lista (layout)
        campos = [COLUNAS.get(t.lower()) for t in cab]
        if sorted(c for c in campos if c) != sorted(["nome", "escola_nome", "rede", "municipio_nome", "uf", "medalha"]):
            raise ValueError(f"cabecalho inesperado em {arquivo.name}: {cab}")
        for tr in tabela.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) != len(cab):
                continue
            v = [_txt(td) for td in tds]
            d = {c: x for c, x in zip(campos, v) if c}
            pos = v[campos.index(None)] if None in campos else ""
            if not d["nome"] or d["nome"] == "---":  # '---' = linha sem dados (placeholder da fonte)
                continue
            linhas.append({
                "olimpiada": "OBMEP", "ano": ano, "nivel": nivel,
                "medalha": medalha, "nome": d["nome"], "escola_nome": d["escola_nome"],
                "rede": d["rede"] if d["rede"] not in ("", "---") else None, "municipio_nome": d["municipio_nome"],
                "uf": d["uf"], "posicao": int(pos) if pos.isdigit() else None,
            })
    if not linhas and "Não existem registros" not in s.get_text(" "):
        raise ValueError(f"nenhuma linha extraida de {arquivo.name}")  # lista vazia legitima traz aviso explicito
    return linhas


# ----------------------------------------------------------------- documentos
def _md_tabela(df: pd.DataFrame) -> str:
    cab = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    corpo = ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)]
    return "\n".join([cab, sep, *corpo])


def escrever_cobertura(df: pd.DataFrame, log: list[dict]) -> None:
    ordem = ["Ouro", "Prata", "Bronze", "Menção Honrosa"]
    partes = ["# Cobertura OBMEP (T1.8)\n",
              f"Fonte: {URL_INDICE} (páginas-mapa por edição). Período: {ANOS[0]}–{ANOS[-1]} (RN 6).",
              f"Total de linhas: {len(df)}. Arquivo: `data/interim/obmep_premiados.parquet`.\n"]
    if len(df):
        por_ano = df.pivot_table(index="ano", columns="medalha", values="nome", aggfunc="count",
                                 fill_value=0).reindex(columns=ordem, fill_value=0)
        por_ano["Total"] = por_ano.sum(axis=1)
        partes += ["## Linhas por ano e medalha\n", _md_tabela(por_ano.reset_index()), ""]
        det = (df.groupby(["ano", "medalha", "nivel"]).size().unstack("nivel", fill_value=0)
               .reindex(columns=[1, 2, 3], fill_value=0))
        det.columns = [f"nível {c}" for c in det.columns]
        det = det.reset_index()
        det["medalha"] = pd.Categorical(det["medalha"], ordem, ordered=True)
        det = det.sort_values(["ano", "medalha"])
        partes += ["## Linhas por ano, medalha e nível\n", _md_tabela(det), ""]
        rede = df.groupby(["ano", "rede"], dropna=False).size().unstack("rede", fill_value=0).reset_index()
        partes += ["## Linhas por ano e valor de `rede` (como publicado)\n", _md_tabela(rede), ""]
        sem_priv = [int(a) for a in sorted(df["ano"].unique()) if not (df.loc[df["ano"] == a, "rede"] == "P").any()]
        if sem_priv:
            partes.append(f"Anos sem escolas privadas (rede `P` ausente; páginas só de escolas públicas): {', '.join(map(str, sem_priv))}. "
                          "`rede` segue o publicado: F federal, E estadual, M municipal, C (outros, como publicado), P privada.\n")
        dup = int(df.duplicated(["ano", "nivel", "medalha", "nome", "escola_nome", "municipio_nome", "uf"]).sum())
        partes.append(f"Linhas duplicadas (mesmo ano/nível/medalha/nome/escola/município/UF): {dup}.\n")
    anos_ok = set(df["ano"]) if len(df) else set()
    falhos = [a for a in ANOS if a not in anos_ok]
    partes += ["## Anos sem dados\n", ", ".join(map(str, falhos)) if falhos else "Nenhum.", "",
               "## Ocorrências (falhas de download/estrutura)\n"]
    partes += [f"- {l['ano'] or l['edicao']}: {l['msg']}" for l in log] or ["Nenhuma."]
    DOC_COBERTURA.parent.mkdir(parents=True, exist_ok=True)
    DOC_COBERTURA.write_text("\n".join(partes) + "\n", encoding="utf-8")


def escrever_lacunas(log: list[dict]) -> None:
    marca = "## OBMEP (T1.8)"
    atual = DOC_LACUNAS.read_text(encoding="utf-8") if DOC_LACUNAS.exists() else "# Lacunas\n"
    atual = atual.split(marca)[0].rstrip() + "\n\n" if marca in atual else atual.rstrip() + "\n\n"
    linhas = [marca, "",
              "- Páginas OBMEP não trazem código INEP da escola; linkage fica para a T2.3.",
              "- A premiação *estadual* (segundo menu das edições recentes) não foi coletada: "
              "o escopo é Ouro/Prata/Bronze/Menção Honrosa nacionais."]
    linhas += [f"- {l['ano'] or l['edicao']}: {l['msg']}" for l in log]
    DOC_LACUNAS.parent.mkdir(parents=True, exist_ok=True)
    DOC_LACUNAS.write_text(atual + "\n".join(linhas) + "\n", encoding="utf-8")


def main() -> None:
    log: list[dict] = []
    edicoes = coletar(log)
    linhas = []
    for ano, arquivos in sorted(edicoes.items()):
        for a in arquivos:
            try:
                linhas += parsear_lista(a["arquivo"], ano, a["medalha"])
            except Exception as e:  # noqa: BLE001
                log.append({"ano": ano, "edicao": "-", "msg": f"parsing {a['arquivo'].name}: {e}"})
    df = pd.DataFrame(linhas, columns=SAIDA_COLS)
    df = df.astype({"ano": "int16", "nivel": "int8", "posicao": "Int16"})
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SAIDA, index=False)
    escrever_cobertura(df, log)
    escrever_lacunas(log)
    print(f"{len(df)} linhas -> {SAIDA}")


if __name__ == "__main__":
    main()
