# Decisões pendentes

## DP-1 — Saeb 2025 (T1.5)
- **Situação:** microdados do Saeb 2025 não estão listados na página oficial do INEP (verificado em 02/10/2026; última edição: 2023). Não há dados locais de 2025.
- **Decisão registrada:** **não será raspado do site** nem buscado por outros meios. As notas Saeb 2025 por escola/município já estão nas planilhas do Ideb 2025 (`nota_saeb_*` em `ideb_escola`/`ideb_municipio`) e cobrem a necessidade de proficiência recente.
- **Ação do responsável:** quando o INEP publicar, baixar o ZIP manualmente para `data/raw/inep/microdados_saeb_2025/` e acrescentar a edição em `EDICOES` de `src/saeb.py` (conferir se a estrutura de `TS_ESCOLA` mudou).

## DP-2 — Censo Escolar 2025 para `dim_escola_base` (T1.13) — **bloqueante**
- **Situação:** arquivo ausente localmente; `download.inep.gov.br` com certificado TLS não verificável a partir desta máquina.
- **Opções:** (a) você baixa o ZIP (`microdados_censo_escolar_2025_.zip`, link na página do Censo Escolar) para `data/raw/inep/microdados_censo_escolar_2025/` e o pipeline gera a tabela; (b) autorizar download com verificação TLS desativada (`curl -k`), aceitando o risco de integridade — conferir depois o hash/tamanho; (c) usar o Catálogo de Escolas (planilha) se estiver disponível por outro caminho.
- **Impacto:** sem a tabela-ponte não há `dim_escola_base` (nome, localização, rede detalhada, etapas) e T2.1/T2.3 (linkage de medalhistas) ficam parciais. O Ideb escola já dá `co_entidade`, nome, município, UF e rede (Federal/Estadual/Municipal/Privada) como alternativa mínima.

## DP-3 — INSE por escola e Taxa de Rendimento completa
- Arquivos oficiais do INEP (Indicadores Educacionais: INSE e Taxas de Rendimento) não estão locais. Baixar se for necessário ter INSE com código real de escola e reprovação/abandono. Ver `lacunas_saeb.md` §2–3.
