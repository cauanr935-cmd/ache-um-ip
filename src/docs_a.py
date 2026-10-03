"""T2.1-T2.4 - Gera docs/chaves_e_normalizacao.md e docs/linkage.md a partir dos dados (sem nomes de aluno).
Pre-requisitos: python src/linkage.py && python src/dedup.py. Uso: python src/docs_a.py"""
from pathlib import Path

import pandas as pd

import chaves
import dedup
import linkage
from enem_docs import md

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
DOCS = RAIZ / "docs"
EXEMPLOS = ["E M E F INSTITUTO NOSSA SENHORA", "EEEFM Prof. Joao da Silva", "COL MILITAR TIRADENTES", "EM Dr. Ana Neri",
            "CIEP 123 Brizolao", "CEF 28 DE CEILANDIA", "EREM Professor Ernesto Silva", "UNID ESCOLA ANISIO DE ABREU"]


def doc_chaves() -> None:
    cfg = linkage.carregar_config()
    aud = chaves.auditar_chaves()
    m = pd.read_parquet(linkage.MEDALHISTAS)
    r = chaves.anexar_co_municipio(m, "municipio_nome", "uf")
    por = r.groupby(["olimpiada", "ano", "match_municipio"]).size().unstack(fill_value=0)
    for c in ("exato", "fuzzy", "ambiguo", "sem_match"):
        if c not in por:
            por[c] = 0
    por["linhas"] = por.sum(axis=1)
    por["% com município"] = (100 * (por["exato"] + por["fuzzy"]) / por["linhas"]).round(2)
    por = por.reset_index()[["olimpiada", "ano", "linhas", "exato", "fuzzy", "ambiguo", "sem_match", "% com município"]]
    pares = r.attrs["pares_fuzzy"].copy()
    nfz = r[r.match_municipio == "fuzzy"].groupby(["municipio_nome", "uf"]).size().rename("linhas").reset_index()
    sem = (r[r.match_municipio.isin(["sem_match", "ambiguo"])].assign(municipio_norm=lambda d: d.municipio_nome.map(chaves.normalizar_nome_municipio))
           .groupby(["municipio_norm", "uf", "match_municipio"]).size().rename("linhas").reset_index().sort_values("linhas", ascending=False))
    siglas = pd.DataFrame(sorted(chaves.SIGLAS.items()), columns=["sigla (token)", "expansão"])
    ex = pd.DataFrame({"original": EXEMPLOS, "normalizado": [chaves.normalizar_texto(e) for e in EXEMPLOS],
                       "núcleo": [chaves.nome_nucleo(e) for e in EXEMPLOS]})
    txt = f"""# Chaves e normalização de texto (T2.1–T2.2)

Código: `src/chaves.py` (`auditar_chaves()`, `normalizar_texto()`, `anexar_co_municipio()` …). Regenerar este documento: `python src/docs_a.py`.

## Regras de chave (ver também `convencoes.md`)
- **Município:** código IBGE de 7 dígitos, `string` (`co_municipio`; no ENEM `co_municipio_prova` e `co_municipio_esc`).
- **Escola:** `co_entidade` INEP de 8 dígitos, `string` (no ENEM, `co_escola`).
- **Ano:** inteiro.
- **Saeb:** `id_escola_saeb` e `id_municipio_saeb` são **máscaras** (códigos fictícios, dicionário oficial); só o *formato* é auditado — **não** são chaves INEP/IBGE e não entram em integridade referencial.
- Listas de olimpíadas **não têm código**: município é obtido por (nome normalizado + UF) contra `dim_municipio_base`.

## Auditoria das bases em `data/interim` (todas passam)
`auditar_chaves()` verifica tipo `VARCHAR`, formato por regex, nulos permitidos, unicidade das dimensões e integridade referencial (municípios do Ideb/ENEM/`dim_escola_base` ∈ `dim_municipio_base`; escolas do Ideb ∈ `dim_escola_base`).

{md(aud)}

`co_municipio_esc` e `co_escola` do ENEM têm nulos por desenho (estudante sem escola recenseada; `co_escola` só em RESULTADOS 2024–25).

## Normalização de texto
Função `normalizar_texto`: caixa alta → remoção de acentos (`unidecode`) → pontuação vira espaço → junta letras soltas no início/fim (`E M E F` → `EMEF`, `E M` → `EM`) → expande siglas (token inteiro). `EM` só é expandido (Escola Municipal) **no início** do nome, por ser ambíguo com Ensino Médio. `nome_nucleo` remove palavras genéricas (tipo/rede/etapa/títulos) e serve de guarda no linkage. `normalizar_nome_municipio` remove preposições e `D` isolado (`D'OESTE`). `normalizar_nome_pessoa` remove acentos e partículas (DE/DA/DO/DAS/DOS/E).

Exemplos (nomes de escola, sem dados de aluno):

{md(ex)}

### Siglas expandidas
{md(siglas)}

## Match de município nas listas de olimpíadas
Exato por (nome normalizado, UF); fallback **fuzzy só na mesma UF** com dobra fonética (Z=S, J=G, Y=I, K=C, W=V, H mudo, letras dobradas), `fuzz.ratio ≥ {chaves.FUZZY_MIN}` e margem ≥ {chaves.FUZZY_MARGEM} sobre o 2º candidato; na dúvida, `sem_match`.

{md(por)}

Pares aplicados pelo fallback fuzzy (município da lista → município IBGE):

{md(pares.merge(nfz.assign(municipio_norm=nfz.municipio_nome.map(chaves.normalizar_nome_municipio)).groupby(["municipio_norm", "uf"], as_index=False)["linhas"].sum(), on=["municipio_norm", "uf"], how="left"))}

**Resíduo sem match** (não inventado; em geral são municípios que mudaram de nome — ex.: Augusto Severo → Campo Grande-RN, Picarras → Balneário Piçarras — ou grafias distantes):

{md(sem)}
"""
    (DOCS / "chaves_e_normalizacao.md").write_text(txt, encoding="utf-8")


def doc_linkage() -> None:
    cfg = linkage.carregar_config()
    m = linkage.preparar_medalhistas(cfg)
    res = pd.read_parquet(linkage.PROCESSED / "linkage_resultado.parquet")
    rev = pd.read_csv(linkage.PROCESSED / "linkage_revisao_manual.csv", dtype=str)
    t_ano = linkage.taxas_por_linhas(m, res, ["olimpiada", "ano"])
    t_rede = linkage.taxas_por_linhas(m, res, ["olimpiada", "rede_grp"])
    t_ol = linkage.taxas_por_linhas(m, res, ["olimpiada"])

    def strings(by):
        x = res.assign(cat=res.link_status.where(res.motivo.ne("sem_municipio"), "sem_municipio"))
        t = x.groupby(by + ["cat"]).size().unstack(fill_value=0)
        for c in ("auto", "revisao", "sem_match", "sem_municipio"):
            if c not in t:
                t[c] = 0
        t["strings"] = t[["auto", "revisao", "sem_match", "sem_municipio"]].sum(axis=1)
        for c in ("auto", "revisao", "sem_match", "sem_municipio"):
            t[f"% {c}"] = (100 * t[c] / t["strings"]).round(1)
        return t.reset_index()[by + ["strings", "% auto", "% revisao", "% sem_match", "% sem_municipio"]]

    s_ol, s_rede = strings(["olimpiada"]), strings(["olimpiada", "rede_grp"])
    motivos = res.groupby(["link_status", "motivo"], dropna=False).agg(strings=("n_linhas", "size"), linhas=("n_linhas", "sum")).reset_index()
    rev_mot = rev.groupby("motivo").size().rename("strings").reset_index()
    exemplos = []
    for st in ("auto", "revisao", "sem_match"):
        x = res[(res.link_status == st) & res.co_entidade.notna()] if st != "sem_match" else res[(res.link_status == st) & (res.motivo == "score_baixo")]
        for _, r in x.sample(min(3, len(x)), random_state=4).iterrows():
            exemplos.append({"status": st, "escola (lista)": r.escola_norm, "candidata (Ideb)": r.no_escola_cand or "—", "score": r.link_score})
    # dedup
    _, alunos, st = dedup.enriquecer()
    dist = alunos["n_premios"].value_counts().sort_index().head(8).rename_axis("premiações distintas").reset_index(name="alunos")
    dist["alunos"] = dist["alunos"].astype(int)
    txt = f"""# Record linkage medalhista → escola e deduplicação (T2.3–T2.4)

Código: `src/linkage.py`, `src/dedup.py`, `src/chaves.py`; parâmetros: `config/linkage.yaml`; este documento: `python src/docs_a.py`.
Saídas: `data/processed/linkage_resultado.parquet` (nível **string de escola**, sem aluno), `data/processed/linkage_revisao_manual.csv` (sem aluno), `data/interim/medalhistas_enriquecido.parquet` e `aluno_dedup.parquet` (interim, com nome; a T2.10 aplica o hash).

> **Limitação estrutural.** O catálogo de escolas disponível é o **`dim_escola_base` provisório, derivado do Ideb** ({len(pd.read_parquet(linkage.DIM_ESCOLA)):,} escolas; só **{int(pd.read_parquet(linkage.DIM_ESCOLA).rede.eq('Privada').sum()):,} privadas**), porque o Censo Escolar não está disponível. Escolas privadas e escolas sem Ideb **não têm onde casar**: ficam `sem_match` por construção. A taxa de linkage deve ser lida **separadamente para rede pública**; para a privada ela é baixa por falta de catálogo, não por falha do método.

## Método
1. **Município:** (nome normalizado + UF) → `co_municipio` (`chaves.anexar_co_municipio`; exato + fuzzy conservador na mesma UF).
2. **Chave de linkage:** `(olimpiada, escola_norm, co_municipio, uf, rede_grp)` — o linkage é feito por **string única de escola** ({len(res):,} strings para {len(m):,} linhas) e depois propagado às linhas.
3. **Blocking:** só escolas do **mesmo município**; se a rede do medalhista é conhecida (OBMEP: F/E/M → pública; P → privada; C e OBI: sem rede) restringe aos candidatos de rede compatível (`usar_rede`).
4. **Score:** `rapidfuzz.fuzz.token_set_ratio` entre nomes normalizados (siglas expandidas).
5. **Guardas contra falso positivo.** `token_set_ratio` dá 100 quando um nome é subconjunto do outro (ex.: *Parque X II* vs *Parque X*), e é alto quando só o final difere (*Santa Luzia* vs *Santa Fé*). Se qualquer guarda falhar, o score é limitado a {cfg['limiar_auto'] - 0.1} (**revisão, nunca automático**): (a) núcleos (sem palavras genéricas) com `token_sort_ratio ≥ {cfg['guarda_subconjunto']['min_token_sort_nucleo']}`, `token_set_ratio ≥ {cfg['guarda_subconjunto']['min_token_set_nucleo']}` e razão de comprimento ≥ {cfg['guarda_subconjunto']['min_razao_comprimento_nucleo']}; (b) conjunto de números/algarismos romanos ≥ II igual (*CEF 24* ≠ *CEF 28*; *Campus II* ≠ *III*); (c) dependência explícita diferente (Estadual × Municipal × Federal).
6. **Decisão:** score ≥ {cfg['limiar_auto']} → `auto`; {cfg['limiar_revisao']} ≤ score < {cfg['limiar_auto']} → `revisao`; abaixo → `sem_match`. **Empate** (outro candidato com score ≥ limiar dentro de {cfg['margem_empate']} pontos e `fuzz.ratio` dentro de {cfg['margem_empate_secundario']}) → `revisao` (motivo `empate`).

Não há rótulo manual para calcular precisão: a validação foi por **amostragem visual** de vínculos automáticos nas faixas de score mais baixas (que revelou e corrigiu falsos positivos: número diferente, final diferente, subconjunto) — a precisão formal vem da amostra de ~200 registros da T4.1.

## Taxas de linkage (propagadas às linhas de medalhista)
Categorias: `auto`, `revisao`, `sem_match` (município ok) e `sem_municipio` (não casou município).

### Por olimpíada
{md(t_ol)}

### Por olimpíada e rede (pública × privada)
{md(t_rede)}

### Por olimpíada e ano
{md(t_ano)}

## Taxas em strings únicas de escola
### Por olimpíada
{md(s_ol)}

### Por olimpíada e rede
{md(s_rede)}

## Fila de revisão manual
`data/processed/linkage_revisao_manual.csv`: **{len(rev):,} strings** de escola (cobrem {int(res.loc[res.link_status == 'revisao', 'n_linhas'].sum()):,} linhas de medalhista), ordenadas por nº de linhas; traz até 3 candidatas com score e a coluna `decisao_manual` para preencher. Fila por motivo:

{md(rev_mot)}

Resultado por motivo (todas as strings):

{md(motivos)}

## Exemplos (nomes de escola, sem dados de aluno)
{md(pd.DataFrame(exemplos))}

## Deduplicação de alunos (T2.4, RF 2.5)
**Identidade** = nome normalizado + `co_municipio` + escola (`co_entidade` se o vínculo é `auto`; senão `escola_norm`). `aluno_key` = blake2b determinístico dessa identidade (id **interno**; não é o hash de LGPD). Premiação distinta = (olimpíada, ano, modalidade, nível, medalha). Contagens por aluno: `n_premios`, `n_ouro`, `n_prata`, `n_bronze`, `n_mencao`, `n_medalhas` (ouro+prata+bronze, sem menção), `n_olimpiadas`, `n_anos`, `primeiro_ano`, `ultimo_ano`.

| métrica | valor |
|---|---|
| linhas de medalhista | {st['linhas']:,} |
| alunos únicos (`aluno_key`) | {st['alunos_unicos']:,} |
| alunos com mais de 1 premiação | {st['alunos_com_mais_de_1_premio']:,} |
| alunos em mais de 1 ano | {st['alunos_em_mais_de_1_ano']:,} |
| alunos em mais de 1 olimpíada (OBMEP e OBI) | {st['alunos_em_mais_de_1_olimpiada']:,} |
| máximo de premiações de um aluno | {st['max_premios_um_aluno']} |
| linhas duplicadas exatas | {st['linhas_duplicadas_exatas']} |

{md(dist)}

**Colisão provável (não fundida):** {st['grupos_nome_municipio_com_varias_escolas']:,} grupos (nome + município) aparecem com **mais de uma escola** ({st['alunos_nesses_grupos']:,} identidades). Pode ser troca de escola entre anos, grafia diferente da mesma escola (quando o vínculo não é automático) ou homônimo. Em {st['grupos_com_homonimo_certo_mesmo_ano']} grupos o mesmo nome aparece em escolas diferentes **no mesmo ano, olimpíada e nível** (homônimos quase certos). Esses casos **não são fundidos**: a contagem acumulada é conservadora (tende a subcontar quem mudou de escola) e a identidade só funde quando município e escola coincidem.

## Limitações
- Catálogo provisório (Ideb): privadas e escolas sem Ideb não vinculam; **retomar com o Censo Escolar** muda as taxas.
- Sem rótulos para precisão/recall: ver T4.1.
- Estudantes que mudam de escola ou cuja escola é grafada de modo muito diferente entre anos viram identidades distintas.
- Homônimos na mesma escola e município são fundidos (limite do método sem outros atributos).
- OBI não tem `rede`: candidatos de qualquer rede no município.
"""
    (DOCS / "linkage.md").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    doc_chaves()
    doc_linkage()
    print("docs ok")
