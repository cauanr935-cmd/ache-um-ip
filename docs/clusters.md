# Clusters de municípios (T3.3)

K-Means (`random_state=42`, `n_init=10`) sobre 4571 municípios com as 5 variáveis completas, padronizadas (z-score): `log(1+taxa de medalhas suavizada)`, nota Saeb padronizada, Ideb, renda per capita mediana (SM, suavizada) e `log(população)`.
Municípios sem alguma dessas variáveis (sem Saeb/Ideb publicado ou com < 10 participantes no ENEM) ficam **sem cluster**.

## Escolha de k (silhouette; k de 3 a 8) → **k = 3**

| k | silhouette | davies_bouldin |
|---|---|---|
| 3 | 0.2902 | 1.3303 |
| 4 | 0.231 | 1.307 |
| 5 | 0.2285 | 1.2996 |
| 6 | 0.2244 | 1.2947 |
| 7 | 0.2239 | 1.279 |
| 8 | 0.2306 | 1.2695 |

## Perfil dos clusters

Médias por cluster (taxa de medalhas = mediana da taxa bruta por 100 mil hab.). `perfil_automatico` lista as variáveis cujo centróide está a ≥ 0,5 desvio-padrão da média geral.

| cluster | municipios | populacao_mediana | medalhas_total | taxa_medalhas_100k | saeb_padr | ideb | renda_pc_sm | pct_renda_le_1_5 | indice | perfil_automatico |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1680 | 8086.5 | 8477 | 23.03 | 5.37 | 5.25 | 0.33 | 95.73 | 0.6 | taxa de medalhas acima da média, nota Saeb acima da média, Ideb acima da média, porte abaixo da média |
| 1 | 2046 | 15351.0 | 4260 | 1.64 | 4.52 | 4.29 | 0.23 | 98.02 | 0.41 | taxa de medalhas abaixo da média, nota Saeb abaixo da média, Ideb abaixo da média, renda per capita abaixo da média |
| 2 | 845 | 47011.0 | 35029 | 19.48 | 5.22 | 5.0 | 0.52 | 89.33 | 0.43 | renda per capita acima da média, porte acima da média |

## Distribuição por região (nº de municípios)

| cluster | CO | N | NE | S | SE |
|---|---|---|---|---|---|
| 0 | 186 | 24 | 385 | 510 | 575 |
| 1 | 155 | 362 | 1211 | 55 | 263 |
| 2 | 73 | 17 | 24 | 318 | 413 |

## Cuidados de leitura

- Silhouette baixo/moderado é esperado: os dados formam um contínuo, não grupos bem separados. Os clusters servem para agrupar municípios comparáveis, não para afirmar categorias naturais.
- `porte` entra como variável de propósito: separa grandes centros de municípios pequenos, onde a taxa de medalhas é mais ruidosa.
- Os rótulos automáticos são descritivos; nomeie os clusters com o IP antes de usar em apresentação.
