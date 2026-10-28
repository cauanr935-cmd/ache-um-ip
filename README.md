# Ache um IP

Site interno do Instituto Ponte: um mapa do Brasil que usa dados de provas (Saeb, ENEM, INSE) e olimpíadas (OBMEP, OBI, OCMAT) para mostrar onde estão os talentos que o Instituto pode procurar, e onde já estão seus alunos.

- **Documentação completa:** [docs/documentacao.md](docs/documentacao.md)
- **Especificação do mapa:** [specs.md](specs.md)
- **Convenções de trabalho:** [claude.md](claude.md)

## Rodar localmente

```bash
npm install
cp .env.example .env   # preencha GOOGLE_CLIENT_ID e SESSION_SECRET
npm run dev            # http://localhost:3000
npm test
```

Os dados que o mapa mostra ficam em `data/api/` (gerados por `src/api_precompute.py`). Nomes de alunos nunca vão para o git: ficam em `data/privado/` e no Redis. Detalhes na documentação.
