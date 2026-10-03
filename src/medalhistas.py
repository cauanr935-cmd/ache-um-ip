"""T1.8-T1.11 - Empilha OBMEP + OBI em data/interim/medalhistas.parquet e gera os docs de cobertura/lacunas.

* OBMEP: data/interim/obmep_premiados.parquet ja existe (src/coleta_obmep.py) -> so valida e reaproveita.
* OBI: coleta e parseia (src/coleta_obi.py).
* ONHB: sem lista publica coletavel -> lacuna (docs/lacunas_olimpiadas.md).
Esquema: olimpiada, ano, nivel (texto), modalidade, medalha, nome, escola_nome, rede, municipio_nome, uf, posicao.
`nivel` vira texto porque a OBI tem Junior/Senior alem de 1/2; `modalidade` so existe na OBI.
nome em claro: apenas em data/interim (fora do versionamento) - ver convencoes.md (LGPD).
"""
import re
from pathlib import Path

import pandas as pd

import coleta_obi
import coleta_obmep

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
OBMEP = RAIZ / "data/interim/obmep_premiados.parquet"
SAIDA = RAIZ / "data/interim/medalhistas.parquet"
DOCS = RAIZ / "docs"
MEDALHAS = {"Ouro", "Prata", "Bronze", "Menção Honrosa"}


def validar_obmep(df: pd.DataFrame) -> list[str]:
    """Valida o parquet da OBMEP; devolve a lista de avisos (levanta AssertionError em erro grave)."""
    avisos = []
    assert list(df.columns) == coleta_obmep.SAIDA_COLS, f"colunas inesperadas: {list(df.columns)}"
    assert set(df["olimpiada"]) == {"OBMEP"}
    assert df["ano"].between(2016, 2025).all()
    assert set(df["nivel"]) <= {1, 2, 3}
    assert set(df["medalha"]) <= MEDALHAS
    assert df["nome"].str.len().gt(0).all() and df["uf"].str.fullmatch(r"[A-Z]{2}").all()
    # contagem independente no HTML bruto (sem usar o parser)
    for ano, n in df.groupby("ano").size().items():
        pasta = coleta_obmep.RAW / str(ano)
        html = [f.read_bytes().decode("utf-8", "replace") for f in pasta.glob("verRelatorioPremiados*.htm")]
        # linhas <tr> com >= 6 celulas <td> (2016 nao tem coluna de posicao), sem usar o parser;
        # exclui as linhas sem nome na fonte (em branco ou '---'), que o parser descarta de proposito
        sem_nome = sum(len(re.findall(r'<td align="?left"?>\s*(?:---)?\s*(?:</td>|<td)', h)) for h in html)
        bruto = sum(sum(c.lower().count("<td") >= 6 for c in h.split("<tr")[1:]) for h in html) - sem_nome
        if sem_nome:
            avisos.append(f"INFO OBMEP {ano}: {sem_nome} linha(s) sem nome na fonte, descartada(s) de propósito")
        if bruto != n:
            avisos.append(f"OBMEP {ano}: {n} linhas no parquet x {bruto} linhas <tr> no HTML bruto")
    dup = int(df.duplicated(["ano", "nivel", "medalha", "nome", "escola_nome", "municipio_nome", "uf"]).sum())
    if dup:
        avisos.append(f"OBMEP: {dup} linha(s) duplicada(s) (mesmo ano/nível/medalha/nome/escola/município)")
    return avisos


def empilhar(obmep: pd.DataFrame, obi: pd.DataFrame) -> pd.DataFrame:
    a = obmep.copy()
    a["nivel"] = a["nivel"].astype(str)
    a["modalidade"] = None
    out = pd.concat([a[coleta_obi.SAIDA_COLS], obi[coleta_obi.SAIDA_COLS]], ignore_index=True)
    out["ano"] = out["ano"].astype("int16")
    out["posicao"] = out["posicao"].astype("Int16")
    return out


def _pct(s: pd.Series) -> str:
    return f"{100 * s.mean():.1f}%"


def doc_cobertura(df: pd.DataFrame, log_obi: list[dict], avisos: list[str]) -> None:
    g = df.groupby(["olimpiada", "ano"])
    tab = g.apply(lambda x: pd.Series({
        "linhas": len(x), "% com escola": _pct(x["escola_nome"].notna()),
        "% com município": _pct(x["municipio_nome"].notna()), "% com UF": _pct(x["uf"].notna()),
        "% com rede": _pct(x["rede"].notna()), "% com posição": _pct(x["posicao"].notna())}),
        include_groups=False).reset_index()
    tot = df.groupby("olimpiada").apply(lambda x: pd.Series({
        "linhas": len(x), "% com escola": _pct(x["escola_nome"].notna()),
        "% com município": _pct(x["municipio_nome"].notna()), "% com UF": _pct(x["uf"].notna()),
        "% com rede": _pct(x["rede"].notna())}), include_groups=False).reset_index()
    ver = coleta_obmep._md_tabela
    txt = f"""# Cobertura das olimpíadas (T1.11)

Base: `data/interim/medalhistas.parquet` ({len(df)} linhas). Pergunta: cada lista liga o aluno a um território (escola e município)?

## Resumo por olimpíada

{ver(tot)}

## Por olimpíada e ano

{ver(tab)}

## Leitura

- **OBMEP:** escola, município e UF em 100% das linhas (nomes, **sem código INEP**; linkage = T2.3). `rede` (F/E/M/C/P) em ~100%: dá para filtrar escola pública. Anos presentes: {sorted(df.loc[df.olimpiada == 'OBMEP', 'ano'].unique().tolist())}.
- **OBI:** escola, cidade e UF em ~100%; **sem rede** (público/privada) e sem código INEP. Há linhas de modalidade Universitária (não são alunos de EF/EM) e Competição Feminina (CF-OBI) — decidir filtros na T2.x.
- **ONHB:** **0 linhas** (não há lista pública de equipes medalhistas coletável; ver `lacunas_olimpiadas.md`).
- Percentuais medem preenchimento, não qualidade do texto (grafias de escola/município variam entre fontes).

## Validação do parquet da OBMEP

{chr(10).join('- ' + a for a in avisos) if avisos else 'Sem divergências: colunas, domínios e contagem de linhas conferem com o HTML bruto.'}
"""
    (DOCS / "cobertura_olimpiadas.md").write_text(txt, encoding="utf-8")


def doc_lacunas(df: pd.DataFrame, log_obi: list[dict]) -> None:
    obi_anos = sorted(df.loc[df.olimpiada == "OBI", "ano"].unique().tolist())
    falhas = [f"- OBI {l['ano']}: {l['msg']}" for l in log_obi]
    txt = f"""# Lacunas — Olimpíadas (T1.8–T1.10)

Regra aplicada: onde bastava HTML simples, coletou-se com as mesmas regras do OBMEP (HTML baixado uma vez, pausa de 1,5 s,
User-Agent identificado, 3 tentativas). Onde exigiria login/interação, **não se forçou**.

## OBMEP (T1.8) — coletada: 2016–2019, 2024, 2025
- **2020–2023 ausentes.** O índice lista as edições 16ª, 17ª e 18ª, mas as páginas delas não informam o ano (só o número da edição) e o ano não foi inferido. Para recuperar: confirmar os anos na fonte oficial e preencher `config/obmep_anos.yaml`, depois rodar `python src/coleta_obmep.py` (mais `python src/medalhistas.py`). Detalhes: `lacunas.md` e `cobertura_obmep.md`.
- Páginas não trazem código INEP da escola (linkage = T2.3). 2016 só tem escolas públicas.
- Premiação *estadual* (segundo menu) não foi coletada.

## OBI (T1.9) — coletada: {', '.join(map(str, obi_anos))}
Fonte: `https://olimpiada.ic.unicamp.br/passadas/` → página de cada edição → "Quadro de Medalhas" por modalidade/nível (tabela HTML: medalha, classificação, nota, nome, escola, cidade, UF). Sem login, sem captcha; `robots.txt` inexistente (devolve página de erro).
{chr(10).join(falhas) if falhas else '- Sem falhas.'}
- **2018:** o link da edição consta no índice, mas a página responde 404 (verificado em 02/10/2026). Sem outra fonte identificada; pendente.
- Sem `rede` e sem código INEP; `posicao` vem preenchida (empates repetem o número).
- "HM" (Honra ao Mérito) foi mapeado para `Menção Honrosa` para unificar com a OBMEP; **2025 não traz linhas de HM** no quadro publicado.
- Inclui modalidade Universitária (2016) e Competição Feminina (CF-OBI): fora do perfil EF/EM ou de outra competição; filtrar na T2.x.
- `nivel` é texto (`Júnior`, `1`, `2`, `Sênior`); mapeamento nível → ano escolar ainda a fazer (T2.2 do plano de entregas).

## ONHB (T1.10) — NÃO coletada
Fonte: `https://www.olimpiadadehistoria.com.br/` (Unicamp). `robots.txt` permite tudo, mas:
- A unidade é a **equipe** (3 estudantes + professor), não o aluno individual.
- O site público publica **notícias com contagens agregadas** (ex.: 17 ouros, 27 pratas, 37 bronzes na final; medalhas por estado, em texto e mapas-imagem). Não há tabela/PDF com nome de equipe, escola e município por medalha.
- A relação nominal das equipes medalhistas fica na área logada ("sala da equipe"; exige login) e há um link para uma pasta do Google Drive ("Edições anteriores", na página *Downloads*), que exige acesso/interação. Não foram acessados.
- **Existe, mas não coletado:** totais de medalhas por edição/estado (texto de notícias; não estruturado).
- **Falta:** lista nominal por equipe (nome da equipe/escola/município/UF/medalha) por edição. **Como obter:** pedir à organização (Comissão Organizadora/Unicamp) ou baixar manualmente a pasta "Edições anteriores" e salvar em `data/raw/olimpiadas/onhb/`; o parser seria escrito sobre o formato real.
- Consequência: RF 2.5 cobre OBMEP e OBI, mas **não** ONHB.
"""
    (DOCS / "lacunas_olimpiadas.md").write_text(txt, encoding="utf-8")


def main() -> None:
    obmep = pd.read_parquet(OBMEP)
    avisos = validar_obmep(obmep)
    log_obi: list[dict] = []
    obi = coleta_obi.coletar_e_parsear(log_obi)
    df = empilhar(obmep, obi)
    df.to_parquet(SAIDA, index=False)
    doc_cobertura(df, log_obi, avisos)
    doc_lacunas(df, log_obi)
    print(f"{len(df)} linhas -> {SAIDA}", "| avisos OBMEP:", avisos or "nenhum")


if __name__ == "__main__":
    main()
