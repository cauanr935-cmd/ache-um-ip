"""T1.13 (PROVISORIO) - dim_escola_base a partir do Ideb escola, enquanto o Censo Escolar 2025 nao esta disponivel.

Cobertura: so escolas que aparecem no Ideb (EF2/EM, 2005-2025). Faltam escolas sem Ideb (muitas privadas, escolas
sem turma de EF2/EM avaliada), localizacao e etapas oferecidas. Quando o Censo chegar, regenerar a partir dele.
Colunas: co_entidade (8), no_escola, co_municipio (7), uf, rede (ultimo ano), rede_publica, ultimo_ano, fonte.
"""
from pathlib import Path

import duckdb

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
SAIDA = RAIZ / "data/interim/dim_escola_base.parquet"


def main() -> None:
    duckdb.sql(f"""COPY (
        SELECT co_entidade, no_escola, co_municipio, uf, rede, (rede <> 'Privada') AS rede_publica,
               ano AS ultimo_ano, 'ideb_escola' AS fonte
        FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY co_entidade ORDER BY ano DESC, etapa) AS rn
              FROM '{RAIZ / 'data/interim/ideb_escola.parquet'}')
        WHERE rn = 1 ORDER BY co_entidade) TO '{SAIDA}' (FORMAT parquet)""")
    print(duckdb.sql(f"SELECT COUNT(*) n, COUNT(DISTINCT co_entidade) k, SUM(rede_publica::INT) publicas FROM '{SAIDA}'"))


if __name__ == "__main__":
    main()
