"""Passo 5 do specs.md: pre-computa os JSON que a API serve (specs.md 6.2).

Le data/interim/agg_*.parquet e escreve em data/api/ (ignorado pelo git, regeneravel):
  recortes.json                       catalogo do que existe (provas, etapas, anos, redes)
  mapa/<prova>_<etapa>_<ano>_<rede>/<uf|SIGLA>.json   [{codigo, valor, n, suprimido}]
  municipio/<SIGLA>.json              painel por municipio (escolas, contexto, medalhas agregadas)
  ufs.json                            codigo IBGE da UF -> sigla

Nenhum arquivo contem nome de aluno (so agregados e nomes de escolas, que sao publicos).
  busca.json                          indice de busca (municipios e escolas)
  escola/<SIGLA>.json                 ficha da escola (serie historica de nota, Ideb e aprovacao)
Fora do data/api (privado, gitignored):
  data/privado/medalhistas/<SIGLA>.json   lista de medalhistas POR MUNICIPIO, com nome em claro.
      O servidor so entrega o nome se ALUNO_IDENTIFICADO=true; senao entrega o pseudonimo (specs.md 7).
Uso: python src/api_precompute.py
"""
import json
import shutil

import numpy as np
import pandas as pd
import yaml

from caminhos import RAIZ
from elegibilidade import ensino_medio
from lgpd import carregar_sal, sha256
from recortes import anexar_etapa

INTERIM = RAIZ / "data/interim"
SAIDA = RAIZ / "data/api"
PRIVADO = RAIZ / "data/privado/medalhistas"
_SUPRESSAO = yaml.safe_load((RAIZ / "config/supressao.yaml").read_text(encoding="utf-8"))
N_MIN = _SUPRESSAO["n_min_padrao"]
N_MIN_OLIMPIADAS = _SUPRESSAO["n_min_olimpiadas"]  # contagem de medalhas é a própria métrica; ver supressao.yaml
ANO_MIN_OLIMPIADA, ANO_MAX_OLIMPIADA = 2016, 2025  # janela de 10 anos (RN 6)
PERCENTIL_DESTAQUE = 0.9  # escola destaque provisoria: top 10% da UF na etapa (specs.md 4.6, [ABERTO])
MEDALHAS_VALIDAS = ["Ouro", "Prata", "Bronze"]  # menção honrosa não conta como medalha
ETAPAS_DE = {"ef2": {"EF2", "EF2_EM"}, "em": {"EM", "EF2_EM"}}  # EF2_EM (misto) entra nas duas

MOTIVO_SEXO = "Esta base não traz o recorte por sexo nas notas e nas medalhas."
MOTIVO_RENDA = "Esta base não cruza renda com nota ou medalha por aluno; o proxy de renda aparece só no contexto do município."


# Página oficial de onde vieram os medalhistas de cada edição. Os endereços saem de https://www.obmep.org.br/premiados.htm
# e de https://olimpiada.ic.unicamp.br/passadas/; o ano das edições 16ª a 18ª está em config/obmep_anos.yaml.
FONTE_OBMEP = {
    2016: "2016/mapa_premiacao_content.htm", 2017: "2017/mapa_premiacao_content.htm", 2018: "2018/mapa.htm", 2019: "2019/mapa.htm",
    2021: "16aobmep/mapa.htm", 2022: "17obmep/mapa.htm", 2023: "18obmep/mapa.htm", 2024: "19obmep/mapa.htm", 2025: "20obmep/mapa.htm",
}


def fonte_oficial(olimpiada, ano):
    if olimpiada == "OBMEP" and ano in FONTE_OBMEP:
        return "http://premiacao.obmep.org.br/" + FONTE_OBMEP[ano]
    if olimpiada == "OBI":
        return f"https://olimpiada.ic.unicamp.br/passadas/OBI{ano}/"
    return None


def num(x, casas=2):
    return None if x is None or pd.isna(x) else round(float(x), casas)


def registros(df, valor, n, casas=2, n_min=N_MIN):
    """[{codigo, valor, n, suprimido}]. Sem valor ou com n < n_min vira suprimido, valor nulo."""
    saida = []
    for codigo, v, k in zip(df["codigo"], df[valor], df[n]):
        k = None if pd.isna(k) else int(k)
        sup = pd.isna(v) or (k is not None and k < n_min)
        saida.append({"codigo": str(codigo), "valor": None if sup else num(v, casas), "n": k, "suprimido": bool(sup)})
    return saida


def gravar(caminho, obj):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# ---------- Carga ----------
dim = pd.read_parquet(INTERIM / "dim_municipio_base.parquet")
dim["co_municipio"] = dim["co_municipio"].astype(str)
UF_DE = dict(zip(dim["co_municipio"], dim["uf"]))
POP = dict(zip(dim["co_municipio"], dim["populacao_estimada"]))
UF_COD = {m[:2]: uf for m, uf in UF_DE.items()}
UFS = sorted(set(UF_DE.values()))

prof_mun = pd.read_parquet(INTERIM / "agg_proficiencia_municipio.parquet")
prof_mun["co_municipio"] = prof_mun["co_municipio"].astype(str)
prof_uf = pd.read_parquet(INTERIM / "agg_proficiencia_uf.parquet")
prof_esc = pd.read_parquet(INTERIM / "agg_proficiencia_escola.parquet")
prof_esc["co_municipio"] = prof_esc["co_municipio"].astype(str)
prof_esc["co_entidade"] = prof_esc["co_entidade"].astype(str)
enem = pd.read_parquet(INTERIM / "agg_enem_municipio.parquet")
enem["co_municipio"] = enem["co_municipio"].astype(str)
med = pd.read_parquet(INTERIM / "agg_medalhas_municipio.parquet")
med["co_municipio"] = med["co_municipio"].astype(str)

for pasta_antiga in (SAIDA, PRIVADO):
    if pasta_antiga.exists():
        shutil.rmtree(pasta_antiga)
gravar(SAIDA / "ufs.json", UF_COD)

catalogo = {"n_min": N_MIN, "provas": {}, "sexo": {"valores": ["todos"], "motivo": MOTIVO_SEXO},
            "renda": {"disponivel": False, "motivo": MOTIVO_RENDA}}


def emitir(prova, etapa, ano, rede, uf_df, mun_df, n_min=N_MIN):
    """Grava o nivel UF e um arquivo por UF (municipios). Os dois ja com colunas codigo, valor, n."""
    pasta = SAIDA / "mapa" / f"{prova}_{etapa}_{ano}_{rede}"
    gravar(pasta / "uf.json", registros(uf_df, "valor", "n", n_min=n_min))
    mun_df = mun_df.assign(uf=mun_df["codigo"].map(UF_DE))
    for uf, parte in mun_df.groupby("uf"):
        gravar(pasta / f"{uf}.json", registros(parte, "valor", "n", n_min=n_min))


# ---------- Saeb (Ideb por municipio, microdados Saeb por UF) ----------
def media_saeb(df):
    return df[["nota_saeb_lp", "nota_saeb_mt"]].mean(axis=1, skipna=False)


anos_saeb = sorted(int(a) for a in prof_uf["ano"].unique() if a >= 2016)  # UF so existe ate 2023
catalogo["provas"]["saeb"] = {
    "nome": "Saeb", "etapas": ["ef2", "em"], "anos": sorted(anos_saeb, reverse=True), "redes": ["publica"],
    "metrica": {"titulo": "Nota média no Saeb (LP e MT), escolas públicas", "curta": "pontos no Saeb", "casas": 1},
}
cod_uf = {v: k for k, v in UF_COD.items()}
for etapa in ("EF2", "EM"):
    for ano in anos_saeb:
        m = prof_mun[(prof_mun.etapa == etapa) & (prof_mun.ano == ano) & (prof_mun.rede == "Pública")]
        m = pd.DataFrame({"codigo": m["co_municipio"], "valor": media_saeb(m), "n": np.nan})
        u = prof_uf[(prof_uf.etapa == etapa) & (prof_uf.ano == ano) & (prof_uf.rede_grupo == "publica")]
        u = pd.DataFrame({"codigo": u["uf"].map(cod_uf), "valor": (u["proficiencia_lp_media"] + u["proficiencia_mt_media"]) / 2, "n": u["n"]})
        emitir("saeb", etapa.lower(), ano, "publica", u, m)

# ---------- ENEM (municipio da escola; nunca por escola) ----------
cols_media = ["media_cn", "media_ch", "media_lc", "media_mt", "media_redacao"]
anos_enem = sorted(enem["ano"].unique(), reverse=True)
catalogo["provas"]["enem"] = {
    "nome": "ENEM", "etapas": ["em"], "anos": [int(a) for a in anos_enem], "redes": ["publica", "todas"],
    "motivo_etapa": "O ENEM só avalia o Ensino Médio.",
    "metrica": {"titulo": "Nota média no ENEM (média das cinco provas)", "curta": "pontos no ENEM", "casas": 1},
}
for rede in ("publica", "todas"):
    for ano in anos_enem:
        e = enem[(enem.visao == "desempenho_escola") & (enem.ano == ano) & (enem.rede_grupo == rede)].copy()
        e = e[~e["suprimido"].astype(bool)]
        e["valor"] = e[cols_media].mean(axis=1, skipna=False)
        e = e.dropna(subset=["valor"])
        m = pd.DataFrame({"codigo": e["co_municipio"], "valor": e["valor"], "n": e["n"]})
        e["uf"] = e["co_municipio"].map(UF_DE)
        u = e.groupby("uf").apply(lambda g: pd.Series({"valor": np.average(g["valor"], weights=g["n"]), "n": g["n"].sum()}), include_groups=False)
        u = u.reset_index().assign(codigo=lambda d: d["uf"].map(cod_uf))[["codigo", "valor", "n"]]
        emitir("enem", "em", int(ano), rede, u, m)

# ---------- Olimpiadas (medalhas por 100 mil habitantes) ----------
med = med[med.medalha.isin(MEDALHAS_VALIDAS) & med.ano.between(ANO_MIN_OLIMPIADA, ANO_MAX_OLIMPIADA)]
nomes_olimpiada = {"OBMEP": ("OBMEP", ["publica", "todas"]), "OBI": ("OBI", ["todas"])}  # OBI não informa a rede da escola
for chave, (olimp, redes) in nomes_olimpiada.items():
    catalogo["provas"][chave.lower()] = {
        "nome": olimp, "etapas": ["ef2", "em"], "anos": ["todos"] + list(range(ANO_MAX_OLIMPIADA, ANO_MIN_OLIMPIADA - 1, -1)),
        "redes": redes, "motivo_rede": "A OBI não informa a rede da escola." if chave == "OBI" else None,
        "metrica": {"titulo": f"Medalhas na {olimp} por 100 mil habitantes", "curta": "medalhas/100 mil hab.", "casas": 1},
    }
    for etapa, grupo in ETAPAS_DE.items():
        base = med[(med.olimpiada == olimp) & med.etapa.isin(grupo)]
        for rede in redes:
            b = base if rede == "todas" else base[base.rede_grupo == rede]
            for ano in ["todos"] + list(range(ANO_MAX_OLIMPIADA, ANO_MIN_OLIMPIADA - 1, -1)):
                bb = b if ano == "todos" else b[b.ano == ano]
                # Soma o n bruto e aplica N_MIN sobre o total publicado (a celula de origem ja pode estar suprimida).
                m = bb.groupby("co_municipio")["n"].sum().reindex(dim["co_municipio"], fill_value=0).rename("n").reset_index()
                m["valor"] = m["n"] / m["co_municipio"].map(POP) * 100000
                m = m.rename(columns={"co_municipio": "codigo"})
                u = m.assign(uf=m["codigo"].map(UF_DE), pop=m["codigo"].map(POP)).groupby("uf").agg(n=("n", "sum"), pop=("pop", "sum")).reset_index()
                u["valor"] = u["n"] / u["pop"] * 100000
                u["codigo"] = u["uf"].map(cod_uf)
                emitir(chave.lower(), etapa, ano, rede, u[["codigo", "valor", "n"]], m[["codigo", "valor", "n"]], n_min=N_MIN_OLIMPIADAS)

gravar(SAIDA / "recortes.json", catalogo)

# ---------- Painel do municipio ----------
# Escolas: edicao mais recente de cada etapa, so rede publica, com nota (LP/MT) divulgada.
esc = prof_esc[(prof_esc.rede_grupo == "publica") & (prof_esc.ano >= 2016)].copy()
esc["nota"] = media_saeb(esc)
esc = esc.dropna(subset=["nota"])
ano_esc = esc.groupby("etapa")["ano"].max().to_dict()

ctx_prof = prof_mun[(prof_mun.rede == "Pública") & (prof_mun.ano >= 2016)]
ultimo_ideb = ctx_prof.sort_values("ano").groupby(["co_municipio", "etapa"]).tail(1).set_index(["co_municipio", "etapa"])
ano_enem = int(max(anos_enem))
enem_ctx = enem[(enem.visao == "desempenho_escola") & (enem.ano == ano_enem) & (enem.rede_grupo == "publica") & ~enem.suprimido.astype(bool)].set_index("co_municipio")
renda_ctx = enem[(enem.visao == "perfil_prova") & (enem.ano == ano_enem) & ~enem.suprimido.astype(bool)].set_index("co_municipio")
med_tot = med.groupby(["co_municipio", "olimpiada", "medalha"])["n"].sum()

# Medalhistas individuais (so em data/privado). Escola vinculada so quando o linkage foi automatico.
mi = pd.read_parquet(INTERIM / "medalhistas_enriquecido.parquet")
mi = mi[~mi["linha_duplicada"] & mi["medalha"].isin(MEDALHAS_VALIDAS) & mi["ano"].between(ANO_MIN_OLIMPIADA, ANO_MAX_OLIMPIADA) & mi["co_municipio"].notna()].copy()
SAL = carregar_sal()
COM_MEDALHISTA = set(mi["co_entidade"].dropna().astype(str))  # escola destaque tambem por >= 1 medalhista (specs.md 4.6)

for uf in UFS:
    painel = {}
    for co in dim.loc[dim.uf == uf, "co_municipio"]:
        painel[co] = {"populacao": None if pd.isna(POP[co]) else int(POP[co]), "escolas": {}, "contexto": {}, "medalhas": []}
    for etapa, grupo in esc[(esc.uf == uf)].groupby("etapa"):
        grupo = grupo[grupo.ano == ano_esc[etapa]]
        corte = grupo["nota"].quantile(PERCENTIL_DESTAQUE)
        for co, g in grupo.groupby("co_municipio"):
            if co not in painel:
                continue
            g = g.sort_values("nota", ascending=False)
            painel[co]["escolas"][etapa.lower()] = {
                "ano": int(ano_esc[etapa]),
                "lista": [{"inep": r.co_entidade, "nome": r.no_escola, "rede": str(r.rede_detalhe or r.rede).capitalize(),
                           "nota": num(r.nota, 1), "destaque": bool(r.nota >= corte or r.co_entidade in COM_MEDALHISTA)} for r in g.itertuples()],
            }
    for co, d in painel.items():
        for etapa in ("EF2", "EM"):
            if (co, etapa) in ultimo_ideb.index:
                r = ultimo_ideb.loc[(co, etapa)]
                d["contexto"][etapa.lower()] = {"ano": int(r["ano"]), "ideb": num(r["ideb"], 1), "taxa_aprovacao": num(r["taxa_aprovacao"], 1)}
        if co in enem_ctx.index:
            r = enem_ctx.loc[co]
            d["contexto"]["enem"] = {"ano": ano_enem, "media": num(r[cols_media].mean(), 1)}
        if co in renda_ctx.index:
            r = renda_ctx.loc[co]
            d["contexto"]["renda"] = {"ano": ano_enem, "pct_ate_1_5_sm": num(r["pct_renda_pc_le_1_5_ponto_medio"], 1)}  # estimado
        if co in med_tot.index.get_level_values(0):
            for (olimp, medalha), n in med_tot.loc[co].items():
                if n >= N_MIN_OLIMPIADAS:
                    d["medalhas"].append({"olimpiada": olimp, "medalha": medalha, "n": int(n)})
    gravar(SAIDA / "municipio" / f"{uf}.json", painel)

# ---------- Busca (specs.md 4.5) ----------
nomes_escola = prof_esc.sort_values("ano").groupby("co_entidade").tail(1).set_index("co_entidade")
escolas_busca = nomes_escola[nomes_escola["rede_grupo"] == "publica"].reset_index()
gravar(SAIDA / "busca.json", {
    "municipios": [[co, nome, uf] for co, nome, uf in zip(dim["co_municipio"], dim["no_municipio"], dim["uf"])],
    "escolas": [[r.co_entidade, r.no_escola, r.co_municipio, r.uf] for r in escolas_busca.itertuples() if r.no_escola],
})

# ---------- Ficha da escola ----------
ficha = prof_esc[(prof_esc.rede_grupo == "publica") & (prof_esc.ano >= 2016)].copy()
ficha["lp"], ficha["mt"] = ficha["nota_saeb_lp"], ficha["nota_saeb_mt"]
ficha = ficha.dropna(subset=["lp", "mt", "ideb"], how="all").sort_values("ano")
n_medalhistas_escola = mi.dropna(subset=["co_entidade"]).groupby("co_entidade")["aluno_key"].nunique()
for uf, grupo in ficha.groupby("uf"):
    fichas = {}
    for inep, g in grupo.groupby("co_entidade"):
        ultimo = g.iloc[-1]
        series = {}
        for etapa, ge in g.groupby("etapa"):
            series[etapa.lower()] = [{"ano": int(r.ano), "lp": num(r.lp, 1), "mt": num(r.mt, 1), "ideb": num(r.ideb, 1),
                                       "aprovacao": num(r.taxa_aprovacao, 1)} for r in ge.itertuples()]
        fichas[inep] = {"nome": ultimo["no_escola"], "rede": str(ultimo["rede_detalhe"] or ultimo["rede"]).capitalize(),
                        "municipio": ultimo["co_municipio"], "uf": uf, "series": series,
                        "tem_medalhista": inep in COM_MEDALHISTA,
                        "n_medalhistas": int(n_medalhistas_escola.get(inep, 0))}
    gravar(SAIDA / "escola" / f"{uf}.json", fichas)

# ---------- Medalhistas por municipio (privado) ----------
def iniciais(nome):
    return ".".join(p[0] for p in str(nome).split() if p) + "."

mi["id_aluno"] = [sha256(k, sal=SAL)[:6].upper() for k in mi["aluno_key"]]
mi["pseudonimo"] = [f"{iniciais(n)} #{i}" for n, i in zip(mi["nome"], mi["id_aluno"])]
mi["escola_inep"] = mi["co_entidade"]
nome_escola_inep = nomes_escola["no_escola"].to_dict()
mi["escola"] = [nome_escola_inep.get(e) or str(raw).title() for e, raw in zip(mi["escola_inep"], mi["escola_nome"])]
ordem = {"Ouro": 0, "Prata": 1, "Bronze": 2}
mi["_o"] = mi["medalha"].map(ordem)
mi = anexar_etapa(mi)
mi["ensino_medio"] = [ensino_medio(e, n) for e, n in zip(mi["etapa"], mi["escola_nome"])]
for uf, grupo in mi.groupby("uf"):
    por_municipio = {}
    for co, g in grupo.sort_values(["_o", "ano"], ascending=[True, False]).groupby("co_municipio"):
        por_municipio[co] = [{"pseudonimo": r.pseudonimo, "nome": r.nome, "medalha": r.medalha, "olimpiada": r.olimpiada,
                              "ano": int(r.ano), "escola": r.escola, "escola_inep": None if pd.isna(r.escola_inep) else r.escola_inep,
                              "fonte": fonte_oficial(r.olimpiada, int(r.ano)), "ensino_medio": bool(r.ensino_medio)}
                             for r in g.itertuples()]
    gravar(PRIVADO / f"{uf}.json", por_municipio)

print("ok:", sum(1 for _ in SAIDA.rglob("*.json")), "arquivos em", SAIDA)
