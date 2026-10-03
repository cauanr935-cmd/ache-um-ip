# Validação de negócio com dados do IP — template (T4.2)

**Status: pendente de dado.** Nenhum dado do Instituto Ponte foi acessado (`docs/dados_internos_ip.md`). Este documento lista as cidades a comparar e o que o IP precisa fornecer. Pergunta: *o ranking do índice bate com as cidades de onde o IP já recruta/aprova alunos?*

## O que pedir ao IP (apenas agregado)

- Tabela `co_municipio` (IBGE 7 dígitos) × `ano_ingresso` × `etapa_ingresso` × `n_alunos` (supressão n < 10; ver `config/supressao.yaml`).
- Opcional: sexo e rede da escola de origem, já agregados. Nenhum dado individual é necessário.

## Como comparar (preencher quando houver dado)

1. **Aderência do top-N:** % dos municípios com alunos do IP que estão no top-N do índice (N = 50, 100, 200) vs. % esperado ao acaso.
2. **Correlação:** Spearman entre `indice` e alunos do IP por 100 mil hab. (apenas municípios com ENEM/Saeb).
3. **Lacunas nos dois sentidos:** cidades do IP fora do top-N (o índice perde algo?) e cidades top-N sem aluno do IP (oportunidade ou ruído?).
4. Registrar a leitura do IP na coluna `observacao_ip` e as decisões em `docs/ata_validacao_ip.md`.

Critério de aceite a combinar com o IP (sugestão, não validado): aderência do top-100 ≥ 2× o acaso e Spearman > 0.

## A. Top 15 do índice entre municípios com ≥ 50 mil habitantes

| co_municipio | no_municipio | uf | pop | indice | cluster | medalhas (O+P+B) | % renda<=1,5SM | alunos_ip (n) | observacao_ip |
|---|---|---|---|---|---|---|---|---|---|
| 2702306 | Coruripe | AL | 50414 | 0.95 | 0 | 56 | 98.6 |  |  |
| 2300200 | Acaraú | CE | 65264 | 0.921 | 0 | 25 | 99.3 |  |  |
| 2312908 | Sobral | CE | 203023 | 0.919 | 0 | 222 | 94.9 |  |  |
| 2302800 | Canindé | CE | 74174 | 0.901 | 0 | 26 | 98.9 |  |  |
| 2306405 | Itapipoca | CE | 131123 | 0.9 | 0 | 53 | 98.6 |  |  |
| 2314102 | Viçosa do Ceará | CE | 59712 | 0.869 | 0 | 21 | 99.3 |  |  |
| 2208403 | Piripiri | PI | 65538 | 0.866 | 0 | 21 | 98.6 |  |  |
| 2312403 | São Gonçalo do Amarante | CE | 54143 | 0.863 | 0 | 29 | 98.6 |  |  |
| 2311801 | Russas | CE | 72928 | 0.857 | 0 | 25 | 97.8 |  |  |
| 2304400 | Fortaleza | CE | 2428708 | 0.853 | 2 | 1889 | 90.5 |  |  |
| 2302602 | Camocim | CE | 62326 | 0.85 | 0 | 22 | 98.5 |  |  |
| 2612208 | Salgueiro | PE | 62372 | 0.83 | 0 | 21 | 97.5 |  |  |
| 2700300 | Arapiraca | AL | 234696 | 0.829 | 2 | 69 | 96.4 |  |  |
| 2304103 | Crateús | CE | 76390 | 0.82 | 0 | 20 | 97.5 |  |  |
| 2211001 | Teresina | PI | 866300 | 0.82 | 2 | 360 | 91.8 |  |  |

## B. Municípios com mais medalhas que o esperado (modelo de expectativa, T3.4)

| co_municipio | no_municipio | uf | pop | indice | cluster | medalhas (O+P+B) | % renda<=1,5SM | alunos_ip (n) | observacao_ip |
|---|---|---|---|---|---|---|---|---|---|
| 2202729 | Cocal dos Alves | PI | 6386 | 0.933 | 0 | 141 | 100.0 |  |  |
| 3123304 | Dores do Turvo | MG | 4987 | 0.821 | 0 | 63 | 100.0 |  |  |
| 2931053 | Tanque Novo | BA | 17158 | 0.876 | 0 | 98 | 94.6 |  |  |
| 2611533 | Quixaba | PE | 6554 | 0.859 | 0 | 52 | 98.0 |  |  |
| 3141009 | Mato Verde | MG | 12038 | 0.795 | 0 | 55 | 100.0 |  |  |
| 2104099 | Formosa da Serra Negra | MA | 17719 | 0.804 | 1 | 46 | 99.4 |  |  |
| 3203346 | Marechal Floriano | ES | 17641 | 0.776 | 0 | 85 | 91.1 |  |  |
| 2307254 | Jijoca de Jericoacoara | CE | 25555 | 0.947 | 0 | 54 | 98.2 |  |  |
| 3117801 | Conceição dos Ouros | MG | 10880 | 0.757 | 0 | 42 | 93.3 |  |  |
| 2303105 | Cariré | CE | 17632 | 0.978 | 0 | 34 | 99.6 |  |  |

## C. Grupo de controle: 10 menores índices entre municípios com ≥ 50 mil habitantes

| co_municipio | no_municipio | uf | pop | indice | cluster | medalhas (O+P+B) | % renda<=1,5SM | alunos_ip (n) | observacao_ip |
|---|---|---|---|---|---|---|---|---|---|
| 4216206 | São Francisco do Sul | SC | 52674 | 0.077 | 2 | <10 | 85.0 |  |  |
| 4203204 | Camboriú | SC | 103074 | 0.089 | 2 | <10 | 89.6 |  |  |
| 3534401 | Osasco | SP | 728615 | 0.1 | 2 | 56 | 84.1 |  |  |
| 3524006 | Itupeva | SP | 70616 | 0.109 | 2 | <10 | 80.3 |  |  |
| 5108402 | Várzea Grande | MT | 300078 | 0.11 | 1 | 10 | 93.3 |  |  |
| 5107925 | Sorriso | MT | 110635 | 0.115 | 2 | <10 | 84.9 |  |  |
| 3522505 | Itapevi | SP | 232297 | 0.119 | 1 | <10 | 95.3 |  |  |
| 4202305 | Biguaçu | SC | 76773 | 0.121 | 2 | <10 | 89.0 |  |  |
| 5106752 | Pontes e Lacerda | MT | 52018 | 0.123 | 1 | <10 | 89.5 |  |  |
| 4300604 | Alvorada | RS | 187315 | 0.124 | 2 | <10 | 95.0 |  |  |

## D. Capitais de referência (sugestão de comparação com grandes centros)

| co_municipio | no_municipio | uf | pop | indice | cluster | medalhas (O+P+B) | % renda<=1,5SM | alunos_ip (n) | observacao_ip |
|---|---|---|---|---|---|---|---|---|---|
| 1302603 | Manaus | AM | 2063689 | 0.684 | 2 | 523 | 94.5 |  |  |
| 1501402 | Belém | PA | 1303403 | 0.376 | 2 | 180 | 93.5 |  |  |
| 2304400 | Fortaleza | CE | 2428708 | 0.853 | 2 | 1889 | 90.5 |  |  |
| 2611606 | Recife | PE | 1488920 | 0.778 | 2 | 773 | 86.7 |  |  |
| 2927408 | Salvador | BA | 2417678 | 0.346 | 2 | 340 | 90.9 |  |  |
| 3304557 | Rio de Janeiro | RJ | 6211223 | 0.613 | 2 | 2034 | 83.6 |  |  |
| 3550308 | São Paulo | SP | 11451999 | 0.477 | 2 | 2698 | 81.8 |  |  |
| 4106902 | Curitiba | PR | 1773718 | 0.652 | 2 | 803 | 77.0 |  |  |
| 4314902 | Porto Alegre | RS | 1332845 | 0.594 | 2 | 460 | 76.7 |  |  |
| 5300108 | Brasília | DF | 2817381 | 0.643 | 2 | 1453 | 79.2 |  |  |

`medalhas (O+P+B)` aparece como `<10` onde a contagem é suprimida. Cidades onde o IP atua e que não estejam acima devem ser acrescentadas pelo IP; o script `src/avaliacao.py` regenera as tabelas.
