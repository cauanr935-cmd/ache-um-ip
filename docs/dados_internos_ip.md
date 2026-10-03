# Dados internos do Instituto Ponte (IP) — esquema esperado, perguntas e anonimização (T1.17–T1.18)

> **Nenhum dado real do IP foi acessado.** Este documento descreve o que se *espera* encontrar, o que perguntar à coordenação e como anonimizar **antes** de qualquer integração. Status: **pendente de dado e de decisão da coordenação** (também bloqueia T4.2).

## 1. Para que servem (RF 3, RF 3.1, T4.2)
Validação de negócio: o top-N de municípios do índice bate com as cidades onde o IP já tem alunos? Para isso **basta contagem por município**; dados individuais não são necessários para o modelo.

## 2. Esquema esperado (hipótese a confirmar)
| Campo (hipotético) | Descrição | Tipo | Sensibilidade | Necessário? |
|---|---|---|---|---|
| `id_aluno_ip` | Identificador interno | texto | Pseudônimo se interno | Só se linha a linha |
| Perfil: `faixa_etaria`, `sexo` | Perfil demográfico (RF 5.3) | categórica | Pessoal (menor de idade) | Opcional, **agregado** |
| Perfil: renda familiar (faixa) | Para comparar com RF 5.4 | categórica | Sensível | Opcional, agregado |
| Perfil: cor/raça, deficiência | Se existir | categórica | **Sensível (LGPD art. 5º, II)** | **Não** |
| `escola_origem_nome` | Escola em que estudava | texto | Pessoal por inferência | Só para linkage |
| `escola_origem_co_entidade` | Código INEP (8 dígitos, string), se já registrado | texto | Baixa | Preferível ao nome |
| `rede_escola_origem` | Pública/privada | categórica | Baixa | Sim |
| `cidade_origem` / `co_municipio` | Cidade (preferir IBGE 7 dígitos, string) | texto | Média | **Sim** |
| `uf_origem` | UF | texto | Baixa | Sim |
| `ano_ingresso` | Ano de entrada no IP (int) | inteiro | Baixa | **Sim** |
| `etapa_ingresso` | EF2 / EM | categórica | Baixa | Sim (RF 5.1) |
| `medalhista` / `olimpiada` | Se entrou por olimpíada (liga com `fato_medalhas`) | booleano/texto | Média | Opcional |
| `status` | Ativo, egresso, desligado | categórica | Baixa | Opcional |
| Identificadores diretos (nome, CPF, e-mail, telefone, endereço, nome dos responsáveis) | — | — | **Alta** | **Não receber** |

## 3. Perguntas para a coordenação
**Existência e qualidade**
1. Existe uma base consolidada de alunos já matriculados? Em que sistema (planilha, banco, CRM) e quem a mantém?
2. Quais campos existem hoje dos listados acima? Desde que ano há registros? Quantos alunos?
3. A escola de origem está registrada por **código INEP** ou só por nome livre? A cidade é padronizada (IBGE) ou texto livre?
4. Como o IP registra a forma de ingresso (olimpíada, indicação, processo seletivo)? Dá para distinguir medalhistas?

**Acesso e finalidade**
5. Quem é o controlador/encarregado (DPO) pelos dados? A finalidade original de coleta permite uso analítico?
6. Qual a base legal usada (consentimento dos responsáveis, execução de programa)? O termo de consentimento cobre uso estatístico/pesquisa?
7. Há acordo ou política interna para compartilhar dados com a equipe do projeto? Há prazo de retenção definido?
8. Estão disponíveis alunos já egressos? E menores de 18 anos (a maioria)?

**Anonimização**
9. A coordenação aceita entregar **apenas tabela agregada** (município × ano de ingresso × etapa, com contagens)?
10. Se for linha a linha, quem faria a pseudonimização (idealmente o próprio IP) e onde ficaria o segredo/chave?
11. Qual a regra de supressão desejada para municípios com poucos alunos (sugestão: n < 10)?
12. Os resultados do projeto (mapa, rankings) poderão citar o IP e mostrar as cidades dos alunos? Em que nível de detalhe?

## 4. Proposta de anonimização (a validar com a coordenação)
**Nível A — recomendado: dado agregado entregue pelo IP.**
- O IP entrega `co_municipio`, `uf`, `ano_ingresso`, `etapa_ingresso`, `n_alunos` (e, se quiser, `sexo`, `rede_escola_origem` já agregados).
- **Supressão:** células com n < 10 são agrupadas (UF ou "outros") ou omitidas, como na T2.9.
- Nenhum identificador individual entra no projeto. Risco residual baixo.

**Nível B — só se houver necessidade analítica: linha a linha pseudonimizada.**
- Remover nome, CPF, contatos, endereço, nomes de responsáveis; manter só os campos marcados "Sim"/"Opcional" da tabela.
- `id_aluno_ip` = HMAC-SHA256 de um identificador interno com **sal/chave guardados só no IP**; nunca no repositório.
- Generalizar: data de nascimento → faixa etária; endereço → município; renda → faixa.
- Checar k-anonimato (k ≥ 5) sobre quase-identificadores (município, ano, etapa, sexo, rede) e suprimir/agrupar o que violar.

**Nível C — não receber** dado individual (se a coordenação não aprovar A ou B).

**Controles comuns**
- Dados internos ficam **fora do Git** (`data/raw/ip/`, coberto por `.gitignore`), acesso restrito; nada disso entra em `data/processed` além de contagens agregadas já suprimidas.
- Registrar origem, data de recebimento, base legal e prazo de descarte (sugestão: apagar o bruto ao fim da validação T4.2).
- Alinhar com a política de LGPD da T2.10 e com a decisão de exibição pública sempre **agregada** (entregáveis do projeto, risco de reidentificação de menores).

## 5. Entregáveis esperados da coordenação
Resposta às perguntas 1–12; escolha do Nível A/B/C; arquivo conforme o nível escolhido; contato do responsável pelos dados.

## 6. O que ainda falta
Tudo acima. Sem a base, **T4.2 permanece como esqueleto** e RF 3/3.1 ficam não atendidos nesta sprint.
