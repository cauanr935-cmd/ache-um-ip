"""Coleta os alunos do Instituto Ponte e a cidade de origem de cada um.

Fonte: https://www.institutoponte.org.br/como-atuamos/#alunos-row (lista de alunos) e a página de cada aluno
(/alunos/<nome>/), que traz "Cidade de Origem". Páginas públicas do próprio IP, baixadas uma única vez
(cache em data/raw/instituto_ponte/) e com pausa entre as requisições.

Saída: data/privado/alunos_ip.json  {codigo_ibge: [{nome, desde, escola_bolsista, escola_origem, url}], ...}
(Fica em data/privado: nomes de alunos, mesmo públicos, não vão para o git.)
"""
import html
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

from caminhos import RAIZ

URL_LISTA = "https://www.institutoponte.org.br/como-atuamos/"
RAW = RAIZ / "data/raw/instituto_ponte"
SAIDA = RAIZ / "data/privado/alunos_ip.json"
HEADERS = {"User-Agent": "ache-um-ip/1.0 (projeto universitario do Instituto Ponte)"}
PAUSA = 0.7
UF_PADRAO = "ES"  # o IP atua no Espírito Santo; a página do aluno não informa a UF


def baixar(url, destino):
    if destino.exists() and destino.stat().st_size > 0:
        return destino.read_text(encoding="utf-8", errors="replace")
    destino.parent.mkdir(parents=True, exist_ok=True)
    for t in range(3):
        time.sleep(PAUSA)
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            destino.write_bytes(r.content)
            return r.content.decode("utf-8", errors="replace")
        except requests.RequestException as e:
            print(f"  tentativa {t + 1}/3 falhou: {url}: {e}", file=sys.stderr)
    raise RuntimeError(f"falha ao baixar {url}")


def sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn").strip()


def texto(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    return [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", "\n", h)).split("\n") if l.strip()]


def campo(linhas, rotulo):
    """Valor de um rótulo ('Cidade de Origem:'): na mesma linha ou na seguinte; vazio se a próxima linha é outro rótulo."""
    base = re.escape(rotulo.rstrip(":").strip())
    for i, l in enumerate(linhas):
        m = re.match(rf"^{base}\s*:?\s*(.*)$", l, re.I)
        if not m:
            continue
        valor = m.group(1).strip()
        if not valor and i + 1 < len(linhas):
            prox = linhas[i + 1].strip()
            if not prox.endswith(":") and not prox.lower().startswith(("política", "contato", "escola ")):
                valor = prox
        return valor.lstrip(": ").strip() or None
    return None


UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}


def separar_uf(cidade):
    """'Cariacica ES', 'Ipojuca/PE', 'Vila Velha - ES' -> ('Cariacica', 'ES'); sem UF -> (cidade, None)."""
    cidade = re.sub(r"[\s\-–/,]+$", "", cidade.strip())
    m = re.match(r"^(.*?)[\s/,\-]+([A-Za-z]{2})\.?$", cidade)
    if m and m.group(2).upper() in UFS:
        return m.group(1).strip(" /-,"), m.group(2).upper()
    return cidade.strip(), None


def listar_alunos(html_lista):
    corpo = html_lista[html_lista.find('id="alunos-row"'):]
    achados = re.findall(r'<a href="(https://www\.institutoponte\.org\.br/alunos/[^"]+/)"[^>]*title="([^"]*)"', corpo)
    return list(dict(achados).items())  # url -> nome, sem repetir


def main():
    lista = baixar(URL_LISTA, RAW / "como-atuamos.html")
    alunos = listar_alunos(lista)
    print(len(alunos), "alunos na lista", flush=True)

    dim = pd.read_parquet(RAIZ / "data/interim/dim_municipio_base.parquet")
    dim["chave"] = dim["no_municipio"].map(sem_acento)
    por_nome = {k: g for k, g in dim.groupby("chave")}

    resultado, sem_cidade, sem_match = {}, [], []
    for n, (url, nome) in enumerate(alunos, 1):
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        linhas = texto(baixar(url, RAW / "alunos" / f"{slug}.html"))
        cidade = campo(linhas, "Cidade de Origem:")
        desde = next((re.search(r"(\d{4})", l).group(1) for l in linhas if l.startswith("Aluno IP desde")), None)
        if not cidade:
            sem_cidade.append(nome)
            continue
        nome_cidade, uf_citada = separar_uf(cidade)
        cand = por_nome.get(sem_acento(nome_cidade))
        if cand is None:
            sem_match.append((nome, cidade))
            continue
        escolhido = cand[cand["uf"] == (uf_citada or UF_PADRAO)]
        if escolhido.empty and not uf_citada:  # sem UF e fora do ES: só aceita se o nome for único no país
            escolhido = cand if len(cand) == 1 else None
        if escolhido is None or escolhido.empty:
            sem_match.append((nome, cidade))
            continue
        ibge = str(escolhido.iloc[0]["co_municipio"])
        resultado.setdefault(ibge, []).append({
            "nome": nome, "desde": int(desde) if desde else None, "cidade": cidade,
            "escola_bolsista": campo(linhas, "Escola como bolsista:"), "escola_origem": campo(linhas, "Escola de origem:"), "url": url,
        })
        if n % 50 == 0:
            print(n, "de", len(alunos), flush=True)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(resultado, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("alunos com município:", sum(len(v) for v in resultado.values()), "em", len(resultado), "municípios")
    print("sem cidade:", len(sem_cidade), sem_cidade[:10])
    print("cidade não encontrada:", len(sem_match), sem_match[:15])


if __name__ == "__main__":
    main()
