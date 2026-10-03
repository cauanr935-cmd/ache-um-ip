"""T1.5 - Saeb -> data/interim/saeb_escola.parquet (uma linha por ano x escola x etapa).

Fonte das medias/n: TS_ESCOLA.csv de cada edicao (medias oficiais do INEP por escola, escala Saeb).
INSE do aluno (media por escola): TS_ALUNO_9EF / TS_ALUNO_34EM, so 2021 e 2023 (antes nao existe INSE_ALUNO).
Etapas: EF2 = 9o ano EF; EM = 3a serie EM (em 2017 colunas *_3EM, depois *_EM).
O Saeb nao traz dependencia administrativa: rede = publica/privada (IN_PUBLICA).

ATENCAO: ID_ESCOLA e ID_MUNICIPIO do Saeb sao MASCARAS ("codigos ficticios", dicionario oficial; prefixo 6).
Nao casam com co_entidade INEP nem com municipio IBGE (0% de sobreposicao com Ideb/ENEM). Por isso as colunas
se chamam id_escola_saeb / id_municipio_saeb; so a UF e real. Notas Saeb por escola com codigo real: ideb_escola.
"""
from pathlib import Path

import duckdb

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
RAW = RAIZ / "data/raw/inep"
SAIDA = RAIZ / "data/interim/saeb_escola.parquet"

# ano -> (pasta, separador, sufixo da etapa EM nas colunas, INSE do aluno disponivel)
EDICOES = {
    2017: ("microdados_saeb_2017", ",", "3EM", False),
    2019: ("microdados_saeb_2019", ";", "EM", False),
    2021: ("microdados_saeb_2021_ensino_fundamental_e_medio", ";", "EM", True),
    2023: ("microdados_saeb_2023", ";", "EM", True),
}
UF = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI", 23: "CE",
      24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP",
      41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}


def arquivo(pasta: str, nome: str) -> Path:
    achados = list((RAW / pasta).rglob(nome))
    if not achados:
        raise FileNotFoundError(f"{nome} em {pasta}")
    return achados[0]


def _leitura(path: Path, sep: str) -> str:
    return f"read_csv('{path}', delim='{sep}', header=true, all_varchar=true, encoding='latin-1', strict_mode=false)"


def _inse_aluno(con, ano: int, pasta: str, sep: str) -> None:
    """Cria a tabela inse_{ano}(etapa, id_escola_saeb, inse_aluno_medio, n_alunos_inse)."""
    partes = []
    for etapa, nome in (("EF2", "TS_ALUNO_9EF.csv"), ("EM", "TS_ALUNO_34EM.csv")):
        partes.append(f"""SELECT '{etapa}' AS etapa, LPAD(TRIM(ID_ESCOLA), 8, '0') AS id_escola_saeb,
            AVG(TRY_CAST(NULLIF(TRIM(INSE_ALUNO), '') AS DOUBLE)) AS inse_aluno_medio,
            COUNT(TRY_CAST(NULLIF(TRIM(INSE_ALUNO), '') AS DOUBLE)) AS n_alunos_inse
            FROM {_leitura(arquivo(pasta, nome), sep)} WHERE TRIM(IN_INSE) = '1' GROUP BY 1, 2""")
    con.execute(f"CREATE OR REPLACE TABLE inse_{ano} AS {' UNION ALL '.join(partes)}")


def _escola(con, ano: int) -> str:
    pasta, sep, em, tem_inse = EDICOES[ano]
    ufs = ", ".join(f"({k}, '{v}')" for k, v in UF.items())
    base = f"""(SELECT *, LPAD(TRIM(ID_ESCOLA), 8, '0') AS _esc FROM {_leitura(arquivo(pasta, 'TS_ESCOLA.csv'), sep)})"""
    sel = []
    for etapa, suf in (("EF2", "9EF"), ("EM", em)):
        # 2017 nao tem NU_MATRICULADOS_CENSO_3EM
        matr = f"TRY_CAST(NULLIF(TRIM(NU_MATRICULADOS_CENSO_{suf}), '') AS INTEGER)" if not (ano == 2017 and etapa == "EM") else "NULL"
        sel.append(f"""SELECT {ano} AS ano, _esc AS id_escola_saeb, LPAD(TRIM(ID_MUNICIPIO), 7, '0') AS id_municipio_saeb,
            u.sg AS uf, CASE TRIM(IN_PUBLICA) WHEN '1' THEN 'publica' WHEN '0' THEN 'privada' END AS rede,
            CASE TRIM(ID_LOCALIZACAO) WHEN '1' THEN 'urbana' WHEN '2' THEN 'rural' END AS localizacao,
            '{etapa}' AS etapa,
            TRY_CAST(NULLIF(TRIM(MEDIA_{suf}_LP), '') AS DOUBLE) AS proficiencia_lp,
            TRY_CAST(NULLIF(TRIM(MEDIA_{suf}_MT), '') AS DOUBLE) AS proficiencia_mt,
            TRY_CAST(NULLIF(TRIM(NU_PRESENTES_{suf}), '') AS INTEGER) AS n_alunos,
            {matr} AS n_matriculados_censo,
            NULLIF(TRIM(NIVEL_SOCIO_ECONOMICO), '') AS inse_escola,
            '{'grupo' if ano == 2017 else 'nivel'}' AS inse_escala
            FROM {base} e JOIN (VALUES {ufs}) u(cod, sg) ON TRY_CAST(e.ID_UF AS INTEGER) = u.cod""")
    uni = " UNION ALL ".join(sel)
    if tem_inse:
        _inse_aluno(con, ano, pasta, sep)
        return f"""SELECT t.*, i.inse_aluno_medio, i.n_alunos_inse FROM ({uni}) t
                   LEFT JOIN inse_{ano} i USING (etapa, id_escola_saeb)"""
    return f"SELECT t.*, NULL::DOUBLE AS inse_aluno_medio, NULL::BIGINT AS n_alunos_inse FROM ({uni}) t"


def main(anos: list[int] | None = None) -> None:
    """`anos`: edicoes do Saeb (chaves de EDICOES) a processar; padrao = todas."""
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    partes = [f"SELECT * FROM ({_escola(con, a)}) WHERE n_alunos IS NOT NULL OR proficiencia_lp IS NOT NULL" for a in (anos or EDICOES)]
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ({' UNION ALL '.join(partes)} ORDER BY ano, etapa, id_escola_saeb) TO '{SAIDA}' (FORMAT parquet, COMPRESSION zstd)")
    print(con.sql(f"SELECT ano, etapa, COUNT(*) FROM '{SAIDA}' GROUP BY 1,2 ORDER BY 1,2"))


if __name__ == "__main__":
    main()
