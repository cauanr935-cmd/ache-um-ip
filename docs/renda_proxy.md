# Proxy de renda per capita ≤ 1,5 SM (T2.5)

**É uma faixa declarada, não o valor exato da renda.** Fonte: ENEM (questionário socioeconômico), origem `microdados` (2023) e `participantes` (2024–2025), recorte EM (`tp_st_conclusao` ∈ {1, 2}), agregado por **município da prova**. Configuração: `config/renda.yaml`; código: `src/renda.py`, `src/agregacoes.py`.

## Fórmula
Para cada inscrito com faixa `renda_familiar_faixa` (A–Q) e `q005` (moradores, incluindo o respondente; 1–20):

- `renda_pc_sm = ponto_médio_da_faixa(SM) ÷ q005`  (proxy central)
- Intervalo: `[lim_inf ÷ q005 , lim_sup ÷ q005]` (faixa = (lim_inf, lim_sup])
- **Flag central:** `renda_pc_sm ≤ 1.5`  → `pct_renda_pc_le_1_5_ponto_medio`
- **Classe pelo intervalo:** `certamente_le` se `lim_sup ÷ q005 ≤ 1.5`; `acima` se `lim_inf ÷ q005 ≥ 1.5`; caso contrário `possivelmente` → `pct_certamente_le_1_5`, `pct_possivelmente_le_1_5`, `pct_acima_1_5` (somam 100%). O número "verdadeiro" fica entre `pct_certamente_le_1_5` e `pct_certamente_le_1_5 + pct_possivelmente_le_1_5`.
- Agregação por município × ano: `n` (inscritos EM), `n_renda_valida`, mediana do proxy (`mediana_renda_pc_sm`, e em R$ com o SM do ano em `mediana_renda_pc_reais`).

## Faixas e salário mínimo de referência
As faixas A–Q do ENEM são **múltiplos do salário mínimo** do ano; as letras são as mesmas em 2023–2025 e os limites em SM também (conferido nos dicionários oficiais). Por isso o proxy em **SM per capita** é comparável entre anos; o SM só converte para R$.

| ano | SM de referência (R$) |
|---|---|
| 2023 | 1320 |
| 2024 | 1412 |
| 2025 | 1518 |

| faixa | lim_inf (SM) | lim_sup (SM) | ponto médio (SM) |
|---|---|---|---|
| A | 0.0 | 0 | 0.0 |
| B | 0.0 | 1 | 0.5 |
| C | 1.0 | 1.5 | 1.25 |
| D | 1.5 | 2 | 1.75 |
| E | 2.0 | 2.5 | 2.25 |
| F | 2.5 | 3 | 2.75 |
| G | 3.0 | 4 | 3.5 |
| H | 4.0 | 5 | 4.5 |
| I | 5.0 | 6 | 5.5 |
| J | 6.0 | 7 | 6.5 |
| K | 7.0 | 8 | 7.5 |
| L | 8.0 | 9 | 8.5 |
| M | 9.0 | 10 | 9.5 |
| N | 10.0 | 12 | 11.0 |
| O | 12.0 | 15 | 13.5 |
| P | 15.0 | 20 | 17.5 |
| Q | 20.0 | ∞ | 25.0 |

- **Faixa A** (nenhuma renda) → 0 SM (certamente ≤ 1,5).
- **Faixa Q** (acima de 20 SM, aberta): ponto médio **arbitrado em 25 SM (1,25 × limite inferior)**; `lim_sup` = ∞. Só afeta o proxy central de quem declara >20 SM; com `q005 ≤ 20` o intervalo nunca é `certamente_le` (correto) e a classe é `acima` sempre que `20 ÷ q005 ≥ 1,5`.
- Colunas usadas: 2023 `Q006` (renda familiar); 2024–2025 `Q007` (já harmonizada em `renda_familiar_faixa`; `Q006` virou "possui renda?" e **não** deve ser usada).

## Resultado nacional (ponderado por inscritos com renda válida; só municípios não suprimidos)
| ano | municípios | n (EM) | % ≤1,5 SM (ponto médio, pond. por n) | % certamente ≤1,5 | % possivelmente | % acima |
|---|---|---|---|---|---|---|
| 2023 | 1750 | 3296465 | 90.5 | 89.4 | 1.1 | 9.5 |
| 2024 | 1753 | 3463913 | 90.9 | 89.6 | 1.3 | 9.1 |
| 2025 | 1805 | 3699664 | 91.2 | 90.2 | 0.9 | 8.8 |

## Limitações
- Faixa declarada: erro de classificação nas fronteiras (a classe `possivelmente` quantifica a incerteza).
- `q005` tem teto 20 (categoria "20" agrupa 20 ou mais) e o ponto médio supõe renda uniforme na faixa.
- Renda familiar é autodeclarada pelo estudante; EM concluintes/cursando 3ª série (2023: `tp_st_conclusao` 1 e 2; treineiros não identificáveis).
- Granularidade = **município da prova** (não da escola nem da residência). Em 2024–2025 não há ligação com notas ou escola.
- Participantes sem renda ou `q005` válidos ficam fora de `n_renda_valida`; células com `n_renda_valida` < n_min (10) têm renda nula.
- **Saeb:** não há conversão para renda. Usam-se apenas `inse_escola` e `inse_aluno_medio` já existentes, sem equivalência com renda per capita (escalas "Grupo" em 2017 e "Nível" depois; ids de escola fictícios).
