# SPEC: Mapa Interativo "Ache um IP"

Documento para o Claude Code implementar a camada de visualização (mapa) do projeto Ache um IP.

## 0. Instruções para quem for implementar

1. Antes de escrever código, leia o repositório existente. O **login com Google (somente e-mail institucional) já está implementado**. Reaproveite-o, não reescreva. Toda rota do mapa e toda rota de dados deve ficar atrás dessa autenticação.
2. Siga o stack já definido: **JavaScript, D3.js (d3-geo, d3-zoom, d3-scale) e CSS** no front; **JS** no back (usar o framework já presente no repo).
3. Não há banco de dados obrigatório nesta fase. Os dados chegam como arquivos tratados (Parquet/CSV, eventualmente DuckDB/SQLite). Veja a seção 6.
4. Itens marcados como **[ABERTO]** dependem de decisão humana. Implemente o comportamento padrão indicado e deixe configurável.

## 1. Objetivo

Permitir que a coordenação do Instituto Ponte (IP) identifique **regiões e escolas com mais potencial de alunos talentosos em vulnerabilidade social**, por meio de um mapa do Brasil clicável com mapa de calor.

Propósito do IP, que orienta decisões de produto: *"Ser a ponte para a ascensão social em uma geração, por meio da educação de qualidade, para jovens em vulnerabilidade social."*

Perfil buscado: alunos talentosos de escolas públicas, renda per capita até 1,5 salário mínimo, premiados em olimpíadas (OBMEP, OBI, ONHB).

## 2. Escopo desta entrega

**Dentro:**
- Mapa do Brasil com drill-down: Brasil → UF → município → escola → medalhistas.
- Mapa de calor por município.
- Painel lateral de detalhe do município.
- Filtros, busca e favoritos.
- Desktop e mobile.

**Fora:** autenticação (já pronta), pipeline de tratamento de dados (feito na sprint de dados), contato com escolas, modelagem estatística (o mapa só consome os resultados).

## 3. Fontes de dados e granularidade

A granularidade principal é o **município** (RF 1). Cada fonte permite um nível diferente, e a interface deve respeitar isso.

| Fonte | Menor nível | Uso no mapa |
|---|---|---|
| ENEM (microdados, até 10 anos) | Município | Desempenho por município. **Sem código de escola** (pós-2015), então nunca exibir ENEM por escola. |
| Saeb (proficiência LP/MT, 9º ano EF2 e 3ª série EM) | Escola | Métrica principal do mapa de calor e ranking de escolas. |
| OBMEP, OBI, ONHB (listas de premiados) | Aluno → escola → município | Contagem de medalhas e lista de medalhistas. |
| Ideb, INSE, Taxa de Rendimento (INEP/QEdu) | Escola/Município/UF | Contexto e índice composto. |
| Catálogo de escolas INEP (Censo Escolar) | Escola | Tabela-ponte código ↔ nome. |
| IBGE (municípios, população, malha) | Município | Geometria do mapa e normalização per capita. |

Chaves canônicas (obrigatórias em todos os arquivos):
- Município: **código IBGE de 7 dígitos**.
- Escola: **CO_ENTIDADE INEP de 8 dígitos**.

Dados com no máximo 10 anos de idade (RN 6).

## 4. Experiência do usuário

### 4.1 Navegação (drill-down)

1. **Nível Brasil:** UFs coloridas pelo mapa de calor (média agregada). Clique em uma UF faz zoom animado para ela.
2. **Nível UF:** municípios da UF coloridos. Hover mostra tooltip (nome, valor da métrica). Clique abre o painel do município.
3. **Nível município:** o mapa destaca o município e o painel lateral abre com o detalhe (4.3).
4. **Nível escola:** clique em uma escola na lista do painel abre a ficha da escola.
5. Breadcrumb sempre visível (Brasil > UF > Município) e botão "voltar". Zoom e pan livres com d3-zoom, e o nível acompanha o zoom.

Geometrias: malha do IBGE (API `servicodados.ibge.gov.br/api/v3/malhas`), convertidas para TopoJSON e **servidas como arquivos estáticos**, com um arquivo do Brasil por UF e um por município de cada UF para não carregar tudo de uma vez.

### 4.2 Mapa de calor (RF 4.1, RF 6)

- **Métrica padrão:** média da pontuação de aprendizado do Saeb das **escolas públicas** do município, para a etapa selecionada.
- **Seletor de métrica** (muda a coloração): Saeb médio, nº de medalhas (OBMEP/OBI/ONHB), desempenho no ENEM, índice composto de potencial.
- **Alternar proporção vs. volume absoluto** (botão): proporção = medalhas por 100 mil habitantes ou % de escolas/alunos acima do corte. Volume = total absoluto. Padrão: proporção.
- **Escala de cor:** sequencial (um matiz), legenda sempre visível, **faixas por quantis** (5 classes) calculadas sobre o conjunto filtrado. Município sem dado ou suprimido usa cinza claro com legenda "sem dados".
- **Todos os filtros afetam o mapa.** Exemplo: filtro "feminino" + medalhas = mapa de calor só com medalhas de meninas (RF 6).

### 4.3 Painel do município (RF 2)

Cabeçalho: nome, UF, código IBGE, população (RF 2.3), valor da métrica atual e posição no ranking da UF.

Seções:
- **Escolas** ranqueadas por nota de aprendizagem no Saeb (RF 2.4): código INEP (RF 2.1), nome (RF 2.2), rede, nota, selo de **escola destaque** (ver 4.6). Ordenação e paginação.
- **Medalhistas** (RF 2.5): lista com medalha, olimpíada, ano e escola. Ver regras de privacidade em 7.
- **Contexto:** Ideb, INSE, taxa de rendimento, ENEM do município (quando existir).
- **Concentração de candidatos ao IP** (RF 3.1): contagem de alunos candidatos no município e, quando houver base interna integrada, alunos já matriculados.
- Botão **favoritar** município ou escola.

### 4.4 Filtros (RF 5)

Filtros globais, em barra superior no desktop e em gaveta no mobile:
- Etapa: **Ensino Fundamental 2** ou **Ensino Médio** (RF 5.1).
- Prova usada como critério: Saeb, ENEM, OBMEP, OBI, ONHB (RF 5.2).
- Sexo: todos, feminino, masculino (RF 5.3).
- Renda: **"renda per capita provável ≤ 1,5 SM" ligado por padrão** (RF 5.4). É proxy (faixa declarada), então a interface deve rotular "estimado".
- Ano/edição: padrão = edição mais recente; opção de escolher outra dentro da janela de 10 anos.
- Rede: apenas pública por padrão.

Nem toda combinação existe (ex.: ENEM por escola). Quando um filtro for incompatível com a fonte, **desabilitar a opção com explicação** em vez de mostrar mapa vazio.

### 4.5 Busca e favoritos

- Busca única com autocomplete por município, escola (nome ou código INEP) e UF. Escolher um resultado faz zoom e abre o painel.
- Favoritos por usuário (associado ao e-mail logado), listados em um menu, com clique que leva ao local no mapa. Persistência: tabela/arquivo simples no back; **[ABERTO]** se é pessoal ou compartilhado entre a coordenação (padrão: pessoal).

### 4.6 Escola destaque e aluno destaque

**[ABERTO]** O critério oficial ainda não foi definido. Padrão provisório, parametrizado em arquivo de configuração:
- **Escola destaque:** top 10% das escolas públicas do município ou da UF por nota Saeb na etapa, ou com ≥ 1 medalhista.
- **Aluno destaque:** medalhista de ouro ou prata em OBMEP/OBI/ONHB na janela de 10 anos.

### 4.7 Responsividade e acessibilidade (RF 7, RN 7)

- Desktop: mapa à esquerda/centro, painel lateral à direita. Mobile: mapa em tela cheia e painel como bottom sheet.
- Controles de zoom em botões, navegação por teclado, foco visível, contraste mínimo AA, legenda com texto e não só cor, textos alternativos. Avaliar integração com **VLibras** (opcional).

## 5. Índice composto de potencial **[ABERTO]**

Ainda não definido. Contrato com o back: o mapa lê uma coluna numérica `indice_potencial` já calculada e **não implementa a fórmula**. Proposta da sprint de modelagem (apenas referência): talento (medalhas per capita) + qualidade da rede (Saeb/Ideb) + vulnerabilidade (INSE/renda), com pesos documentados. Se os pesos virarem editáveis no futuro, isolar o cálculo em um módulo à parte.

## 6. Contrato de dados e API

### 6.1 Tabelas analíticas (entregues pela sprint de dados)

`dim_municipio`, `dim_escola`, `dim_aluno`, `fato_desempenho`, `fato_medalhas`.

Requisito crítico (T5.5): **uma métrica por município por recorte**, com schema estável. Recorte = (etapa, prova, sexo, renda, ano, rede).

### 6.2 Estratégia de performance

Para atender RN 2, 4 e 5, **pré-computar** agregações por recorte (ex.: JSON/Parquet por UF e por recorte) em vez de agregar na hora. Servir:
- `GET /api/mapa?nivel=uf|municipio&uf=XX&metrica=...&etapa=...&sexo=...&renda=...&ano=...` retorna `[{codigo, valor, n, suprimido}]`.
- `GET /api/municipio/{ibge}?...` retorna o painel.
- `GET /api/escola/{inep}?...` retorna a ficha.
- `GET /api/busca?q=...`
- `GET/POST/DELETE /api/favoritos`

Todas as rotas exigem sessão autenticada. Parâmetros validados por lista fechada (nada de SQL montado por string), em linha com RN 3.

### 6.3 Supressão estatística

Escolas/municípios com poucos participantes (limite configurável, padrão n < 10) vêm com `suprimido=true` e não entram em ranking nem em média. Mostrar "dados insuficientes".

## 7. Privacidade e LGPD **[ABERTO, ponto de atenção]**

O documento do projeto registra que nomes de medalhistas, mesmo públicos, são dado pessoal, e muitos são menores. A decisão final (T2.10) ainda não foi tomada. Em conversa, foi indicado acesso total a alunos identificados para a equipe interna. Para conciliar:

- Implementar um **flag de configuração `ALUNO_IDENTIFICADO`** (padrão `false`). Com `false`, a lista mostra o aluno **pseudonimizado** (ex.: iniciais + código) e sem dados de contato. Com `true`, mostra nome completo.
- **Registrar log de auditoria** (e-mail do usuário, data/hora, aluno ou município consultado) sempre que a lista de medalhistas for aberta.
- Não expor aluno em URL, nem em exportação, sem o flag ligado.
- Acesso restrito à coordenação do IP, pelo login já existente. Se houver lista de e-mails autorizados além do domínio institucional, respeitá-la.
- Os arquivos com nomes não devem ficar no repositório público, e sim no Google Drive indicado pelo projeto, ou em armazenamento privado.

## 8. Requisitos não funcionais (do documento)

- RN 1: até 10 usuários simultâneos.
- RN 2: carregamento inicial em até 2 s (carregar só o Brasil/UF; municípios sob demanda).
- RN 3: proteção contra SQL injection e demais injeções (validação por lista fechada, queries parametrizadas).
- RN 4: clique/zoom em município sem travar mais que 10 s (meta real: abaixo de 1 s).
- RN 5: troca de filtro sem travar mais que 30 s (meta real: abaixo de 2 s, graças ao pré-cálculo).
- RN 6: dados de no máximo 10 anos.
- RN 7: acessibilidade (seção 4.7).

## 9. Ordem de implementação sugerida

1. **Casca e dados mockados:** mapa do Brasil em D3 com UFs coloridas por valor fictício, legenda, zoom/pan, atrás do login.
2. **Drill-down:** UF → municípios (TopoJSON por UF), tooltip, breadcrumb.
3. **Painel do município** com dados mockados, depois conectar ao contrato real.
4. **Filtros** refletindo no mapa (etapa, prova, sexo, renda, ano), com estados desabilitados para combinações inválidas.
5. **Dados reais** via API e pré-computação; supressão estatística.
6. **Busca e favoritos.**
7. **Mobile, acessibilidade e performance** (medir RN 2, 4, 5).
8. **Privacidade:** flag de aluno identificado e log de auditoria (pode ser antecipada se medalhistas entrarem cedo).

## 10. Critérios de aceite

- Usuário não autenticado ou fora do domínio não acessa nenhuma rota do mapa nem da API.
- Clicar em uma UF dá zoom e mostra seus municípios coloridos; clicar em um município abre o painel com escolas ranqueadas pelo Saeb.
- Ativar "feminino" + medalhas recolore o mapa só com medalhas de meninas.
- ENEM nunca aparece por escola.
- Municípios com poucos dados aparecem como "dados insuficientes", sem entrar na legenda.
- Funciona em tela de 375 px de largura e em desktop.
- Carregamento inicial ≤ 2 s em conexão comum.
- Cada abertura de lista de medalhistas gera registro de auditoria.

## 11. Decisões em aberto (resumo)

1. Critério oficial de **escola destaque** e **aluno destaque**.
2. Fórmula e pesos do **índice composto**.
3. Política de **LGPD**: alunos identificados ou pseudonimizados, retenção, base legal. Alinhar com jurídico/coordenação.
4. Favoritos pessoais ou compartilhados.
5. Escopo geográfico inicial (Brasil inteiro ou alguns estados) e volume real de escolas e medalhistas.
6. Hospedagem e domínio (pendentes no documento do projeto).
7. Disponibilidade do Saeb 2025 (só via site, pode exigir scraping).