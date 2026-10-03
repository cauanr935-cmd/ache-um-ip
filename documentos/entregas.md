# Entregáveis para o projeto de mapeamento de talentos por região

## Fase 1 (Semanas 1–4): Descoberta, mapeamento de fontes e modelagem de dados

**Objetivo da fase:** saber exatamente de onde vêm os dados, o que é possível coletar legalmente/tecnicamente, e ter o modelo de dados desenhado.

| # | Entregável | Subentregas |
|---|---|---|
| 1.1 | **Catálogo de provas/olimpíadas elegíveis** | Lista final de olimpíadas dentro do escopo (7º EF ao 2º EM); para cada uma: site oficial, periodicidade, se tem API/CSV/planilha aberta ou só HTML, campos disponíveis (nome, escola, cidade/UF, nível, medalha, ano da edição), e se expõe dado de aluno individual ou só agregado por escola/município |
| 1.2 | **Mapeamento de viabilidade técnica de coleta por fonte** | Para cada fonte: scraping viável? Precisa de login/captcha? Estrutura muda entre edições? Estimativa de volume de registros |
| 1.3 | **Definição do escopo geográfico** | Decisão de granularidade "subregião" (mesorregião/microrregião IBGE? região metropolitana? território de identidade? agrupamento próprio do Instituto Pontes?) — isso trava a escolha da base geográfica (IBGE, OpenStreetMap/Nominatim, etc.) |
| 1.4 | **Modelo de dados (schema)** | Entidades: Aluno/Registro de premiação (ou registro agregado, ver nota de LGPD abaixo), Escola, Município, Subregião, Prova, Edição, Nível/Ano escolar normalizado, Medalha |
| 1.5 | **Análise de privacidade/LGPD** | Como os dados envolvem menores de idade, definir: o mapa vai mostrar nomes de alunos ou só contagens agregadas por região/escola? |
| 1.6 | **Protótipo de scraper/coletor para 1 prova (prova de conceito)** | Rodar o pipeline ponta a ponta com a OBMEP (fonte mais robusta e documentada publicamente) para validar a arquitetura antes de escalar para as outras provas |
| 1.7 | **Decisão de stack técnica** | Backend/DB (ex: Postgres + PostGIS se for usar geolocalização), frontend de mapa (ex: Mapbox GL, Leaflet, deck.gl), hospedagem |

**Marco de fim da Fase 1:** protótipo funcional coletando e estruturando dados de 1 olimpíada, schema de dados aprovado, decisão de privacidade tomada.

---

## Fase 2 (Semanas 5–8): Coleta em escala, ETL e backend

**Objetivo da fase:** ter o pipeline de dados rodando para todas (ou a maioria) das provas do catálogo, com dados limpos, geolocalizados e servidos por uma API própria.

| # | Entregável | Subentregas |
|---|---|---|
| 2.1 | **Coletores (scrapers/importadores) para cada fonte do catálogo** | Um coletor por prova, com tratamento de erro e log; priorizar as 3-4 maiores primeiro (OBMEP, OBA, OBC/ONHB) |
| 2.2 | **Normalização de "nível de prova" → "ano escolar"** | Tabela de mapeamento por prova/edição; filtro automático descartando registros fora do 7º ano–2º EM |
| 2.3 | **Geocodificação** | De município/escola para coordenadas e subregião definida na Fase 1 (usar base do IBGE como fonte primária; Nominatim/OpenStreetMap como fallback para geocoding pontual, testando se atende volume sem custo) |
| 2.4 | **Agregação por região** | Tabelas materializadas: nº de premiações por subregião/UF/prova/ano/nível de medalha |
| 2.5 | **Banco de dados populado e versionado** | Estrutura final com pelo menos 2-3 edições históricas por prova (para permitir visão de série temporal, se fizer sentido) |
| 2.6 | **API própria (backend)** | Endpoints para: listar regiões com contagem, filtrar por prova/ano/nível/medalha, detalhar uma subregião |
| 2.7 | **Rotina de atualização** | Job agendado (ex: mensal ou por edição de olimpíada) para reprocessar novas listas de premiados |

**Marco de fim da Fase 2:** API respondendo com dados agregados reais de todas as provas prioritárias, cobrindo geograficamente o Brasil.

---

## Fase 3 (Semanas 9–12): Frontend do mapa, filtros e lançamento

**Objetivo da fase:** entregar o website público, testado e no ar.

| # | Entregável | Subentregas |
|---|---|---|
| 3.1 | **Mapa interativo base** | Visualização coroplética/heatmap por subregião mostrando concentração de talentos |
| 3.2 | **Painel de filtros** | Por região/UF/subregião, por prova, por ano/edição, por nível de medalha; contador dinâmico "quantos talentos nesta região" |
| 3.3 | **Página de detalhe da região** | Ao clicar numa subregião: nº de premiados, distribuição por prova, escolas com mais destaque (agregado, sem nome de aluno) |
| 3.4 | **Responsividade e testes de usabilidade** | Mobile/desktop, teste com 3-5 pessoas do Instituto Pontes |
| 3.5 | **Documentação e handoff** | Como atualizar os dados (rodar a rotina da Fase 2), como o Instituto Pontes usa o filtro para priorizar visitas/contato com talentos |
| 3.6 | **Deploy e domínio final** | Ambiente de produção, HTTPS, monitoramento básico |
| 3.7 | **Lançamento interno** | Apresentação da plataforma pronta para o Instituto Pontes |

**Marco de fim da Fase 3 = entrega final do projeto.**

---

## Riscos a monitorar desde já

- **Falta de API oficial** nas olimpíadas: scraping pode quebrar se o site mudar de estrutura — vale já prever manutenção contínua pós-lançamento, não só os 3 meses.
- **Volume e inconsistência de dados** entre edições diferentes de uma mesma prova (formatos de página mudam ano a ano).
- **LGPD**: mesmo que os dados de premiados sejam públicos nas fontes originais, publicar um mapa que reidentifique menores de idade é sensível — a recomendação é manter a exibição pública sempre agregada.
- **Escopo de subregião**: se a definição de "subregião" não for decidida cedo (Fase 1), trava toda a geocodificação da Fase 2.

