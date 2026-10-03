"""T5.4 - Orquestracao: todas as etapas como funcoes, parametrizadas por ano e por caminho.

    import pipeline
    pipeline.configurar("/content/drive/MyDrive/ache-um-ip")   # raiz com data/, config/, docs/ (ANTES de rodar as etapas)
    pipeline.run_coleta(anos_enem=[2026], anos_saeb=None, baixar=False)
    pipeline.run_preprocessamento()
    pipeline.run_modelagem(ano_recortes=2026)
    pipeline.run_avaliacao()
    pipeline.run_deploy()
    pipeline.tempos()        # DataFrame com o tempo de cada etapa

Reexecutar quando sair a proxima edicao: coloque os microdados em data/raw/inep/, acrescente o ano em
src/enem.py (FONTES) / src/saeb.py (EDICOES) se o layout mudou e chame run_tudo(anos_enem=[...]).
Os modulos leem a raiz de `caminhos.py` na importacao; por isso `configurar` define ACHE_RAIZ e descarta os modulos ja importados.
"""
import importlib
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_TEMPOS: list[dict] = []
_PROPRIOS = {p.stem for p in _SRC.glob("*.py")} - {"pipeline"}


def configurar(raiz: str | Path | None = None) -> Path:
    """Define a raiz do projeto (pasta com data/, config/, docs/) e recarrega os modulos de src/ com ela."""
    if raiz is not None:
        os.environ["ACHE_RAIZ"] = str(Path(raiz).expanduser())
    for nome in list(sys.modules):
        if nome in _PROPRIOS:
            del sys.modules[nome]
    return _m("caminhos").RAIZ


def _m(nome: str):
    return importlib.import_module(nome)


@contextmanager
def _etapa(nome: str):
    t0 = time.perf_counter()
    print(f"[{nome}] ...", flush=True)
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        _TEMPOS.append({"etapa": nome, "segundos": round(dt, 1)})
        print(f"[{nome}] {dt:.1f}s", flush=True)


def tempos() -> pd.DataFrame:
    return pd.DataFrame(_TEMPOS, columns=["etapa", "segundos"])


# ----------------------------------------------------------------------------- Fase 2: coleta
def run_coleta(raiz=None, anos_enem: list[int] | None = None, anos_saeb: list[int] | None = None, baixar: bool = False) -> None:
    """ENEM/Saeb/Ideb/IBGE a partir de data/raw + listas de olimpiadas.

    anos_enem / anos_saeb: edicoes a converter (None = todas as presentes em data/raw/inep).
    baixar=False (padrao): nunca acessa a rede; olimpiadas so leem o cache HTML de data/raw/olimpiadas.
    baixar=True: permite baixar paginas de OBMEP/OBI que ainda nao estao em cache (os microdados do INEP NAO sao baixados aqui).
    """
    if raiz is not None:
        configurar(raiz)
    obmep = _m("coleta_obmep")
    obmep.OFFLINE = not baixar
    with _etapa("coleta: ENEM (CSV -> parquet)"):
        _m("enem").main(anos_enem)
    with _etapa("coleta: Saeb"):
        _m("saeb").main(anos_saeb)
    with _etapa("coleta: Ideb"):
        _m("ideb").main()
    with _etapa("coleta: IBGE (municipios + populacao)"):
        _m("geo").main()
    with _etapa("coleta: dim_escola_base"):
        _m("dim_escola_base").main()
    with _etapa("coleta: OBMEP"):
        obmep.main()
    with _etapa("coleta: OBI + medalhistas"):
        _m("medalhistas").main()  # coleta_obi usa coleta_obmep.baixar (respeita OFFLINE)
    with _etapa("coleta: EDA/dicionarios (ENEM, Saeb)"):
        _m("enem_docs").main()
        _m("saeb_docs").main()


# ----------------------------------------------------------------------------- Fase 3: pre-processamento
def run_preprocessamento(raiz=None) -> None:
    """Chaves, linkage, dedup, agregacoes e tabelas finais (dim_*/fato_*) com asserts e LGPD (hash com sal de config/lgpd.yaml)."""
    if raiz is not None:
        configurar(raiz)
    with _etapa("prep: auditoria de chaves"):
        _m("chaves").auditar_chaves()
    with _etapa("prep: record linkage"):
        _m("linkage").main()
    with _etapa("prep: deduplicacao"):
        _m("dedup").main()
    with _etapa("prep: agregacoes + supressao"):
        _m("agregacoes").main()
    with _etapa("prep: tabelas finais (dim_*/fato_*)"):
        _m("processed").main()
    with _etapa("prep: docs de chaves e linkage"):
        d = _m("docs_a")
        d.doc_chaves()
        d.doc_linkage()


# ----------------------------------------------------------------------------- Fase 4: modelagem
def run_modelagem(raiz=None, anos_qualidade: list[int] | None = None, ano_escola: int | None = None,
                  ano_recortes: int | None = None) -> dict:
    """Indice, clusters, residuos e rankings. Anos None = derivados dos dados (ultimas edicoes disponiveis)."""
    if raiz is not None:
        configurar(raiz)
    with _etapa("modelagem: indice, clusters, residuos, rankings"):
        return _m("modelagem").run_fase4(anos_qualidade, ano_escola, ano_recortes)


# ----------------------------------------------------------------------------- Fase 5: avaliacao
def run_avaliacao(raiz=None, resultado_modelagem: dict | None = None, anos_qualidade=None, ano_escola=None, ano_recortes=None):
    """Metricas, sensibilidade, vies, amostra de rotulagem (NAO sobrescreve rotulos ja preenchidos) e docs de avaliacao."""
    if raiz is not None:
        configurar(raiz)
    with _etapa("avaliacao: metricas, sensibilidade, vies, docs"):
        return _m("avaliacao").run_fase5(resultado_modelagem, anos_qualidade, ano_escola, ano_recortes)


# ----------------------------------------------------------------------------- Fase 6: deploy
def run_deploy(raiz=None, versao: str = "v1", duckdb_unico: bool = True) -> dict:
    """Exporta data/processed/<versao>/ (Parquet + CSV UTF-8 [+ ache_um_ip.duckdb]), confere LGPD e gera o dicionario de dados."""
    if raiz is not None:
        configurar(raiz)
    with _etapa("deploy: exportacao + checagens + dicionario"):
        return _m("deploy").exportar(versao, duckdb_unico)


def run_tudo(raiz=None, anos_enem=None, anos_saeb=None, baixar=False, anos_qualidade=None, ano_escola=None,
             ano_recortes=None, versao="v1") -> pd.DataFrame:
    """Todas as etapas em sequencia; devolve o DataFrame de tempos."""
    if raiz is not None:
        configurar(raiz)
    run_coleta(None, anos_enem, anos_saeb, baixar)
    run_preprocessamento()
    r = run_modelagem(None, anos_qualidade, ano_escola, ano_recortes)
    run_avaliacao(None, r)
    run_deploy(None, versao)
    return tempos()
