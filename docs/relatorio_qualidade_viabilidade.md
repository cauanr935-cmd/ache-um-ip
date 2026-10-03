# Relatório de qualidade e viabilidade dos dados (T1.19)

Data: 02/10/2026 · Escopo: frentes ENEM, Saeb/Ideb/indicadores, Olimpíadas, Chaves e Geo, MEC/Secretarias e Interno do IP (Fase 2).
Fontes deste relatório: `docs/progresso.md`, `docs/lacunas.md`, `lacunas_enem.md`, `lacunas_saeb.md`, `lacunas_olimpiadas.md`, `decisoes_pendentes.md` e os parquets em `data/interim/`.

> **Nota sobre os RF.** O `plano.md` não define o texto dos requisitos. Os rótulos usados aqui vêm da tabela de rastreabilidade do documento "Divisão de Tasks" (24/09/2026). **O RF 5.2 não aparece nessa tabela** e não foi avaliado; os requisitos completos devem ser conferidos com o documento de requisitos original.

## 1. Veredito
**Viável com restrições.** Há dado suficiente para o núcleo do projeto (índice por **município**: Ideb/Saeb por escola e município, ENEM por município, população, malha, medalhistas OBMEP/OBI). Três limitações moldam a próxima fase:
1. **Linkage medalhista → escola (RF 2.5) ainda não é possível:** as listas trazem só nomes de escola e falta a tabela-ponte do Censo (T1.13 bloqueada). Sem ela, o vínculo é por **município/UF** (por nome).
2. **Granularidade de renda e sexo é município, não escola:** no ENEM 2024–2025 perfil e notas/escola não se juntam; os códigos de escola do Saeb são fictícios.
3. **Cobertura temporal incompleta (RN 6):** ENEM 3 de 10 anos; OBMEP 6 de 10; OBI 9 de 10; ONHB 0.

Dependem de humanos: dados do IP (RF 3/3.1, T4.2), download do Censo Escolar, anos das edições 16ª–18ª da OBMEP e ENEM 2016–2022.

## 2. Inventário de fontes
| Fonte | Situação | Anos / cobertura | Chaves | Arquivo |
|---|---|---|---|---|
| **ENEM** (INEP) | Parcial | 2023–2025 (faltam 2016–2022); 3,9 / 4,3 / 4,8 mi de inscritos | `co_municipio_prova/esc` (7 dígitos); `co_escola` só em RESULTADOS 2024–25 (~36% das linhas; máscara `6…` p/ escolas <10) | `interim/enem_{ano}.parquet`, `enem_all.parquet` |
| **Saeb** microdados | Parcial | 2017, 2019, 2021, 2023 (EF2/EM); 2025 não publicado | **IDs fictícios** (máscara; mudam por edição); só UF real | `interim/saeb_escola.parquet` (224 mil linhas) |
| **Ideb** (INEP 2025) | Completo | EF2 2005–2025, EM 2017–2025; escola (498.809 linhas) e município (206.273) | `co_entidade` (8), `co_municipio` (7) reais | `interim/ideb_escola.parquet`, `ideb_municipio.parquet` |
| **INSE** | Parcial | Só o do Saeb (escola; aluno médio 2021/2023); escala 2017 incomparável | pseudônimos (Saeb) | em `saeb_escola` |
| **Taxa de Rendimento** | Parcial | Aprovação e indicador de rendimento via Ideb; faltam reprovação/abandono | reais (via Ideb) | em `ideb_*` |
| **Censo Escolar / Catálogo** | **Ausente** | — (download INEP falha em TLS; decisão: deixar pendente) | — | `dim_escola_base` **não gerada** |
| **IBGE** (municípios, população, malha) | Completo | 5.571 municípios; Censo 2022 + estimativa 2026; malha 2025 | `co_municipio` (7) | `interim/dim_municipio_base.parquet`; `raw/ibge/` |
| **OBMEP** | Parcial | 2016–2019, 2024, 2025 (329.796 linhas); 2020–2023 ausentes | nomes (sem código INEP) | `interim/obmep_premiados.parquet` |
| **OBI** | Parcial | 2016–2017, 2019–2025 (5.485 linhas); 2018: página 404 | nomes (sem código INEP, sem rede) | em `medalhistas.parquet` |
| **ONHB** | **Não coletada** | Sem lista pública por equipe | — | `lacunas_olimpiadas.md` |
| **MEC / Secretarias** | Mapeada, sem dados | Pesquisa web; nada baixado | — | `mec_secretarias.md` |
| **Base interna do IP** | **Sem acesso** (por desenho) | Esquema esperado + perguntas | — | `dados_internos_ip.md` |

## 3. Matriz fonte × requisito
Legenda: **●** atende · **◐** atende em parte (ver nota) · **○** não atende · **–** não se aplica.

| RF (rótulo) | ENEM | Saeb micro | Ideb | Censo | IBGE | OBMEP | OBI | ONHB | MEC/Sec | IP | **Situação** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.1 código da escola | ◐ (¹) | ○ | ● | ○ (ausente) | – | ○ | ○ | ○ | ○ | – | **Parcial** |
| 2.2 nome da escola | ○ | ○ | ● | ○ (ausente) | – | ◐ (nome livre) | ◐ (nome livre) | ○ | ○ | – | **Parcial** |
| 2.3 população | – | – | – | – | ● | – | – | – | – | – | **Atendido** |
| 2.4 ranking Saeb | – | ◐ (²) | ● | – | – | – | – | – | ◐ (SARESP, futuro) | – | **Atendido via Ideb** (²) |
| 2.5 medalhistas | – | – | – | ○ (p/ linkage) | – | ◐ | ◐ | ○ | ○ | – | **Parcial** (³) |
| 3 / 3.1 dados do IP | – | – | – | – | – | – | – | – | – | ○ | **Não atendido** (pendente) |
| 4 / 4.1 mapa de calor | – | – | – | – | ● (malha) | – | – | – | – | – | **Insumos prontos** (⁴) |
| 5.1 EF2 / EM | ◐ (só EM) | ● | ● | ○ | – | ◐ (⁵) | ◐ (⁵) | ○ | – | – | **Atendido p/ indicadores** |
| 5.3 sexo | ◐ (município) | ○ (não extraído) | ○ | – | – | ○ | ◐ (⁶) | ○ | – | – | **Parcial** |
| 5.4 renda ≤ 1,5 SM | ◐ (faixa + Q005, município) | ◐ (INSE, sem chave real) | ○ | – | – | – | – | – | ◐ (futuro) | – | **Parcial** (proxy) |
| RN 6 (≤ 10 anos) | ◐ 3/10 | ◐ 4 edições | ● | – | ● | ◐ 6/10 | ◐ 9/10 | ○ 0/10 | – | – | **Não atendido integralmente** |
| RN 3 (segurança) | fora do escopo desta sprint | | | | | | | | | | – |

Notas:
- ¹ ENEM 2024–2025: `co_escola` (8 dígitos) real em ~36% das linhas de RESULTADOS, sem nome; 2023 sem código.
- ² Saeb microdados só dão perfil por UF/etapa/rede (IDs fictícios). O ranking por escola e município com código real sai das notas Saeb dentro do **Ideb** (2017–2025, EF2 e EM). Em 2025 o Ideb traz só escolas públicas (Municipal/Estadual/Federal).
- ³ Faltam: anos 2020–2023 (OBMEP), ONHB, e o linkage escola (T2.3, depende de T1.13). Possível já agora: contagem por município/UF por nome.
- ⁴ Há população e malha; as métricas por recorte dependem das Fases 3–4. "Uma métrica por município por recorte" (T5.5) não foi testada.
- ⁵ Níveis das olimpíadas (OBMEP 1/2/3; OBI Júnior/1/2/Sênior) ainda não foram mapeados para EF2/EM; a OBI inclui modalidade Universitária.
- ⁶ Só a CF-OBI (Competição Feminina) permite inferir sexo, e apenas nela.

## 4. Qualidade dos dados — achados verificados
| # | Achado | Impacto | Onde |
|---|---|---|---|
| Q1 | Saeb: `ID_ESCOLA`/`ID_MUNICIPIO` são códigos fictícios; 0% de sobreposição com INEP e entre edições | Saeb micro não liga a escolas/municípios; sem painel por escola | `lacunas_saeb.md` §1 |
| Q2 | ENEM 2024–25: `PARTICIPANTES` e `RESULTADOS` não se relacionam (declarado pelo INEP) | Nota × renda × sexo por aluno impossível; renda só por município | `lacunas_enem.md` |
| Q3 | ENEM: `Q006` muda de significado em 2024 ("possui renda?"); renda familiar vai para `Q007`; faixas em R$ mudam com o salário mínimo | Erro silencioso se `q006` cru for usado; tratado em `renda_familiar_faixa` | `dicionario_enem.md` |
| Q4 | ENEM RS 2024: 279 mil inscritos (vs 160 mil em 2023 e 187 mil em 2025) | Outlier não explicado | `eda_enem.md` |
| Q5 | ENEM: cobertura de escola 24% (2023) vs 36% (2024–25); % de escola pública sobe de 76% para 83–84% | Séries 2023 × 2024+ não comparáveis sem cautela | `eda_enem.md` |
| Q6 | Ideb: 594 valores com asterisco (cálculo alternativo por extravio de provas); `ND*`, `ND***` → nulo | Pequeno; mantido numérico | `ideb.py` |
| Q7 | INSE do Saeb: 2017 "Grupo 1–5", 2019+ "Nível I–VII" | Não comparável entre 2017 e demais | `eda_saeb.md` |
| Q8 | OBMEP: páginas de 16ª–18ª sem ano; 2 linhas-placeholder (`---`) e 3 linhas sem nome na fonte | 3 edições perdidas; linhas descartadas e documentadas | `lacunas.md`, `cobertura_olimpiadas.md` |
| Q9 | Municípios: a API IBGE entrega `5101837` sem microrregião; esse município não tem população do Censo 2022 | Tratado; população = estimativa 2026 | `lacunas_saeb.md` §6 |
| Q10 | Chaves: todos os `co_municipio` de Ideb e ENEM estão em `dim_municipio_base` | Chave de município consistente | verificado |
| Q11 | OBMEP: a validação independente (contagem de linhas no HTML bruto) bate com o parquet em todos os anos | Parser confiável | `src/medalhistas.py` |
| Q12 | Saeb: média oficial por escola difere em média 0,29 ponto da média simples dos alunos (máx. 41,9) | Usada a oficial | `eda_saeb.md` |

## 5. Lacunas consolidadas
| ID | Lacuna | Origem | Bloqueia | Ação / responsável |
|---|---|---|---|---|
| L1 | ENEM 2016–2022 ausentes | `lacunas_enem.md` | RN 6; séries históricas | Usuário baixa os ZIPs; acrescentar mapeamento em `FONTES` (`src/enem.py`) |
| L2 | Censo Escolar 2025 / `dim_escola_base` | DP-2 | RF 2.1/2.2, linkage T2.3, T2.1 | Usuário baixa o ZIP, ou autoriza download sem verificação TLS (decisão atual: deixar pendente) |
| L3 | Saeb 2025 não publicado | DP-1 | Atualização | Aguardar INEP; notas 2025 via Ideb |
| L4 | INSE por escola (INEP) e Taxa de Rendimento completa | `lacunas_saeb.md` | RF 5.4 por escola | Baixar indicadores do INEP (DP-3) |
| L5 | OBMEP 2020–2023 (16ª–18ª sem ano) | `lacunas.md` | RF 2.5, RN 6 | Confirmar anos na fonte → `config/obmep_anos.yaml` |
| L6 | OBI 2018 (página 404) | `lacunas_olimpiadas.md` | RN 6 (1 ano) | Verificar se a fonte corrige; sem outra fonte |
| L7 | ONHB sem lista pública | `lacunas_olimpiadas.md` | RF 2.5 (parcial) | Pedir à organização / baixar a pasta "Edições anteriores" manualmente |
| L8 | Dados do IP (RF 3/3.1, T4.2) | `dados_internos_ip.md` | T4.2, T4.5 | Coordenação do IP (12 perguntas) |
| L9 | Mapeamento nível da olimpíada → etapa (EF2/EM) | `lacunas_olimpiadas.md` | RF 5.1 para medalhistas | T2.2/T2.7 |
| L10 | Sexo só no ENEM (município); renda sem chave de escola | Q2, Q1 | RF 5.3/5.4 por escola | Aceitar granularidade município ou obter INSE INEP (L4) |
| L11 | OFMAT não identificada | `backlog_olimpiadas.md` | — | Perguntar à coordenação |
| L12 | MEC/Secretarias: nada baixado | `mec_secretarias.md` | — | Fase futura (FNDE/PDDE, SARESP) |

## 6. Riscos
| # | Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | **Record linkage medalhista → escola (T2.3)** sem tabela-ponte | Alta | Alto | Obter Censo (L2); enquanto isso, linkage por município/UF; fila de revisão manual; amostra rotulada (T4.1) |
| R2 | **Índice baseado em poucos anos** (ENEM 3 anos; Saeb sem painel por escola) → instabilidade e viés de ano | Alta | Alto | Usar Ideb como base de proficiência (série longa); documentar anos usados; baixar ENEM 2016–2022 |
| R3 | **Renda/sexo por escola inviáveis** → análise de vulnerabilidade só por município (falácia ecológica) | Alta | Médio | Declarar a granularidade no contrato (T5.5); INSE INEP por escola (L4) |
| R4 | **LGPD:** nomes de menores em `interim/` (OBMEP/OBI, ~335 mil linhas) | Média | Alto | Nome em claro só em `interim` (fora do Git); `processed` com hash (T2.10); exibição pública sempre agregada |
| R5 | **Scrapers frágeis:** o layout muda entre anos (ex.: OBMEP 2016 sem coluna de posição e HTML sem aspas; títulos da OBI diferentes entre edições) | Média | Médio | Raw salvo em disco (reprocessável); validação independente por contagem; rotina por edição |
| R6 | **Supressão estatística:** muitos municípios com poucos medalhistas/participantes | Alta | Médio | n < 10 suprimido (T2.9); agregações por UF/microrregião |
| R7 | **Viés de seleção:** olimpíadas favorecem escolas que participam; a **OBI concentra 63% das linhas em SP (35%) e CE (28%)** (OBMEP: SP 25%, MG 18%); ONHB ausente | Alta | Médio | Medalhas per capita com cautela; relatório de viés (T4.4); registrar cobertura por UF |
| R8 | **Comparabilidade:** ENEM 2023 vs 2024+, INSE 2017 vs demais, SARESP vs Saeb | Média | Médio | Documentado; evitar misturar escalas |
| R9 | Dependência de decisões humanas (Censo, anos OBMEP, IP) bloqueia Fase 3 | Alta | Alto | Decidir L2 e L5 antes de iniciar T2.x |
| R10 | Normalização de nomes de município/escola (grafias distintas entre fontes) reduz taxa de linkage | Alta | Médio | `unidecode`, expansão de siglas, blocking por município/UF (T2.2) |

## 7. Recomendações antes da Fase 3
1. **Resolver L2 (Censo Escolar 2025)** — sem ele T2.1/T2.3 ficam parciais. Usar o Ideb escola como tabela-ponte mínima se necessário (código, nome, município, UF, rede; só rede pública em 2025).
2. **Confirmar os anos da 16ª–18ª OBMEP** (L5): 3 edições dentro da janela RN 6.
3. **Usar município como granularidade comum** e declarar isso no contrato de dados.
4. Proficiência por escola/município: **Ideb** (não o Saeb micro).
5. Obter ENEM 2016–2022 se a análise temporal for requisito.
6. Fechar com a coordenação do IP o nível de dado (A/B/C) para a T4.2.

## 8. Estado das frentes (verificado em `progresso.md`)
Concluídas: T0.1–T0.3, T1.1–T1.12 (com lacunas), T1.14–T1.18 (esqueleto para T1.17/18). **Bloqueada: T1.13 (Censo Escolar).** Nenhuma frente ficou aberta além dessa.
