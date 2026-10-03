"""T1.1-T1.4 - Gera docs/lacunas_enem.md, docs/dicionario_enem.md e docs/eda_enem.md."""
import duckdb
import pandas as pd

import enem

DOCS = enem.RAIZ / "docs"
ALL = enem.INTERIM / "enem_all.parquet"
NOTAS = ["nu_nota_cn", "nu_nota_ch", "nu_nota_lc", "nu_nota_mt", "nu_nota_redacao"]


def md(df: pd.DataFrame, indice: bool = False) -> str:
    if indice:
        df = df.reset_index()
    cab = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    linhas = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([cab, sep, *linhas])


def q(sql: str) -> pd.DataFrame:
    return duckdb.sql(sql).df()


def fmt_int(df: pd.DataFrame) -> pd.DataFrame:
    return df.map(lambda v: f"{v:,}".replace(",", ".") if isinstance(v, (int,)) and not isinstance(v, bool) else v)


# ------------------------------------------------------------ dicionario oficial
def categorias(ano: int, aba: str, variavel: str) -> list[tuple[str, str]]:
    xlsx = next((enem.RAW / f"microdados_enem_{ano}").rglob("*.xlsx"))
    d = pd.read_excel(xlsx, sheet_name=aba, header=None, dtype=str).fillna("")
    out, dentro = [], False
    for _, r in d.iterrows():
        nome = r[0].strip()
        if nome:
            dentro = nome == variavel
        if dentro and r[2].strip():
            out.append((r[2].strip(), r[3].strip()))
    return out


def tabela_cat(ano, aba, var) -> str:
    return md(pd.DataFrame(categorias(ano, aba, var), columns=["código", "descrição"]))


def gerar_lacunas(presentes: dict) -> None:
    linhas = [{"ano": a, "status": "presente" if a in presentes else "AUSENTE",
               "arquivos": ", ".join(presentes[a]) if a in presentes else "-"} for a in enem.ANOS_ALVO]
    ausentes = [a for a in enem.ANOS_ALVO if a not in presentes]
    txt = f"""# Lacunas — ENEM (T1.1 / T1.4)

## Inventário de anos (alvo 2016–2025, RN 6)

Fonte: `data/raw/inep/microdados_enem_AAAA/`.

{md(pd.DataFrame(linhas))}

- **Presentes:** {', '.join(map(str, presentes))}.
- **Ausentes:** {', '.join(map(str, ausentes))} ({len(ausentes)} de 10 anos). Nenhum ZIP desses anos foi encontrado no projeto nem em `~/Documentos/buildinpublic/` (que só repete 2023–2025). Os microdados antigos (2016–2022) precisam ser baixados da página oficial do INEP; o pipeline (`python src/enem.py`) só precisa que seus mapeamentos de colunas sejam acrescentados em `FONTES` (`src/enem.py`).
- Consequência: séries históricas (tendência 2016–2025) **não são possíveis** com os dados atuais; há só 3 anos consecutivos.

## T1.4 — Limitação de granularidade (código de escola)

1. **2023:** o arquivo único não tem código de escola (`CO_ESCOLA`); só município da escola (`CO_MUNICIPIO_ESC`, preenchido em ~24% das linhas) e `TP_ESCOLA`/`TP_DEPENDENCIA_ADM_ESC`. Granularidade: **município**.
2. **2024 e 2025:** o INEP separou a base em `PARTICIPANTES` (sexo, conclusão, Q005, renda, município da prova; **sem escola e sem notas**) e `RESULTADOS` (notas, **`CO_ESCOLA`**, município e dependência da escola; **sem sexo, renda ou Q005**).
   - O dicionário oficial afirma que `NU_SEQUENCIAL` ≠ `NU_INSCRICAO` e que **não é possível relacionar as duas bases**. Logo, nota × renda × sexo do mesmo aluno **não pode ser reconstruída** nesses anos.
   - `CO_ESCOLA` existe (obtido do Censo Escolar pelo CPF) para ~36% das linhas de resultados; é nulo para quem não concluiu/cursa o EM em escola recenseada. Escolas com < 10 participantes têm o código **mascarado** (prefixo `6`); sinalizadas em `co_escola_mascarado`.
   - Portanto, **nota por escola** é possível em 2024–2025 (via `RESULTADOS`), mas **renda/Q005 por escola não** — a renda só existe agregada por município da prova (participantes).
3. Para o restante do projeto: usar **município** como granularidade comum (`co_municipio_esc` para notas por escola-município; `co_municipio_prova` para perfil socioeconômico), e `co_escola` apenas como bônus em 2024–2025.
"""
    (DOCS / "lacunas_enem.md").write_text(txt, encoding="utf-8")


def gerar_dicionario() -> None:
    saida_cols = pd.DataFrame([
        ("ano", "NU_ANO (fixo no pipeline)", "Ano do Enem"),
        ("origem", "—", "`microdados` (2023), `participantes` ou `resultados` (2024+): de qual arquivo a linha veio"),
        ("co_escola", "CO_ESCOLA (RESULTADOS 2024+)", "Código INEP da escola (8 dígitos, str); nulo em 2023. Mascarado se escola < 10 participantes"),
        ("co_escola_mascarado", "derivado", "True se o código começa com 6 (máscara do INEP)"),
        ("co_municipio_esc / sg_uf_esc", "CO_MUNICIPIO_ESC / SG_UF_ESC", "Município (IBGE 7 dígitos, str) e UF da escola"),
        ("co_municipio_prova / sg_uf_prova", "CO_MUNICIPIO_PROVA / SG_UF_PROVA", "Município e UF onde fez a prova"),
        ("tp_escola", "TP_ESCOLA (só 2023)", "Tipo de escola do EM (autodeclarado)"),
        ("tp_sexo", "TP_SEXO (MICRODADOS 2023, PARTICIPANTES 2024+)", "M/F"),
        ("tp_st_conclusao", "TP_ST_CONCLUSAO", "Situação de conclusão do EM"),
        ("tp_dependencia_adm_esc", "TP_DEPENDENCIA_ADM_ESC", "Dependência administrativa da escola (nulo se sem escola)"),
        ("nu_nota_cn / ch / lc / mt", "NU_NOTA_CN/CH/LC/MT", "Notas: Ciências da Natureza, Ciências Humanas, Linguagens e Códigos, Matemática (nulo se ausente/eliminado)"),
        ("nu_nota_redacao", "NU_NOTA_REDACAO", "Nota da redação (0–1000)"),
        ("q005", "Q005", "Nº de pessoas na residência (1–20)"),
        ("q006", "Q006", "Como publicado. **2023:** renda familiar. **2024+:** \"Você possui renda?\" (A=Não, B=Sim)"),
        ("renda_familiar_faixa", "Q006 (2023) / Q007 (2024, 2025)", "Faixa de renda familiar A–Q, **harmonizada** (letras iguais, valores em R$ mudam por ano; ver abaixo)"),
    ], columns=["coluna", "variável original", "descrição"])
    pesos = "\n".join(f"- {a}: {r}" for a, r in [(2023, "faixas em múltiplos do SM de R$ 1.320"),
                                                  (2024, "SM R$ 1.412"), (2025, "SM R$ 1.518")])
    txt = f"""# Dicionário — ENEM (T1.3)

Fonte: dicionários oficiais do INEP (`microdados_enem_AAAA/**/Dicionário_*.xlsx`). Parquets em `data/interim/enem_AAAA.parquet` (+ `enem_all.parquet`).
Convenções: ver `convencoes.md`. Layout varia por ano: ver mapeamento em `src/enem.py` (`FONTES`).

## Colunas do parquet

{md(saida_cols)}

Colunas ausentes na origem de uma linha ficam **nulas**. Em 2024+ cada ano tem duas origens independentes (sem junção possível); agregue por `origem`.

## Categorias

### TP_SEXO
{tabela_cat(2023, 'MICRODADOS_ENEM_2023', 'TP_SEXO')}

### TP_ST_CONCLUSAO (2023; em 2024/2025 muda só o ano citado)
{tabela_cat(2023, 'MICRODADOS_ENEM_2023', 'TP_ST_CONCLUSAO')}

### TP_ESCOLA (apenas 2023)
{tabela_cat(2023, 'MICRODADOS_ENEM_2023', 'TP_ESCOLA')}

### TP_DEPENDENCIA_ADM_ESC
{tabela_cat(2025, 'RESULTADOS_2025', 'TP_DEPENDENCIA_ADM_ESC')}

### Q005 — pessoas na residência
Códigos 1 a 20: 1 = "moro sozinho(a)"; 2..20 = número de pessoas.

### Q006
- **2023** — renda mensal familiar (faixas A–Q):

{tabela_cat(2023, 'MICRODADOS_ENEM_2023', 'Q006')}

- **2024 e 2025** — "Você possui renda?":

{tabela_cat(2025, 'PARTICIPANTES_2025', 'Q006')}

### Renda familiar em 2024 (Q007)
{tabela_cat(2024, 'PARTICIPANTES_2024', 'Q007')}

### Renda familiar em 2025 (Q007)
{tabela_cat(2025, 'PARTICIPANTES_2025', 'Q007')}

Observações sobre renda (importante para T2.5):
{pesos}
- As letras A–Q são as mesmas nos três anos, mas os limites em R$ mudam com o salário mínimo; as faixas são **múltiplos do SM** (B = até 1 SM; C = 1–1,5 SM; D = 1,5–2 SM ...). Para o corte "≤ 1,5 SM por pessoa", combinar `renda_familiar_faixa` com `q005`.
- `renda_familiar_faixa` já aponta para a coluna certa de cada ano (Q006 em 2023, Q007 depois). Quem usar `q006` cru em 2024+ está lendo "possui renda?".

## Limitação T1.4
Ver `lacunas_enem.md`: sem junção aluno-a-aluno entre perfil e notas/escola em 2024–2025; `co_escola` só em RESULTADOS 2024+ e mascarado para escolas pequenas. Granularidade comum confiável: **município**.
"""
    (DOCS / "dicionario_enem.md").write_text(txt, encoding="utf-8")


def gerar_eda() -> None:
    P = f"'{ALL}'"
    vol_ano = q(f"SELECT ano, origem, COUNT(*) AS linhas FROM {P} GROUP BY 1,2 ORDER BY 1,2")
    vol_uf = q(f"""SELECT sg_uf_prova AS uf, ano, COUNT(*) n FROM {P} WHERE origem IN ('microdados','participantes')
                   GROUP BY 1,2""").pivot(index="uf", columns="ano", values="n").fillna(0).astype(int)
    vol_uf.loc["TOTAL"] = vol_uf.sum()
    vol_uf = vol_uf.reset_index()
    # nulos: so colunas que existem na origem
    cols = [c for c in enem.SAIDA_COLS if c not in ("ano", "origem")]
    exist = {}
    for a, fontes in enem.FONTES.items():
        for origem, _, mapa, renda in fontes:
            e = set(mapa) | ({"q006"} if origem != "resultados" else set()) | ({"renda_familiar_faixa"} if renda else set())
            if "co_escola" in mapa:
                e.add("co_escola_mascarado")
            exist[(a, origem)] = e
    nul_rows = []
    for (a, origem), e in exist.items():
        sel = ", ".join(f"100.0*AVG(CASE WHEN {c} IS NULL THEN 1 ELSE 0 END) AS {c}" for c in sorted(e))
        r = q(f"SELECT {sel} FROM {P} WHERE ano={a} AND origem='{origem}'").iloc[0]
        nul_rows.append({"ano": a, "origem": origem, **{c: f"{r[c]:.1f}" for c in r.index}})
    nul = pd.DataFrame(nul_rows).fillna("n/d")[["ano", "origem", *[c for c in cols if any(c in r for r in nul_rows)]]]
    # notas
    notas = []
    for n in NOTAS:
        d = q(f"""SELECT ano, COUNT({n}) AS n_validos, ROUND(AVG({n}),1) media, ROUND(STDDEV({n}),1) dp, MIN({n}) min,
                  ROUND(QUANTILE_CONT({n},0.25),1) p25, ROUND(MEDIAN({n}),1) mediana, ROUND(QUANTILE_CONT({n},0.75),1) p75, MAX({n}) max
                  FROM {P} WHERE {n} IS NOT NULL GROUP BY 1 ORDER BY 1""")
        d.insert(0, "nota", n.replace("nu_nota_", ""))
        notas.append(d)
    notas = pd.concat(notas)
    # escola publica
    tp23 = q(f"""SELECT tp_escola, COUNT(*) n, ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),1) pct
                 FROM {P} WHERE ano=2023 GROUP BY 1 ORDER BY 1""")
    tp23["tp_escola"] = tp23["tp_escola"].map({1: "1 Não respondeu", 2: "2 Pública", 3: "3 Privada"})
    dep = q(f"""SELECT ano, COUNT(*) AS linhas_resultados, COUNT(tp_dependencia_adm_esc) AS com_escola,
                ROUND(100.0*COUNT(tp_dependencia_adm_esc)/COUNT(*),1) AS pct_com_escola,
                SUM((tp_dependencia_adm_esc IN (1,2,3))::INT) AS publica, SUM((tp_dependencia_adm_esc=4)::INT) AS privada,
                ROUND(100.0*SUM((tp_dependencia_adm_esc IN (1,2,3))::INT)/COUNT(tp_dependencia_adm_esc),1) AS pct_publica_entre_com_escola
                FROM {P} WHERE (ano=2023 AND origem='microdados' AND tp_dependencia_adm_esc IS NOT NULL)
                   OR (ano>2023 AND origem='resultados') GROUP BY 1 ORDER BY 1""")
    dep23 = q(f"SELECT COUNT(*) n FROM {P} WHERE ano=2023").iloc[0, 0]
    dep.loc[dep.ano == 2023, ["linhas_resultados", "pct_com_escola"]] = [dep23, round(100 * dep.loc[dep.ano == 2023, "com_escola"].iloc[0] / dep23, 1)]
    dep = dep.astype({"linhas_resultados": int, "publica": int, "privada": int})
    pub_uf = q(f"""SELECT sg_uf_esc AS uf, ano, ROUND(100.0*SUM((tp_dependencia_adm_esc IN (1,2,3))::INT)/COUNT(*),1) pct
                   FROM {P} WHERE tp_dependencia_adm_esc IS NOT NULL AND ano=2025 AND origem='resultados' GROUP BY 1,2 ORDER BY 1""")
    esc = q(f"""SELECT ano, COUNT(DISTINCT co_escola) FILTER (WHERE NOT co_escola_mascarado) escolas_codigo_real,
                COUNT(DISTINCT co_escola) FILTER (WHERE co_escola_mascarado) codigos_mascara,
                SUM(co_escola_mascarado::INT) linhas_mascaradas FROM {P} WHERE co_escola IS NOT NULL GROUP BY 1 ORDER BY 1""")
    txt = f"""# EDA — ENEM (T1.2)

Base: `data/interim/enem_all.parquet` (anos {', '.join(map(str, sorted(vol_ano.ano.unique())))}; 2016–2022 ausentes, ver `lacunas_enem.md`).
Em 2024–2025 a base se divide em duas origens independentes (`participantes` e `resultados`) com o **mesmo número de linhas** mas **sem junção possível**.

## Volumetria

{md(vol_ano)}

### Inscritos por UF da prova (origem `microdados`/`participantes`)

{md(vol_uf)}

**Observação:** o RS tem 279 mil inscritos em 2024, contra 160 mil (2023) e 187 mil (2025) — valor atípico não explicado nos dados; não corrigido, verificar na fonte antes de usar RS em séries.

## % de nulos (somente colunas que existem na origem; `n/d` = coluna inexistente na origem)

Nulo em nota = ausente/eliminado na prova. `co_escola`/`*_esc` nulos = sem escola recenseada (não concluinte do EM, ou fora do Censo).

{md(nul)}

## Distribuição das notas (apenas valores não nulos)

{md(notas)}

## Cobertura de escola pública

### 2023 — `TP_ESCOLA` (autodeclarado, todas as linhas)

{md(tp23)}

`tp_escola` **não existe** em 2024/2025. A rede passa a vir de `tp_dependencia_adm_esc` (Censo Escolar, só em `resultados`; 1–3 = pública, 4 = privada):

{md(dep)}

(2023: `linhas_resultados` = total de linhas do microdados; escola identificada via `TP_DEPENDENCIA_ADM_ESC` preenchido.)
Atenção: 2023 (24% com escola) e 2024–2025 (36%) **não são diretamente comparáveis** — o percentual de escola pública entre quem tem escola sobe de 76% para 83–84%, o que pode refletir mudança de cobertura do vínculo com o Censo Escolar, não só da realidade.

### % de escola pública por UF da escola (2025, entre linhas com escola)

{md(pub_uf)}

### Escolas identificáveis (2024–2025)

{md(esc)}

Códigos mascarados agrupam escolas com < 10 participantes: não identificam escola individual.
"""
    (DOCS / "eda_enem.md").write_text(txt, encoding="utf-8")


def main() -> None:
    gerar_lacunas(enem.anos_presentes())
    gerar_dicionario()
    gerar_eda()
    print("docs gerados")


if __name__ == "__main__":
    main()
