"""Marca os medalhistas de ensino médio, para quem vale a regra de elegibilidade do IP (config/elegibilidade.yaml)."""
import re
import unicodedata

import yaml

from caminhos import RAIZ

_CFG = yaml.safe_load((RAIZ / "config/elegibilidade.yaml").read_text(encoding="utf-8"))
_ETAPAS_EM = set(_CFG["etapas_ensino_medio"])
_PADROES = [re.compile(p) for p in _CFG["padroes_escola_ensino_medio"]]


def _sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).upper()) if unicodedata.category(c) != "Mn")


def escola_de_ensino_medio(nome):
    n = _sem_acento(nome)
    return any(p.search(n) for p in _PADROES)


def ensino_medio(etapa, escola_nome):
    """True se o medalhista estava no ensino médio (ou além) quando ganhou a medalha."""
    if etapa in _ETAPAS_EM:
        return True
    if etapa == _CFG["etapa_ambigua"]:
        return escola_de_ensino_medio(escola_nome)
    return False  # ensino fundamental: a regra não vale
