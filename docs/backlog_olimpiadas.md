# Backlog de olimpíadas (T1.12)

Olimpíadas do levantamento inicial **fora do escopo confirmado da sprint** (OBMEP, OBI e ONHB são o escopo). Levantamento por busca web em 02/10/2026; **nenhuma lista foi baixada** e os formatos abaixo vêm de resultados de busca, não de inspeção das listas — validar antes de planejar a coleta.

| Olimpíada | Organização / fonte | O que a busca mostrou | Formato provável das listas | Esforço estimado | Observações |
|---|---|---|---|---|---|
| **OBM** — Olimpíada Brasileira de Matemática | OBM (`obm.org.br`) | Páginas "Premiados" por edição (de 2001 a 2025); um PDF de resultado de 2025 hospedado por um IF | HTML por ano e/ou PDF | Médio | Competição diferente da OBMEP (seleção para olimpíadas internacionais); volume pequeno (premiados nacionais). Verificar se traz escola/cidade. |
| **OBF** — Olimpíada Brasileira de Física | Sociedade Brasileira de Física (SBF); portal `app.graxaim.org/obf/<ano>` | Existe desde 1999; três fases; portal por ano | Provavelmente HTML/PDF no portal; não verificado | Médio | Confirmar se a lista é pública sem login. |
| **OBQ** — Olimpíada Brasileira de Química | ABQ; Programa Nacional Olimpíadas de Química (`obquimica.org`) | Arquivo de resultados por ano e fase (2013–2024, com lacunas), ~24 medalhas nacionais por edição | **PDF** por ano/fase | Alto (PDF) | Há também coordenações estaduais (ex.: PE, RN) com listas próprias. |
| **OBA** — Olimpíada Brasileira de Astronomia e Astronáutica | SAB + Agência Espacial Brasileira (`oba.org.br`, `sistema.oba.org.br`) | Volume enorme: 50.619 medalhas (2023), 81.153 (2024); distribuição por escola | Relatórios em PDF; resultados por escola em sistema próprio (acesso por escola/login) | Alto | Provavelmente só agregados públicos; lista nominal não verificada. Muitas "medalhas" são por escola (não são seletivas) — cuidar da comparabilidade. |
| **OFMAT** | **Não identificada** | A busca não encontrou uma olimpíada com esse nome | — | — | Perguntar à coordenação do IP a que olimpíada se refere (organizador/site) antes de qualquer trabalho. |
| **Maratona Cactus** | Citada na página da NOIC (`noic.com.br/olimpiadas/maratona-cactus/`) | Premiação por equipes (ouro/prata/bronze); segunda fase por nível | Não identificado | Desconhecido | Organizador e site oficial não confirmados. Unidade = equipe. |
| **MANDACARU** — Olimpíada Mandacaru de Matemática | Organização não confirmada; divulgada por secretarias e colégios | Do 4º ano do EF ao EM; resultados definitivos previstos para 14/07/2026; listas de premiados em **PDF** hospedados em sites de governos estaduais (ex.: CE) | PDF por estado/órgão | Alto (PDF, dispersos) | Listas fragmentadas por órgão; investigar se há lista nacional central. |

## Critérios para priorizar (sugestão)
1. Lista nacional única, pública, em HTML (menor esforço): OBM.
2. Lista com escola e município (para o linkage T2.3): verificar em OBM, OBF e OBQ.
3. Evitar, num primeiro momento, PDFs dispersos (MANDACARU, OBQ) e olimpíadas com volume inflado por escola (OBA).

## Premissas de integração
Mesmo esquema de `medalhistas.parquet` (`olimpiada, ano, nivel, modalidade, medalha, nome, escola_nome, rede, municipio_nome, uf, posicao`), nome em claro só em `data/interim`, mesmas regras de coleta (HTML baixado uma vez, pausa de 1,5 s, User-Agent identificado).
