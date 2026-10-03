# Ata da reunião de validação com o Instituto Ponte (T4.5) — template

**Status: reunião ainda não realizada.** Preencher durante/depois da reunião.

| Campo | Preenchimento |
|---|---|
| Data / horário | |
| Local / link | |
| Participantes (nome, cargo, instituição) | |
| Responsável pela ata | |

## 1. Pauta

1. Objetivo do projeto e escopo da modelagem (índice de potencial, clusters, modelo de expectativa).
2. Apresentação do ranking e dos clusters (`docs/avaliacao.md`, `rankings.parquet`).
3. Comparação com as cidades do IP (`docs/validacao_negocio_template.md`).
4. Decisões de modelagem em aberto (abaixo).
5. Uso e publicação dos resultados; LGPD.
6. Próximos passos.

## 2. Decisões que precisam do IP

| # | Pergunta | Opções | Decisão do IP |
|---|---|---|---|
| 1 | Sinal da qualidade da rede no índice | +1 (priorizar rede forte) / −1 (priorizar rede carente) | |
| 2 | Pesos (talento 0,50 / rede 0,20 / vulnerabilidade 0,30) | manter / ajustar | |
| 3 | Corte de vulnerabilidade | renda per capita ≤ 1,5 SM / outro | |
| 4 | Granularidade exigida | município / escola | |
| 5 | Uso de sexo no recorte | agregado do IP disponível? | |
| 6 | Regra de supressão para contagens pequenas | n < 10 (padrão) / outra | |

## 3. Resultados da comparação com dados do IP

| Métrica | Valor | Observações |
|---|---|---|
| Aderência do top-50 / top-100 / top-200 | | |
| Spearman índice × alunos do IP por 100 mil hab. | | |
| Cidades do IP fora do top-N | | |
| Cidades top-N sem aluno do IP | | |

## 4. Feedback qualitativo

| Tema | Comentário do IP | Ação |
|---|---|---|
| Cidades que surpreendem | | |
| Variáveis que faltam | | |
| Clareza dos clusters | | |

## 5. Dados e LGPD

- [ ] IP aceita entregar apenas tabela agregada (município × ano × etapa × n)? Prazo: ____
- [ ] Regra de supressão acordada: ____
- [ ] IP autoriza citar o nome do Instituto e mostrar cidades em materiais públicos? Nível de detalhe: ____

## 6. Encaminhamentos

| Ação | Responsável | Prazo |
|---|---|---|
| | | |

## 7. Aprovação

Validação do IP sobre os resultados: ( ) aprovado ( ) aprovado com ressalvas ( ) não aprovado. Ressalvas: ____
