"""T2.3 - Record linkage medalhista -> escola (dim_escola_base), em nivel de STRING de escola.

Chave de linkage: (olimpiada, escola_norm, co_municipio, uf, rede_grp). Blocking por co_municipio.
Scorer: rapidfuzz token_set_ratio + guarda anti-subconjunto (ver config/linkage.yaml e docs/linkage.md).
Saidas (sem nome de aluno): data/processed/linkage_resultado.parquet, data/processed/linkage_revisao_manual.csv.
Uso: python src/linkage.py
"""
from pathlib import Path

import pandas as pd
import yaml
from rapidfuzz import fuzz, process

import chaves

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
CONFIG = RAIZ / "config/linkage.yaml"
MEDALHISTAS = RAIZ / "data/interim/medalhistas.parquet"
DIM_ESCOLA = RAIZ / "data/interim/dim_escola_base.parquet"
PROCESSED = RAIZ / "data/processed"
STATUS = {"auto", "revisao", "sem_match"}


def carregar_config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def preparar_medalhistas(cfg: dict | None = None) -> pd.DataFrame:
    """medalhistas + row_id, escola_norm, nome_norm, co_municipio, match_municipio, rede_grp (reaproveitado por dedup.py)."""
    cfg = cfg or carregar_config()
    m = pd.read_parquet(MEDALHISTAS).reset_index(drop=True)
    m.insert(0, "row_id", range(len(m)))
    m = chaves.anexar_co_municipio(m, "municipio_nome", "uf")
    m["escola_norm"] = m["escola_nome"].map(chaves.normalizar_texto)
    m["nome_norm"] = m["nome"].map(chaves.normalizar_nome_pessoa)
    pub, priv = set(cfg["rede_publica"]), set(cfg["rede_privada"])
    m["rede_grp"] = m["rede"].map(lambda r: "publica" if r in pub else "privada" if r in priv else "desconhecida")
    return m


def _preparar_dim(dim: pd.DataFrame) -> pd.DataFrame:
    d = dim.copy()
    d["norm"] = d["no_escola"].map(chaves.normalizar_texto)
    d["core"] = d["no_escola"].map(chaves.nome_nucleo)
    return d


def _guarda(core_a: str, core_b: str, g: dict) -> bool:
    if not g.get("ativa", True):
        return True
    la, lb = len(core_a), len(core_b)
    if max(la, lb) == 0:
        return False
    return (fuzz.token_sort_ratio(core_a, core_b) >= g["min_token_sort_nucleo"]
            and fuzz.token_set_ratio(core_a, core_b) >= g.get("min_token_set_nucleo", 0)
            and min(la, lb) / max(la, lb) >= g["min_razao_comprimento_nucleo"])


_DEP = {"ESTADUAL", "MUNICIPAL", "FEDERAL"}
_ROMANOS = {"II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"}


def _numeros(norm: str) -> set[str]:
    """Tokens numericos (digitos ou romanos >= II): 'CEF 24 DE X' != 'CEF 28 DE X'; 'CAMPUS II' != 'CAMPUS III'."""
    return {t for t in norm.split() if t.isdigit() or t in _ROMANOS}


def _conflito_dep(a: str, b: str) -> bool:
    da, db = _DEP & set(a.split()), _DEP & set(b.split())
    return bool(da) and bool(db) and da.isdisjoint(db)


def vincular(chaves_str: pd.DataFrame, dim: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """chaves_str: colunas olimpiada, escola_norm, co_municipio, uf, rede_grp (unicas). Devolve uma linha por chave."""
    la, lr, marg = cfg["limiar_auto"], cfg["limiar_revisao"], cfg["margem_empate"]
    top = cfg["top_candidatos"]
    d = _preparar_dim(dim)
    por_mun = {k: g.reset_index(drop=True) for k, g in d.groupby("co_municipio")}
    scorer = getattr(fuzz, cfg["scorer"])
    saida = []
    for r in chaves_str.itertuples(index=False):
        base = {"olimpiada": r.olimpiada, "escola_norm": r.escola_norm, "co_municipio": r.co_municipio, "uf": r.uf,
                "rede_grp": r.rede_grp, "link_status": "sem_match", "link_score": None, "co_entidade": None,
                "no_escola_cand": None, "cand2_co_entidade": None, "cand2_no_escola": None, "cand2_score": None,
                "cand3_co_entidade": None, "cand3_no_escola": None, "cand3_score": None,
                "motivo": None, "n_candidatos_mun": 0}
        if pd.isna(r.co_municipio) or r.co_municipio is None:
            base["motivo"] = "sem_municipio"
            saida.append(base)
            continue
        c = por_mun.get(r.co_municipio)
        if c is not None and cfg["usar_rede"] and r.rede_grp != "desconhecida":
            c = c[c["rede_publica"] == (r.rede_grp == "publica")].reset_index(drop=True)
        if c is None or c.empty or not r.escola_norm:
            base["motivo"] = "sem_candidato_no_municipio" if (c is None or c.empty) else "nome_vazio"
            saida.append(base)
            continue
        base["n_candidatos_mun"] = len(c)
        scores = process.cdist([r.escola_norm], c["norm"].tolist(), scorer=scorer)[0]
        order = scores.argsort()[::-1][:max(top, 3)]
        core_a = chaves.nome_nucleo(r.escola_norm)
        cands = []
        for i in order:
            s_raw = float(scores[i])
            ok = _guarda(core_a, c.at[i, "core"], cfg["guarda_subconjunto"])
            if cfg.get("conflito_dependencia", True) and _conflito_dep(r.escola_norm, c.at[i, "norm"]):
                ok = False
            if cfg.get("guarda_numerica", True) and _numeros(r.escola_norm) != _numeros(c.at[i, "norm"]):
                ok = False
            s_eff = s_raw if ok or s_raw < la else la - 0.1  # guarda falhou: teto abaixo do auto
            sec = float(fuzz.ratio(r.escola_norm, c.at[i, "norm"]))
            cands.append((s_eff, s_raw, ok, c.at[i, "co_entidade"], c.at[i, "no_escola"], sec))
        cands.sort(key=lambda x: (-x[0], -x[5], -x[1]))
        best = cands[0]
        base.update(link_score=round(best[0], 1), co_entidade=best[3], no_escola_cand=best[4])
        for n, cd in enumerate(cands[1:3], start=2):
            base[f"cand{n}_co_entidade"], base[f"cand{n}_no_escola"], base[f"cand{n}_score"] = cd[3], cd[4], round(cd[0], 1)
        if best[0] >= la:
            fortes = [x for x in cands[1:] if x[0] >= la and best[0] - x[0] <= marg and best[5] - x[5] <= cfg["margem_empate_secundario"]
                      and x[3] != best[3]]
            if fortes:
                base["link_status"], base["motivo"] = "revisao", "empate"
            else:
                base["link_status"] = "auto"
        elif best[0] >= lr:
            base["link_status"] = "revisao"
            base["motivo"] = "guarda" if (not best[2] and best[1] >= la) else "score_intermediario"
        else:
            base["co_entidade"] = base["no_escola_cand"] = base["cand2_co_entidade"] = base["cand2_no_escola"] = None
            base["cand2_score"] = base["cand3_co_entidade"] = base["cand3_no_escola"] = base["cand3_score"] = None
            base["motivo"] = "score_baixo"
        saida.append(base)
    out = pd.DataFrame(saida)
    assert out["link_status"].isin(STATUS).all()
    return out


def taxas_por_linhas(m: pd.DataFrame, res: pd.DataFrame, por: list[str]) -> pd.DataFrame:
    j = m.merge(res[["olimpiada", "escola_norm", "co_municipio", "uf", "rede_grp", "link_status", "motivo"]],
                on=["olimpiada", "escola_norm", "co_municipio", "uf", "rede_grp"], how="left")
    j["cat"] = j["link_status"].where(j["motivo"].ne("sem_municipio"), "sem_municipio")
    t = j.groupby(por + ["cat"], dropna=False).size().unstack("cat", fill_value=0)
    for c in ("auto", "revisao", "sem_match", "sem_municipio"):
        if c not in t:
            t[c] = 0
    t["linhas"] = t[["auto", "revisao", "sem_match", "sem_municipio"]].sum(axis=1)
    for c in ("auto", "revisao", "sem_match", "sem_municipio"):
        t[f"% {c}"] = (100 * t[c] / t["linhas"]).round(1)
    return t.reset_index()[por + ["linhas", "% auto", "% revisao", "% sem_match", "% sem_municipio"]]


def main() -> None:
    cfg = carregar_config()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    m = preparar_medalhistas(cfg)
    dim = pd.read_parquet(DIM_ESCOLA)
    chave = ["olimpiada", "escola_norm", "co_municipio", "uf", "rede_grp"]
    g = m.groupby(chave, dropna=False)
    ks = g.agg(n_linhas=("row_id", "size"), ano_min=("ano", "min"), ano_max=("ano", "max")).reset_index()
    res = vincular(ks[chave], dim, cfg).merge(ks, on=chave, how="left")
    assert len(res) == len(ks) and not res.duplicated(chave).any()
    assert res["n_linhas"].sum() == len(m)
    res["ano_min"], res["ano_max"] = res["ano_min"].astype("int16"), res["ano_max"].astype("int16")
    res.to_parquet(PROCESSED / "linkage_resultado.parquet", index=False)
    # fila de revisao (sem nome de aluno)
    mun = pd.read_parquet(RAIZ / "data/interim/dim_municipio_base.parquet")[["co_municipio", "no_municipio"]]
    rev = res[res.link_status == "revisao"].merge(mun, on="co_municipio", how="left").sort_values("n_linhas", ascending=False)
    cols = {"olimpiada": "olimpiada", "uf": "uf", "co_municipio": "co_municipio", "no_municipio": "municipio",
            "escola_norm": "escola_medalhista_norm", "rede_grp": "rede_grp", "n_linhas": "n_linhas", "motivo": "motivo",
            "co_entidade": "cand1_co_entidade", "no_escola_cand": "cand1_nome", "link_score": "cand1_score",
            "cand2_co_entidade": "cand2_co_entidade", "cand2_no_escola": "cand2_nome", "cand2_score": "cand2_score",
            "cand3_co_entidade": "cand3_co_entidade", "cand3_no_escola": "cand3_nome", "cand3_score": "cand3_score"}
    rev = rev[list(cols)].rename(columns=cols)
    rev["decisao_manual"] = ""  # preencher: co_entidade escolhido ou NENHUMA
    rev.to_csv(PROCESSED / "linkage_revisao_manual.csv", index=False, encoding="utf-8")
    print(res.link_status.value_counts().to_dict(), "| fila de revisao:", len(rev), "strings")
    print(taxas_por_linhas(m, res, ["olimpiada"]).to_string())


if __name__ == "__main__":
    main()
