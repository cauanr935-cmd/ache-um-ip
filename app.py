"""Ache um IP: versão Streamlit para consulta dos dados agregados do mapa.

Lê só os JSON de data/api/ (que vão no repositório), com caminhos relativos a este arquivo. Não tem nomes de alunos:
medalhistas e alunos do Instituto Ponte ficam fora (data/privado e Redis, atrás do login do site principal).

Rodar:  streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ_API = Path(__file__).resolve().parent / "data" / "api"
NIVEIS_INSE = {"Todos": None, "Baixo (I a III)": ("I", "II", "III"), "Médio (IV e V)": ("IV", "V"), "Alto (VI e VII)": ("VI", "VII")}

st.set_page_config(page_title="Ache um IP", page_icon="🗺️", layout="wide")


@st.cache_data
def ler(*partes):
    return json.loads(RAIZ_API.joinpath(*partes).read_text(encoding="utf-8"))


@st.cache_data
def municipios():
    """código IBGE -> (nome, UF), a partir do índice de busca."""
    return {c: (nome, uf) for c, nome, uf in ler("busca.json")["municipios"]}


def tabela_mapa(prova, etapa, ano, rede, nivel, uf=None):
    caminho = ["mapa", f"{prova}_{etapa}_{ano}_{rede}", f"{uf or 'uf'}.json"]
    try:
        dados = ler(*caminho)
    except FileNotFoundError:
        return pd.DataFrame()
    df = pd.DataFrame(dados)
    if nivel == "uf":
        df["local"] = df["codigo"].map(ler("ufs.json"))  # código IBGE da UF -> sigla
    else:
        df["local"] = df["codigo"].map(lambda c: municipios().get(c, (c, ""))[0])
    return df


def formatar(df, casas):
    saida = df[["local", "valor", "n", "suprimido"]].rename(columns={"local": "Local", "valor": "Valor", "n": "n", "suprimido": "Dados insuficientes"})
    saida["Valor"] = saida["Valor"].round(casas)
    return saida


st.title("Ache um IP")
st.caption("Onde estão os talentos que o Instituto Ponte pode procurar. Dados públicos e agregados (INEP, IBGE, OBMEP, OBI, OCMAT); sem nomes de alunos.")

try:
    catalogo = ler("recortes.json")
except FileNotFoundError:
    st.error("Dados não encontrados em data/api. Gere-os com `python src/api_precompute.py`.")
    st.stop()

provas = catalogo["provas"]
aba_mapa, aba_escolas, aba_busca = st.tabs(["Ranking por local", "Escolas do município", "Buscar escola"])

# ---------------------------------------------------------------- ranking
with aba_mapa:
    c1, c2, c3, c4 = st.columns(4)
    chave = c1.selectbox("Prova", list(provas), format_func=lambda k: provas[k]["nome"])
    prova = provas[chave]
    etapa = c2.selectbox("Etapa", prova["etapas"], format_func=lambda e: {"ef2": "Ensino Fundamental 2", "em": "Ensino Médio"}[e])
    ano = c3.selectbox("Ano", prova["anos"], format_func=lambda a: "Todos (2016 a 2025)" if a == "todos" else str(a))
    ufs = ler("ufs.json")
    sigla = c4.selectbox("Nível", ["Estados"] + sorted(set(ufs.values())), help="Estados do Brasil ou municípios de uma UF")
    rede = "publica" if "publica" in prova["redes"] else prova["redes"][0]  # todos os alunos de interesse são de escola pública
    if prova.get("nota"):
        st.info(prova["nota"])

    df = tabela_mapa(chave, etapa, ano, rede, "uf" if sigla == "Estados" else "municipio", None if sigla == "Estados" else sigla)
    metrica = prova["metrica"]
    st.subheader(metrica["titulo"] + (", por UF" if sigla == "Estados" else f", municípios de {sigla}"))
    if df.empty:
        st.warning("Sem dados para este recorte.")
    else:
        validos = df[~df["suprimido"]].sort_values("valor", ascending=False)
        st.caption(f"{len(validos)} de {len(df)} locais com dado suficiente (n mínimo de {catalogo['n_min']}; nas olimpíadas, a partir de 1 medalha).")
        if len(validos):
            st.bar_chart(validos.head(30).set_index("local")["valor"], horizontal=True)
        st.dataframe(formatar(df.sort_values("valor", ascending=False, na_position="last"), metrica["casas"]), width="stretch", hide_index=True)

# ---------------------------------------------------------------- escolas do município
with aba_escolas:
    c1, c2, c3 = st.columns(3)
    uf = c1.selectbox("UF", sorted(set(ler("ufs.json").values())), index=sorted(set(ler("ufs.json").values())).index("ES"), key="uf_escolas")
    por_nome = {c: nome for c, (nome, u) in municipios().items() if u == uf}
    cod = c2.selectbox("Município", sorted(por_nome, key=por_nome.get), format_func=por_nome.get)
    grupo = c3.selectbox("INSE das escolas", list(NIVEIS_INSE), help="Nível socioeconômico da escola (INEP). Baixo = mais vulnerável.")
    etapa_e = st.radio("Etapa", ["em", "ef2"], format_func=lambda e: {"ef2": "Ensino Fundamental 2", "em": "Ensino Médio"}[e], horizontal=True)

    painel = ler("municipio", f"{uf}.json").get(cod)
    bloco = (painel or {}).get("escolas", {}).get(etapa_e)
    if not bloco:
        st.info("Nenhuma escola pública com nota do Saeb divulgada nesta etapa.")
    else:
        linhas = []
        for pos, e in enumerate(bloco["lista"], start=1):
            inse = e.get("inse")
            linhas.append({"#": pos, "INEP": e["inep"], "Escola": e["nome"], "Rede / selo": "Destaque ★" if e["destaque"] else e["rede"],
                           "Nota Saeb": e["nota"], "INSE": f"Nível {inse['nivel']} ({inse['valor']:.2f})" if inse else "-",
                           "_nivel": inse["nivel"] if inse else None})
        escolas = pd.DataFrame(linhas)
        niveis = NIVEIS_INSE[grupo]
        if niveis:
            escolas = escolas[escolas["_nivel"].isin(niveis)]
        st.caption(f"Ranking do Saeb {bloco['ano']}; {len(escolas)} escola(s). A posição (#) é a do ranking completo.")
        st.dataframe(escolas.drop(columns="_nivel"), width="stretch", hide_index=True)
        st.subheader("Contexto do município")
        ctx = painel["contexto"]
        ideb = ctx.get(etapa_e)
        st.write({"População (estimada)": painel["populacao"], "Ideb": ideb and ideb["ideb"], "Taxa de aprovação (%)": ideb and ideb["taxa_aprovacao"],
                  "ENEM, média": (ctx.get("enem") or {}).get("media"), "Renda até 1,5 SM, estimado (%)": (ctx.get("renda") or {}).get("pct_ate_1_5_sm")})

# ---------------------------------------------------------------- busca de escola
with aba_busca:
    consulta = st.text_input("Nome ou código INEP da escola", placeholder="Ex.: EEEFM, 3205200...")
    if len(consulta.strip()) >= 3:
        q = consulta.strip().lower()
        achadas = [e for e in ler("busca.json")["escolas"] if q in e[1].lower() or q in e[0]][:50]
        if not achadas:
            st.info("Nenhuma escola encontrada.")
        for inep, nome, cod_mun, uf_e in achadas:
            with st.expander(f"{nome} ({uf_e})"):
                ficha = ler("escola", f"{uf_e}.json").get(inep)
                if not ficha:
                    st.write("Sem ficha detalhada.")
                    continue
                inse = ficha.get("inse")
                st.write({"INEP": inep, "Rede": ficha["rede"], "Município": municipios().get(ficha["municipio"], ("-",))[0],
                          "INSE": f"Nível {inse['nivel']} ({inse['valor']:.2f}, {inse['ano']})" if inse else "-",
                          "Medalhistas vinculados": ficha["n_medalhistas"]})
                for et, serie in ficha["series"].items():
                    st.caption(f"Evolução, {'Ensino Médio' if et == 'em' else 'Ensino Fundamental 2'}")
                    st.dataframe(pd.DataFrame(serie), hide_index=True, width="stretch")
    else:
        st.caption("Digite pelo menos 3 caracteres.")
