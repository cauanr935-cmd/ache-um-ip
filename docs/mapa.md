# Mapa "Ache um IP": como roda e o que foi entregue

Implementação dos passos 1 a 8 do `specs.md` (seção 9). Front em `screens/`, back em `server/`, pré-cálculo em `src/api_precompute.py`.

## Como rodar
1. `npm install`
2. Copie `.env.example` para `.env` e preencha (`GOOGLE_CLIENT_ID`, `SESSION_SECRET`, domínios). Em desenvolvimento use `NODE_ENV=development`.
3. Gere os dados que a API serve: `.venv/bin/python src/api_precompute.py` (~2 min; lê `data/interim/agg_*.parquet` e `medalhistas_enriquecido.parquet`, exige `config/lgpd.yaml`).
4. `npm run dev` e abra `http://localhost:3000`. Testes: `npm test`.

Saídas do pré-cálculo (todas fora do git):
- `data/api/` (60 MB): catálogo de recortes, mapa por UF e por município, painel do município, ficha da escola, índice de busca. Sem nome de aluno.
- `data/privado/medalhistas/<UF>.json`: lista por município **com nome em claro**. Só o servidor lê.
- `data/privado/favoritos.json` e `data/privado/auditoria.jsonl`: criados pelo servidor em execução.

## API (todas atrás do login)
`/api/recortes`, `/api/mapa`, `/api/municipio/:ibge`, `/api/municipio/:ibge/medalhistas`, `/api/escola/:inep`, `/api/busca?q=`, `GET/POST /api/favoritos`, `DELETE /api/favoritos/:tipo/:id`. Parâmetros validados por lista fechada (catálogo); POST/DELETE exigem mesma origem e JSON.

## Privacidade (specs.md 7)
- `ALUNO_IDENTIFICADO=false` (padrão): a lista mostra iniciais + código (hash com o sal de `config/lgpd.yaml`); o nome nem sai do servidor. Com `true` mostra o nome completo.
- Cada abertura da lista grava uma linha em `data/privado/auditoria.jsonl` (quando, e-mail, município, se identificado, quantidade). Se a gravação falhar, a lista não é entregue.
- A lista só abre por clique explícito; não há exportação nem aluno em URL.

## Limitações dos dados (o mapa desabilita a opção e explica)
- Sem recorte por **sexo** e sem cruzamento de **renda** com nota/medalha. Renda ≤ 1,5 SM (estimada) aparece só no contexto do município.
- **ONHB** não existe nos dados. **OBI** não informa a rede da escola (só rede "todas").
- Saeb no mapa: 2017 a 2023 (nível UF só existe até 2023). O painel usa a edição mais recente de escolas (2025), rotulada com o ano.
- Escola destaque (provisório, [ABERTO]): top 10% da UF na etapa pela nota Saeb, ou ≥ 1 medalhista com vínculo automático à escola.
- Candidatos ao IP: base interna ainda não integrada.

## Critérios de aceite (specs.md 10)
| critério | situação |
|---|---|
| Não autenticado/fora do domínio não acessa mapa nem API | ok (testes em `server/app.test.js`) |
| Clique em UF dá zoom e mostra municípios; município abre painel com escolas ranqueadas | ok |
| "Feminino" + medalhas recolore só com medalhas de meninas | **não atendido**: as bases não têm sexo (opção desabilitada com explicação) |
| ENEM nunca por escola | ok (só município) |
| Poucos dados = "dados insuficientes", fora da legenda | ok (n < 10; suprimidos fora dos quantis) |
| 375 px e desktop | ok (sem rolagem horizontal; axe WCAG 2.1 A/AA sem violações) |
| Carregamento inicial ≤ 2 s | ok: 0,24 s em localhost, 206 KB transferidos |
| Cada abertura da lista de medalhistas gera auditoria | ok |

## Medições (Chrome headless, localhost, 26/10/2026)
Mapa pintado 0,24 s; clique em UF até municípios 0,8 a 0,9 s; clique em município até painel 0,13 a 0,17 s; troca de filtro 0,15 a 0,22 s. Metas: RN 2 ≤ 2 s, RN 4 < 1 s, RN 5 < 2 s.
