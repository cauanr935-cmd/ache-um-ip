"""T2.10 - Pseudonimizacao (LGPD). Nome de aluno em claro NUNCA vai para data/processed.

* id_registro_hash = SHA-256(sal | nome_normalizado | ano | olimpiada): identifica o REGISTRO de premiacao.
* id_aluno_hash    = SHA-256(sal | aluno_key): identifica a PESSOA entre anos/olimpiadas (aluno_key vem da dedup:
  nome normalizado + municipio + escola). E um pseudonimo, nao anonimizacao: quem tem o sal e a lista de nomes
  consegue recomputar. Por isso o sal fica em config/lgpd.yaml, fora do Git.
* assert_sem_nomes: falha se algum valor de coluna textual de uma tabela processada coincide com um nome conhecido.
"""
import hashlib
from pathlib import Path

import pandas as pd
import yaml

from caminhos import RAIZ  # noqa: E402  (ACHE_RAIZ configura a raiz)
CONFIG = RAIZ / "config/lgpd.yaml"


def carregar_sal() -> str:
    if not CONFIG.exists():
        raise FileNotFoundError("config/lgpd.yaml ausente: copie config/lgpd.example.yaml e gere um sal (fora do Git)")
    sal = str(yaml.safe_load(CONFIG.read_text(encoding="utf-8")).get("sal", ""))
    if len(sal) < 32 or sal.startswith("TROQUE"):
        raise ValueError("sal invalido em config/lgpd.yaml (use >= 32 caracteres aleatorios)")
    return sal


def sha256(*partes, sal: str) -> str:
    return hashlib.sha256("|".join([sal, *map(str, partes)]).encode("utf-8")).hexdigest()


def hash_registro(nome_norm: pd.Series, ano: pd.Series, olimpiada: pd.Series, sal: str) -> pd.Series:
    return pd.Series([sha256(n, a, o, sal=sal) for n, a, o in zip(nome_norm, ano, olimpiada)], index=nome_norm.index)


def hash_aluno(aluno_key: pd.Series, sal: str) -> pd.Series:
    return pd.Series([sha256(k, sal=sal) for k in aluno_key], index=aluno_key.index)
