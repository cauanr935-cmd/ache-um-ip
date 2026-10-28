# Ache um IP: documentação do projeto

Site interno do **Instituto Ponte (IP)** que mostra, em um mapa do Brasil, onde estão os talentos que o IP pode procurar: escolas e municípios com bom desempenho, medalhistas de olimpíadas e os alunos que o IP já tem.

Propósito do IP: ascensão social em uma geração, por meio da educação de qualidade para jovens em vulnerabilidade social. Perfil buscado: aluno talentoso de escola pública, com renda per capita até 1,5 salário mínimo, que esteja entre o 7º ano do fundamental e o 2º ano do ensino médio.

Equipe: Cauan, Emanuel e Davi Amaral. Repositório: `github.com/cauanr935-cmd/ache-um-ip`.

> Este documento descreve o que existe hoje. A especificação original do mapa está em [specs.md](../specs.md); as convenções de trabalho em [claude.md](../claude.md). Em caso de conflito, vale o `specs.md`.

---

## 1. O que o site faz

### Mapa
- Mapa do Brasil em mapa de calor, com **zoom em três níveis**: Brasil → UF → município. Clicar em uma UF aproxima e mostra os municípios; clicar em um município abre o painel lateral.
- Cores por **5 faixas de quantis** calculadas sobre os valores válidos. Município sem dado ou com dado insuficiente fica cinza, com legenda "Sem dados".
- Busca por município, escola ou UF; **favoritos** por usuário; funciona no celular (painel vira gaveta).

### Provas (filtro "Prova")
| Prova | O que o mapa mostra | Anos | Observação |
|---|---|---|---|
| **Saeb** | Nota média (LP e MT) das escolas públicas | 2017, 2019, 2021, 2023 | Nível UF só até 2023 |
| **ENEM** | Nota média por município | 2023 a 2025 | Nunca por escola |
| **OBMEP** | Medalhas por 100 mil habitantes | 2016 a 2025 (sem 2020) | Rede pública ou todas |
| **OBI** | Medalhas por 100 mil habitantes | 2016 a 2025 (sem 2018) | Não informa a rede da escola |
| **OCMAT** | Medalhas por 100 mil habitantes | 2025 | Olimpíada Capixaba de Matemática; só ES; 1ª edição em 2025 |
| **INSE** | Nível socioeconômico médio das escolas públicas (menor = mais vulnerável) | 2019, 2021, 2023 | Fonte INEP; não separa etapas |

Outros filtros: **Etapa** (Ensino Fundamental 2 ou Ensino Médio) e **Ano**. A rede é sempre pública (só a OBI usa "todas", porque a base dela não informa a rede). Sexo e renda aparecem desabilitados com a explicação, porque as bases não têm esses recortes. Incompatibilidades viram opção desabilitada com o motivo, nunca mapa vazio.

### Filtros extras
- **INSE das escolas:** limita a lista de escolas do painel do município a um grupo (baixo: níveis I a III; médio: IV e V; alto: VI e VII). Serve para achar escola de baixo INSE com nota alta.
- **Mostrar cidades com alunos do Instituto Ponte:** coloca pinos amarelos nas cidades de origem dos alunos do IP. Clicar no pino leva ao município e o painel lista os alunos (nome com link para a página do IP, ano de entrada, escola de origem).

### Painel lateral
- **Município:** população, posição na UF, métrica do recorte, escolas ranqueadas pelo Saeb (com selo "Destaque" e **INSE** de cada escola), medalhas por olimpíada, contexto (Ideb, aprovação, ENEM, renda estimada) e, se o filtro estiver ligado, os alunos do IP.
- **Escola:** ficha com código INEP, rede, INSE, evolução do Saeb/Ideb e número de medalhistas vinculados.
- **Medalhistas do município:** lista de alunos com medalha (ver seção 4), sempre com **link para a página oficial** de onde a lista foi tirada.

### Páginas
- `index.html`: login com Google.
- `mapa.html`: o mapa.
- `sobre.html`: "Sobre o Projeto" (pública, linkada da tela de login).

---

## 2. Arquitetura

```
 Fontes públicas                Pipeline Python (src/)                 Servidor Node (server/)          Navegador (screens/)
 INEP, IBGE, OBMEP,   ──►  coleta → data/raw → tratamento →   ──►  Express + login Google      ──►  HTML/CSS/JS + D3
 OBI, OCMAT, IP            data/interim → api_precompute.py        serve JSON pré-computado        mapa, filtros, painel
                                  │                                       ▲
                                  ├─► data/api/        (público, sem nomes)│
                                  └─► data/privado/    (nomes) ──► Redis privado (produção)
```

- **Pré-cálculo:** tudo que o mapa mostra é gerado antes, por `src/api_precompute.py`, em JSON. O servidor só entrega arquivos; não faz conta pesada. Por isso a troca de filtro leva décimos de segundo.
- **Dados com nomes de alunos** nunca entram no git: ficam em `data/privado/` (local) e no **Redis** (produção, na Vercel).
- **Stack:** front em JavaScript, CSS e D3.js (sem framework); back em Node.js 20+ com Express; dados em Parquet/JSON; pipeline em Python (pandas, DuckDB, rapidfuzz).

### Estrutura de pastas
| Pasta | Conteúdo |
|---|---|
| `screens/` | Front: `html/`, `css/`, `js/` (`mapa.js`, `mapa-filtros.js`, `mapa-dados.js`, `mapa-busca.js`, `login.js`), `assets/` |
| `server/` | `app.js` (rotas e segurança), `dados.js` (API de dados), `auth.js` (login), `redis.js`, `medalhistas.js` (elegibilidade), `favoritos.js`, `busca.js`, testes em `app.test.js` |
| `src/` | Coleta, tratamento, linkage, modelagem e pré-cálculo (Python) |
| `config/` | Regras em YAML: supressão, elegibilidade, recortes, linkage, pesos, renda |
| `scripts/` | Utilitários Node: malha do mapa, envio ao Redis, alunos do IP |
| `data/` | `raw/` e `interim/` (fora do git), `malha/` (TopoJSON), `api/` (JSON servido), `privado/` (fora do git) |
| `docs/` | Documentação técnica de cada etapa e de cada base |

---

## 3. Fontes de dados

| Dado | Fonte | Granularidade |
|---|---|---|
| Saeb e Ideb | INEP | Escola e município |
| ENEM | INEP (microdados) | Município |
| INSE | INEP (`INSE_2019/2021/2023_escolas.xlsx`) | Escola (código INEP) |
| Taxas de rendimento | INEP | Escola e município |
| Catálogo de escolas, municípios, população, malha | INEP e IBGE | Escola, município |
| Medalhistas OBMEP | `obmep.org.br/premiados.htm` e páginas por edição | Aluno |
| Medalhistas OBI | `olimpiada.ic.unicamp.br/passadas/` | Aluno |
| Medalhistas OCMAT 2025 | `matematicanarede.sedu.es.gov.br/ocmat/2025` (12 PDFs no Google Drive da Sedu-ES) | Aluno |
| Alunos do Instituto Ponte | `institutoponte.org.br/como-atuamos/` e a página de cada aluno | Aluno (cidade de origem) |

Chaves canônicas: município = código IBGE de 7 dígitos; escola = `CO_ENTIDADE` do INEP, 8 dígitos. O vínculo medalhista → escola usa casamento aproximado de nomes (`src/linkage.py`); só vínculo automático vira código INEP.

---

## 4. Regras de negócio

### Supressão estatística
Município ou escola com **menos de 10** participantes não mostra valor ("dados insuficientes") e fica fora de quantis e rankings. Configuração: [config/supressao.yaml](../config/supressao.yaml).
Para **olimpíadas** (OBMEP, OBI, OCMAT) a regra é diferente: o `n` é a própria contagem de medalhas, então aparece a partir de **1 medalha** (`n_min_olimpiadas: 1`). Só município com 0 medalhas fica cinza.

### Elegibilidade dos medalhistas (processo seletivo do IP)
O IP só aceita aluno que esteja, no mínimo, no 2º ano do ensino médio e que ainda não esteja no 3º. Como o ano da medalha não diz a série, vale o critério otimista:

> Medalhista **do ensino médio** que ganhou no ano X só é elegível em **X ou X + 1**. Hoje (2026), só entra medalha de 2025 ou 2026.

- Vale para OBMEP nível 3, OCMAT níveis 3 e 4, e categorias de ensino médio da OBI. **Não vale para o ensino fundamental.**
- O servidor aplica a regra na hora, com o ano corrente ([server/medalhistas.js](../server/medalhistas.js)), então não é preciso regerar dados todo ano.
- A tela mostra quantos medalhistas ficaram de fora.
- Como saber se é ensino médio: primeiro pela categoria da prova; nas provas de nível misto (OBI Programação 1 e 2), pelo nome da escola (IF, ETEC, técnico, estadual etc.). Configuração em [config/elegibilidade.yaml](../config/elegibilidade.yaml).

### Níveis da OCMAT
| Nível | Série | Aviso na tela |
|---|---|---|
| 1 | 6º e 7º ano | Pode ser do 6º ano (abaixo do perfil) |
| 2 | 8º e 9º ano | Nenhum |
| 3 | 1ª série do médio | Nenhum |
| 4 | 2ª e 3ª séries do médio | Pode ser do 3º ano (acima do perfil) |

Não dá para separar as séries dentro de um mesmo nível, então os níveis 1 e 4 entram com aviso em destaque na lista.

### Outras regras
- **Rede:** todos os alunos de interesse são de escola pública; não há filtro de rede.
- **Renda ≤ 1,5 SM** é sempre rotulada "estimada".
- **Dados de no máximo 10 anos** (2016 a 2025).
- **INSE:** média ponderada pelo número de alunos; para a escola vale o dado mais recente (2023, depois 2021 e 2019).

---

## 5. Privacidade e segurança

- **Login com Google**, restrito ao domínio institucional (`ALLOWED_EMAIL_DOMAINS`) e a uma lista opcional de e-mails extras. Toda página e toda rota de API (menos login, `sobre.html` e os arquivos públicos de `PUBLICOS` em `server/app.js`) exige sessão válida.
- **Nomes de alunos são dado pessoal**, mesmo públicos, e muitos são menores. Por isso:
  - `ALUNO_IDENTIFICADO=false` (padrão): a lista mostra só iniciais e código. Com `true`, mostra o nome completo.
  - **Cada abertura** da lista de medalhistas ou dos alunos do IP grava um **registro de auditoria** (quem, quando, qual município, quantos). Se a gravação falhar, a lista não é entregue.
  - Não há exportação nem nome de aluno em URL.
  - Os arquivos com nomes ficam fora do git (`data/privado/`, Redis).
- Parâmetros de API são validados por **lista fechada** (catálogo); não há SQL. POST e DELETE exigem mesma origem e JSON. Cabeçalhos de segurança e CSP configurados em `server/app.js`.
- A decisão formal de LGPD sobre exibir nomes (tarefa T2.10) continua **em aberto** no projeto; o padrão seguro é `false`.

---

## 6. Como rodar

### Pré-requisitos
Node.js 20+ e Python 3 (só para regerar dados) e as dependências: `npm install` e `pip install -r requirements.txt` (use a `.venv` do projeto).

### Configuração (`.env`, fora do git; modelo em `.env.example`)
| Variável | Para quê |
|---|---|
| `GOOGLE_CLIENT_ID` | Login com Google (origem autorizada: `http://localhost:3000`) |
| `SESSION_SECRET` | Assina o cookie de sessão (obrigatório em produção) |
| `SESSION_HOURS` | Duração da sessão (padrão 8) |
| `ALLOWED_EMAIL_DOMAINS`, `ALLOWED_EMAILS` | Quem pode entrar |
| `ALUNO_IDENTIFICADO` | `true` mostra nomes completos; `false` (padrão) só iniciais |
| `KV_REST_API_URL`, `KV_REST_API_TOKEN` | Redis REST (Upstash/Vercel KV) para produção |
| `NODE_ENV` | `development` ou `production` |

### Comandos
```bash
npm install
npm run dev      # servidor em http://localhost:3000 (recarrega sozinho)
npm start        # sem recarregar
npm test         # testes do servidor (10)
npm run malha    # regera a malha do mapa (TopoJSON) a partir do shapefile do IBGE
```

---

## 7. Como atualizar os dados

Ordem completa (ver também [docs/progresso.md](progresso.md) e os arquivos de cada etapa em `docs/`):

1. **Coleta e tratamento** (`src/pipeline.py`: `run_coleta`, `run_preprocessamento`, `run_modelagem`). Gera `data/interim/` e `data/processed/`.
2. **Olimpíadas:** `src/coleta_obmep.py`, `src/coleta_obi.py`, `src/medalhistas.py`, `src/linkage.py`, `src/dedup.py`. Para a **OCMAT**, baixar os PDFs para `data/raw/ocmat/<ano>/nivel<N>_<Medalha>.bin` e rodar `python src/coleta_ocmat.py`.
3. **Alunos do Instituto Ponte:** `python src/coleta_alunos_ip.py` (lê as páginas do site do IP, com pausa e cache em `data/raw/instituto_ponte/`), depois `node scripts/gerar_alunos_ip_mapa.js` (calcula a posição de cada cidade).
4. **Pré-cálculo da API:** `.venv/bin/python src/api_precompute.py` (cerca de 2 a 3 minutos). Gera `data/api/` (vai para o git) e `data/privado/medalhistas/` (não vai).
5. **Produção:** `node scripts/enviar_medalhistas_redis.js` envia medalhistas e alunos do IP para o Redis. Rodar de novo sempre que os passos 3 ou 4 mudarem.
6. Commit e push. A Vercel publica sozinha.

Quando sair uma nova edição (por exemplo OCMAT 2026), acrescente o ano nos arquivos de entrada e rode os passos 2, 4 e 5. Os links de fonte das edições estão em `src/api_precompute.py` (`FONTE_OBMEP`, `fonte_oficial`) e `src/ocmat.py`.

---

## 8. API

Todas atrás do login (`GET`, salvo indicação).

| Rota | Devolve |
|---|---|
| `/api/me` | Usuário logado |
| `/api/recortes` | Catálogo de provas, etapas, anos, redes e motivos de indisponibilidade |
| `/api/mapa?nivel=uf\|municipio&uf=&prova=&etapa=&ano=&rede=&sexo=&renda=` | `[{codigo, valor, n, suprimido}]` |
| `/api/geo/br_uf`, `/api/geo/municipios/:uf` | Malha em TopoJSON |
| `/api/municipio/:ibge?etapa=` | Painel do município (escolas com INSE, contexto, medalhas) |
| `/api/escola/:inep` | Ficha da escola |
| `/api/busca?q=` | Sugestões de UF, município e escola |
| `/api/municipio/:ibge/medalhistas` | Lista de medalhistas elegíveis (auditada) |
| `/api/alunos-ip` | Alunos do Instituto Ponte por cidade (auditada) |
| `GET/POST /api/favoritos`, `DELETE /api/favoritos/:tipo/:id` | Favoritos do usuário |
| `POST /auth/google`, `POST /auth/logout` | Login e logout |

---

## 9. Deploy (Vercel)

- `vercel.json` usa `@vercel/node` com `index.js` como entrada e inclui `screens/`, `config/`, `data/malha/` e `data/api/` no pacote.
- O disco da Vercel é **somente leitura**. Por isso favoritos, auditoria, medalhistas e alunos do IP usam o **Redis** (`server/redis.js`). Sem Redis configurado, a lista de medalhistas responde "indisponível neste ambiente".
- Variáveis na Vercel: as da seção 6, com `ALUNO_IDENTIFICADO=true` se a equipe quiser ver nomes.
- O push na branch publica o deploy automaticamente.

---

## 10. Testes

`npm test` roda 10 testes do servidor: autenticação e domínios, rotas protegidas, busca, favoritos, ficha da escola, medalhistas com auditoria e pseudonimização, medalhistas e auditoria via Redis, regra de elegibilidade e alunos do IP. Os dados de cada teste são gerados na hora, sem depender de `data/`.

---

## 11. Identidade visual

Segue o manual do Instituto Ponte: roxo `#6b6fa3`, amarelo `#f9b233`, fonte da marca **Gotham Family**. A Gotham é paga e não pode ser carregada pela web, então o site usa **Montserrat** como substituta. Para usar a Gotham, troque a variável `--fonte-marca` em `screens/css/style.css`. A logo fica em `screens/assets/`.

---

## 12. Limitações conhecidas e pendências

- **Sem recorte por sexo** nas notas e nas medalhas (as bases não têm).
- **Renda** não cruza com nota ou medalha por aluno; só aparece como proxy no contexto do município.
- **ONHB** não existe nos dados. **OBI** não informa a rede da escola.
- **OCMAT** só tem a edição 2025 (a de 2026 ainda não tem medalhistas). Na OBMEP não há dados de 2020, e a página oficial da edição 2018 respondia 404 na última verificação (ver `docs/cobertura_obmep.md`).
- **Alunos do IP:** 487 dos 566 alunos têm cidade identificada. 66 não têm cidade na página do IP e 13 têm nome de cidade ambíguo (sem UF).
- **Medalhistas do fundamental** não passam pelo filtro de elegibilidade (decisão do projeto); medalhas antigas desse grupo continuam na lista.
- **Filtro de INSE** age só na lista de escolas, não recolore o mapa.
- **Base interna de candidatos do IP** ainda não integrada (ver `docs/dados_internos_ip.md`).
- **Decisão LGPD (T2.10)** sobre nomes completos ainda em aberto.
- Dados candidatos a entrar: PAEBES (avaliação do ES), Censo Escolar, Pé-de-Meia, CadÚnico, outras olimpíadas (OBF, OBQ, OBA, OBB, ONC, OBR).
