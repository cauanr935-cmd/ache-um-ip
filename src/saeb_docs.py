"""T1.5-T1.7 - Gera docs/eda_saeb.md (calculado dos parquets). lacunas_saeb.md e decisoes_pendentes.md sao escritos a mao."""
import duckdb
import pandas as pd

from enem_docs import md

from caminhos import RAIZ
I = RAIZ / "data/interim"
S, IE, IM, DM = (f"'{I / n}'" for n in ("saeb_escola.parquet", "ideb_escola.parquet", "ideb_municipio.parquet",
                                          "dim_municipio_base.parquet"))


def q(sql: str) -> pd.DataFrame:
    return duckdb.sql(sql).df()


def main() -> None:
    vol = q(f"""SELECT ano, etapa, rede, COUNT(*) escolas, COUNT(proficiencia_lp) com_proficiencia,
                SUM(n_alunos) alunos_presentes FROM {S} GROUP BY ALL ORDER BY ALL""")
    cols = ["proficiencia_lp", "proficiencia_mt", "n_alunos", "n_matriculados_censo", "inse_escola", "inse_aluno_medio"]
    nul = q(f"""SELECT ano, etapa, COUNT(*) n, {', '.join(f"ROUND(100.0*AVG(({c} IS NULL)::INT),1) AS {c}" for c in cols)}
                FROM {S} GROUP BY ALL ORDER BY ALL""")
    prof = q(f"""SELECT ano, etapa, rede, ROUND(AVG(proficiencia_lp),1) lp_media, ROUND(STDDEV(proficiencia_lp),1) lp_dp,
                 ROUND(QUANTILE_CONT(proficiencia_lp,0.1),1) lp_p10, ROUND(MEDIAN(proficiencia_lp),1) lp_mediana,
                 ROUND(QUANTILE_CONT(proficiencia_lp,0.9),1) lp_p90, ROUND(AVG(proficiencia_mt),1) mt_media,
                 ROUND(STDDEV(proficiencia_mt),1) mt_dp, ROUND(MEDIAN(proficiencia_mt),1) mt_mediana
                 FROM {S} WHERE proficiencia_lp IS NOT NULL GROUP BY ALL ORDER BY ALL""")
    uf = q(f"""SELECT uf, etapa, COUNT(proficiencia_lp) n FROM {S} WHERE ano=2023 GROUP BY ALL""") \
        .pivot(index="uf", columns="etapa", values="n").fillna(0).astype(int).reset_index()
    cob = q(f"""WITH t AS (SELECT etapa, ano, COUNT(DISTINCT co_municipio) FILTER (WHERE nota_saeb_lp IS NOT NULL) municipios_com_nota
                FROM {IM} WHERE rede = 'Pública' GROUP BY ALL), d AS (SELECT COUNT(*) total FROM {DM})
                SELECT t.etapa, t.ano, municipios_com_nota, ROUND(100.0*municipios_com_nota/d.total,1) pct_dos_municipios
                FROM t, d WHERE t.ano >= 2017 ORDER BY 1, 2""")
    cob_e = q(f"""SELECT etapa, ano, COUNT(*) FILTER (WHERE nota_saeb_lp IS NOT NULL) escolas_com_nota,
                  COUNT(DISTINCT co_municipio) FILTER (WHERE nota_saeb_lp IS NOT NULL) municipios
                  FROM {IE} WHERE ano >= 2017 GROUP BY ALL ORDER BY ALL""")
    inse_n = q(f"""SELECT ano, inse_escala, COALESCE(inse_escola, '(nulo)') inse_escola, COUNT(*) escolas
                   FROM {S} GROUP BY ALL ORDER BY 1, 3""").pivot(index=["inse_escola"], columns="ano", values="escolas") \
        .fillna(0).astype(int).reset_index()
    inse_a = q(f"""SELECT ano, etapa, COUNT(inse_aluno_medio) escolas, ROUND(AVG(inse_aluno_medio),2) media,
                   ROUND(STDDEV(inse_aluno_medio),2) dp, ROUND(MIN(inse_aluno_medio),2) min, ROUND(MAX(inse_aluno_medio),2) max
                   FROM {S} WHERE inse_aluno_medio IS NOT NULL GROUP BY ALL ORDER BY ALL""")
    ideb_n = q(f"""SELECT etapa, ano, COUNT(*) escolas, COUNT(ideb) com_ideb, COUNT(indicador_rendimento) com_rendimento,
                   COUNT(taxa_aprovacao) com_aprovacao FROM {IE} WHERE ano >= 2017 GROUP BY ALL ORDER BY ALL""") \
        if "taxa_aprovacao" in q(f"DESCRIBE SELECT * FROM {IE}")["column_name"].tolist() else None
    txt = f"""# EDA — Saeb e Ideb (T1.5–T1.7)

Bases: `data/interim/saeb_escola.parquet` (Saeb 2017, 2019, 2021, 2023; EF2 = 9º ano EF, EM = 3ª série EM),
`ideb_escola.parquet` e `ideb_municipio.parquet` (Ideb 2025, séries 2005–2025).

> **Limitação central.** No Saeb (microdados), `ID_ESCOLA` e `ID_MUNICIPIO` são **máscaras ("códigos fictícios")**
> segundo o dicionário oficial. Não casam com `co_entidade` INEP nem com o município IBGE (0% de sobreposição com Ideb e ENEM)
> e mudam a cada edição (0 escolas em comum entre 2017/2019/2021/2023). Só a UF é real. Por isso `saeb_escola` usa
> `id_escola_saeb`/`id_municipio_saeb` e **não serve para linkage**. As notas Saeb por escola/município **com código real** estão no Ideb
> (`nota_saeb_lp`, `nota_saeb_mt`). Detalhes em `lacunas_saeb.md`.

## Volumetria Saeb (escola × etapa × rede)

{md(vol)}

`alunos_presentes` = `NU_PRESENTES_*` do TS_ESCOLA (alunos presentes na etapa). Escolas sem proficiência divulgada têm participação insuficiente.

## % de nulos (Saeb)

{md(nul)}

`n_matriculados_censo` não existe para o EM em 2017. `inse_aluno_medio` só existe em 2021 e 2023 (INSE do aluno ausente antes).

## Proficiência média por escola (escala Saeb; escolas com média divulgada)

Média/desvio calculados **entre escolas** (sem ponderar por alunos).

{md(prof)}

Conferência (2023, EF2, LP): a média oficial do `TS_ESCOLA` difere em média 0,29 ponto (máx. 41,9) da média simples dos alunos
com proficiência (`PROFICIENCIA_LP_SAEB`) — usamos a oficial (31.080 escolas comparadas).

## Cobertura por UF (2023, escolas com proficiência LP)

{md(uf)}

## Cobertura por município (via Ideb, códigos IBGE reais)

Municípios com nota Saeb LP na **rede pública** (`ideb_municipio`), sobre os 5.571 da `dim_municipio_base`:

{md(cob)}

Escolas e municípios com nota Saeb no `ideb_escola`:

{md(cob_e)}

## INSE

Nível socioeconômico da **escola** (`inse_escola`, texto do INEP). **2017 usa "Grupo 1–5"; 2019+ usa "Nível I–VII": escalas diferentes, não comparar entre 2017 e os demais.**

{md(inse_n)}

INSE médio dos **alunos** por escola (`inse_aluno_medio`, só 2021/2023; entre alunos com `IN_INSE=1`):

{md(inse_a)}
"""
    if ideb_n is not None:
        txt += f"""
## Ideb — cobertura por escola

{md(ideb_n)}
"""
    (RAIZ / "docs/eda_saeb.md").write_text(txt, encoding="utf-8")
    print("eda_saeb.md ok")


if __name__ == "__main__":
    main()
