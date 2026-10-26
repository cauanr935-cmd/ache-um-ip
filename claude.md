# Ache um IP

Site interno do Instituto Ponte (IP) que usa dados de provas e avaliações (ENEM, Saeb, olimpíadas) para mostrar, em um mapa do Brasil, onde estão as escolas e os alunos com mais potencial para o IP.

Propósito do IP: ser a ponte para a ascensão social em uma geração, por meio da educação de qualidade, para jovens em vulnerabilidade social. Perfil buscado: alunos talentosos de escola pública, renda per capita até 1,5 salário mínimo, premiados em olimpíadas.

## Regra principal

**Antes de escrever ou alterar qualquer código, leia `specs.md` inteiro.** Ele é a fonte de verdade para o mapa: navegação, filtros, mapa de calor, API, privacidade, requisitos não funcionais, ordem de implementação e critérios de aceite. Se algo no código ou neste arquivo conflitar com o `specs.md`, siga o `specs.md` e avise o usuário. Itens marcados **[ABERTO]** no `specs.md` não devem ser decididos sozinho: use o padrão indicado e deixe configurável.

## Stack

- Front: JavaScript, CSS e **D3.js** (d3-geo, d3-zoom, d3-scale) para o mapa.
- Back: JavaScript, usando o framework já presente no repositório.
- Dados: arquivos tratados em Parquet/CSV (opcionalmente DuckDB/SQLite). Banco de dados completo não é necessário nesta fase.
- Login com Google, restrito a e-mail institucional, **já implementado**. Reaproveite, não reescreva. Toda rota de página e de API fica atrás dele.

## Dados e convenções

- Fontes: microdados do ENEM e do Saeb (INEP), listas de premiados OBMEP, OBI e ONHB, catálogo de escolas do INEP, municípios e malhas do IBGE. Dados com no máximo 10 anos.
- Chaves canônicas: município = código IBGE de 7 dígitos; escola = `CO_ENTIDADE` do INEP, 8 dígitos.
- Granularidade principal: **município**. O ENEM só existe por município (sem código de escola), o Saeb vai até a escola e as olimpíadas até o aluno.
- Tabelas analíticas: `dim_municipio`, `dim_escola`, `dim_aluno`, `fato_desempenho`, `fato_medalhas`. Contrato: uma métrica por município por recorte (etapa, prova, sexo, renda, ano, rede), com schema estável.
- Renda ≤ 1,5 SM é uma estimativa (faixa declarada), então sempre rotule como "estimado".
- Escolas ou municípios com poucos participantes são suprimidos ("dados insuficientes").

## Segurança e LGPD

- Nomes de medalhistas são dado pessoal, mesmo sendo públicos, e muitos são menores de idade. Siga a seção de privacidade do `specs.md` (flag `ALUNO_IDENTIFICADO`, log de auditoria).
- Nunca commitar arquivos com nomes de alunos. Esses dados ficam no Google Drive do projeto ou em armazenamento privado.
- Nunca montar SQL ou queries por concatenação de string; validar parâmetros por lista fechada. Nunca expor segredos no front.

## Como trabalhar

- Siga a ordem de implementação do `specs.md` e entregue em passos pequenos que rodem de ponta a ponta.
- Ao terminar uma tarefa, confira os critérios de aceite do `specs.md` que ela afeta.
- Na dúvida entre duas interpretações do `specs.md`, pergunte antes de implementar.
- Comentários, textos de interface e commits em português.
- Não adicionar dependências grandes sem necessidade; o projeto é pequeno (até 10 usuários simultâneos).

## Repositório

github.com/cauanr935-cmd/ache-um-ip (dono: Cauan). Equipe: Cauan, Emanuel, Davi Amaral. Metodologia: Agile, com dados seguindo CRISP-DM.