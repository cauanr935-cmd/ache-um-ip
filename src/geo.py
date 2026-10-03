"""T1.14 - dim_municipio_base a partir de data/raw/ibge/ (API Localidades + SIDRA).

Fontes (baixadas em data/raw/ibge/):
  localidades_municipios.json        API Localidades (id IBGE 7 digitos, nome, UF, regiao)
  sidra_censo2022_pop_t4714.json     Censo 2022, tabela 4714, variavel 93 (populacao residente)
  sidra_estimativa_pop_t6579.json    Estimativas, tabela 6579, variavel 9324 (ano mais recente publicado)
  BR_Municipios_2025.zip             malha municipal (shapefile) para o mapa da proxima sprint
"""
import json
from pathlib import Path

import pandas as pd

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
IBGE = RAIZ / "data/raw/ibge"
SAIDA = RAIZ / "data/interim/dim_municipio_base.parquet"


def _sidra(arquivo: str, coluna: str) -> pd.DataFrame:
    d = json.loads((IBGE / arquivo).read_text(encoding="utf-8"))[1:]
    df = pd.DataFrame({"co_municipio": [x["D1C"].zfill(7) for x in d],
                       coluna: pd.to_numeric(pd.Series([x["V"] for x in d]), errors="coerce").astype("Int64"),
                       "_ano": [int(x["D3C"]) for x in d]})
    return df


def main() -> None:
    loc = json.loads((IBGE / "localidades_municipios.json").read_text(encoding="utf-8"))
    def uf_de(m: dict) -> dict:  # municipio novo pode vir sem microrregiao: usa regiao-imediata
        if m.get("microrregiao"):
            return m["microrregiao"]["mesorregiao"]["UF"]
        return m["regiao-imediata"]["regiao-intermediaria"]["UF"]

    base = pd.DataFrame([{
        "co_municipio": str(m["id"]).zfill(7), "no_municipio": m["nome"],
        "uf": uf_de(m)["sigla"], "regiao": uf_de(m)["regiao"]["sigla"]} for m in loc])
    censo = _sidra("sidra_censo2022_pop_t4714.json", "populacao")
    est = _sidra("sidra_estimativa_pop_t6579.json", "populacao_estimada")
    ano_est = int(est["_ano"].iloc[0])
    assert est["_ano"].nunique() == 1
    out = (base.merge(censo[["co_municipio", "populacao"]], how="left", on="co_municipio")
           .merge(est[["co_municipio", "populacao_estimada"]], how="left", on="co_municipio"))
    out["ano_populacao"] = 2022
    out["ano_populacao_estimada"] = ano_est
    assert out["co_municipio"].is_unique and out["co_municipio"].str.len().eq(7).all()
    out.sort_values("co_municipio").to_parquet(SAIDA, index=False)
    print(SAIDA, out.shape, "sem populacao censo:", int(out.populacao.isna().sum()),
          "sem estimativa:", int(out.populacao_estimada.isna().sum()), "| ano estimativa", ano_est)


if __name__ == "__main__":
    main()
