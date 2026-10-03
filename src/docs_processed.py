"""Gera docs/qualidade_processed.md a partir das tabelas de data/processed (chamado por processed.py)."""
from pathlib import Path

import pandas as pd

from processed import CHAVES

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)


def md(df: pd.DataFrame) -> str:
    cab = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    linhas = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([cab, sep, *linhas])


def _nulos(d: pd.DataFrame) -> pd.DataFrame:
    n = d.isna().mean().mul(100).round(1)
    return pd.DataFrame({"coluna": n.index, "% nulos": n.values, "tipo": [str(d[c].dtype) for c in n.index]})


def gerar(t: dict, res: dict, m: pd.DataFrame) -> None:
    vis = pd.DataFrame([{"tabela": k, "linhas": f"{len(d):,}".replace(",", "."), "colunas": d.shape[1],
                         "chave": ", ".join(CHAVES[k]), "chaves duplicadas": res[f"{k}_dup"]} for k, d in t.items()])
    fm = t["fato_medalhas"]
    lig = (fm.groupby(["olimpiada", "ano", "link_status"]).size().unstack(fill_value=0)
           .reindex(columns=["auto", "revisao", "sem_match"], fill_value=0))
    tot = lig.sum(axis=1)
    lig_pct = (lig.div(tot, axis=0) * 100).round(1).astype(str) + "%"
    lig_pct.insert(0, "linhas", tot)
    lig_pct = lig_pct.reset_index()
    mm = fm.groupby(["olimpiada", "match_municipio"], dropna=False).size().unstack(fill_value=0).reset_index()
    et = fm.groupby(["olimpiada", "etapa"], dropna=False).size().unstack(fill_value=0).reset_index()
    fd = t["fato_desempenho"]
    fdres = fd.groupby(["fonte", "nivel_geo"]).agg(linhas=("valor", "size"), metricas=("metrica", "nunique"),
                                                   suprimidas=("suprimido", "sum")).reset_index()
    fdres["% suprimidas"] = (100 * fdres["suprimidas"] / fdres["linhas"]).round(1)
    fdn = fd.groupby("fonte")["valor"].apply(lambda s: round(100 * s.isna().mean(), 1)).rename("% valor nulo (suprimido)").reset_index()
    secoes_nulos = "\n\n".join(f"### {k}\n\n{md(_nulos(d))}" for k, d in t.items() if k != "fato_desempenho")
    hits = res["lgpd_hits_exatos"]
    txt = f"""# Qualidade das tabelas de `data/processed/` (T2.10–T2.11)

Gerado por `python src/processed.py`. Tabelas: `dim_municipio`, `dim_escola`, `dim_aluno`, `fato_desempenho`, `fato_medalhas`.

## 1. Visão geral e chaves

{md(vis)}

Asserts executados (todos passaram): chaves únicas; `co_municipio` com 7 dígitos e `co_entidade` com 8 dígitos (str); integridade referencial
(`dim_escola`/`dim_aluno`/`fato_medalhas` → `dim_municipio`; `dim_aluno`/`fato_medalhas` → `dim_escola`; `fato_medalhas` → `dim_aluno`;
`fato_desempenho` → dimensões por `nivel_geo`); célula suprimida sem valor; nenhuma coluna de nome de pessoa.

## 2. LGPD
- Nenhuma coluna `nome*`, `nome_norm`, `aluno_key` em `data/processed`. Ids: `id_registro_hash` (SHA-256 de sal + nome normalizado + ano + olimpíada) e `id_aluno_hash` (SHA-256 de sal + identidade da dedup). Política em `lgpd.md`.
- Varredura: valores textuais das tabelas comparados com os {len(set()) or 'todos os'} nomes normalizados de medalhistas (igualdade exata). Coincidências: {hits if hits else 'nenhuma'}.
  {'Cada coincidência é um valor textual (ex.: nome de escola) idêntico a um nome de pessoa; revisar se houver.' if hits else ''}
- `dim_aluno` e `fato_medalhas` são **pseudonimizados, não anonimizados**: município + escola + ano + medalha podem permitir reidentificação por quem conheça o aluno. Não publicar linha a linha; a exposição pública deve usar só agregados com `suprimido`/`n_publicavel`.

## 3. Nulos por coluna

{secoes_nulos}

### fato_desempenho
Nulos estruturais: `valor` nulo só em células `suprimido=True`; `rede_detalhe` e `n` são nulos conforme a fonte (ver abaixo).

{md(fdn)}

## 4. fato_medalhas — linkage e município
Status do vínculo medalhista → escola por olimpíada/ano (catálogo provisório do Ideb; ver `linkage.md`):

{md(lig_pct)}

Casamento de município (`match_municipio`):

{md(mm)}

Etapa (`etapa`; vazio = nível não mapeável; `no_escopo_ef2_em` marca o que está em EF2/EM):

{md(et)}

## 5. fato_desempenho (formato longo)
Granularidade: `nivel_geo` (escola | municipio | uf) × `entidade_id` × `fonte` (ideb | saeb_microdados | enem | obmep | obi) × `etapa` × `ano` × `rede_grupo` × `rede_detalhe` × `recorte` × `metrica`. Uma linha por métrica.

{md(fdres)}

- `entidade_id`: `co_entidade` (8), `co_municipio` (7) ou sigla da UF, conforme `nivel_geo`.
- Ideb não informa `n` (nulo); vale o `ND` do INEP. ENEM: `n` = base da célula; supressão n < 10.
- Medalhas: `n_medalhas` e `n_alunos_unicos` por município × ano × olimpíada × medalha × etapa × rede; suprimidas quando n < 10.
- ENEM 2024–2025: perfil/renda (participantes) e notas/escola (resultados) **não se juntam**; por isso a coluna `recorte` carrega a visão (`perfil_prova`, `desempenho_prova`, `desempenho_escola`).

## 6. Limitações
1. **`dim_escola` é provisória**: só 53.773 escolas do Ideb (1.244 privadas), sem localização nem etapas; o Censo Escolar (T1.13) segue pendente. O linkage de medalhistas precisa ser refeito quando o Censo chegar.
2. **Linkage baixo na OBI e nas escolas privadas** (ver §4) por construção do catálogo, não só do método.
3. **Saeb microdados não entra por escola ou município** (IDs fictícios): só em `nivel_geo='uf'`. Escola/município vêm do Ideb.
4. `dim_aluno.co_entidade` só existe quando o vínculo foi automático; candidatos em revisão não são promovidos.
5. A identidade de aluno (nome + município + escola) pode **separar** a mesma pessoa (escola grafada diferente) e **juntar** homônimos; ver `linkage.md`.
6. `rede_grupo` de medalhistas é nulo para a OBI e para o código `C` da OBMEP.
7. Não há validação formal de precisão/recall do linkage (T4.1).
"""
    (RAIZ / "docs/qualidade_processed.md").write_text(txt, encoding="utf-8")
