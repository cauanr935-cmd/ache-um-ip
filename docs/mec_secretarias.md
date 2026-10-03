# MEC e Secretarias Estaduais de Educação — o que publicam e sobreposição com o INEP (T1.15–T1.16)

Método: pesquisa web curta em 02/10/2026 (buscas + 2 páginas de portais). **Nada foi raspado nem baixado.** Limitação: `dadosabertos.mec.gov.br` bloqueou a leitura automática (HTTP 403), então o catálogo do MEC foi conhecido só por resultados de busca. Nada abaixo foi validado por download de arquivo — tratar como mapeamento, não como inventário confirmado.

## 1. O que existe

### MEC (nível federal)
| Fonte | O que traz | Formato / acesso |
|---|---|---|
| Portal de Dados Abertos do MEC (`dadosabertos.mec.gov.br`; também `dados.gov.br`) | ~81 conjuntos em processo de "readequação e recatalogação" (segundo a busca); predominam temas de ensino superior e programas | Catálogo web; arquivos conforme o conjunto (não verificado) |
| Educacenso / Censo da Educação Básica | Escolas, matrículas, docentes, turmas | **É dado do INEP**; o MEC apenas o referencia |
| Programa Pé-de-Meia | Desde 31/07/2025 o Portal da Transparência publica a lista de **estudantes e pagamentos** (nome, UF, município, etapa, tipo de incentivo) | Portal da Transparência (consulta/download) |
| Editais (ex.: Pé-de-Meia Licenciaturas) | Chamadas e resultados de programas | Páginas e PDFs; **ensino superior, fora do escopo** |

### FNDE (autarquia do MEC)
Dados abertos de **PNAE** (alunos atendidos, escolas, repasses), **PDDE** (lista de escolas atendidas, execução financeira; consulta por `co_escola`) e **PNLD**. Distribuídos em CSV/XML/JSON via `dados.gov.br` e portal do FNDE (nas buscas; não verificado arquivo a arquivo).

### Secretarias Estaduais
| UF | O que foi encontrado |
|---|---|
| **SP** | Portal de Dados Abertos da Educação (`dados.educacao.sp.gov.br`; categorias: matrículas, infraestrutura, resultados educacionais, profissionais, orçamento) e conjunto **"SARESP (Microdados)"** em `dadosabertos.sp.gov.br` (3º, 5º, 7º e 9º ano do EF e 3ª série do EM; LP e MT) |
| **PE, MG, CE** | Têm avaliações estaduais próprias (SAEPE, SIMAVE, SPAECE); só foram vistas **menções**, sem confirmar publicação de microdados |
| **ES** | Plano de Dados Abertos da SEDU (PDF); sem conjuntos identificados |
| Demais UFs | Não pesquisadas (limite de tempo) |

## 2. Sobreposição com INEP/Saeb/ENEM e o que é exclusivo

| Tema | INEP já cobre? | Exclusivo da fonte MEC/Secretaria? | Recomendação |
|---|---|---|---|
| Cadastro de escolas (código, nome, rede, localização) | **Sim** (Censo Escolar / Catálogo de Escolas) | Não relevante | Usar só INEP (pendente: T1.13) |
| Matrículas, docentes | Sim (Censo) | Não | Só INEP |
| Proficiência | Saeb/Ideb (nacional) | **Sim, parcial:** SARESP (SP) e avaliações de outros estados têm escalas próprias, outras séries (ex.: 3º, 5º, 7º ano) | Futuro; **não comparável** com o Saeb; só para validar/complementar |
| ENEM, Ideb, INSE | Sim | Não | Só INEP |
| Recursos por escola (PDDE/PNAE/PNLD) | Não | **Sim** (FNDE) | Candidato a proxy de porte/vulnerabilidade; chave por escola (`co_escola`) a confirmar |
| Beneficiários Pé-de-Meia por município | Não | **Sim** | Possível proxy de vulnerabilidade de EM público por município, mas é **dado pessoal de menores**: exige decisão LGPD (T2.10) e usar **apenas agregado por município**, nunca nomes |
| Editais/resultados de programas | Não | Sim | Fora do escopo da sprint |

## 3. Conclusão
- Para a sprint atual, MEC e Secretarias são **complementares**, não necessários: o essencial (escolas, proficiência, renda, ENEM) vem do INEP.
- Candidatos para uma próxima fase, em ordem: (1) PDDE/PNAE por escola (FNDE), (2) SARESP microdados (SP, maior rede), (3) Pé-de-Meia agregado por município.
- **Falta verificar:** conteúdo real dos catálogos (MEC bloqueou acesso automático), formato e chaves dos CSVs do FNDE, e se os demais estados publicam microdados. Não houve acesso a arquivos.
