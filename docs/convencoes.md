# Convenções do projeto

- **Codificação:** UTF-8 em todos os arquivos gerados (os CSVs brutos do INEP costumam vir em ISO-8859-1 e são convertidos na leitura).
- **Nomes de colunas e arquivos:** `snake_case`, minúsculo, sem acentos.
- **Município:** código IBGE de 7 dígitos, tipo `string` (ex.: `"3550308"`); nunca inteiro (preserva zeros à esquerda).
- **Escola:** `co_entidade` INEP de 8 dígitos, tipo `string`.
- **Ano:** inteiro (`int`).
- **UF:** sigla de 2 letras maiúsculas.
- **Dados:** brutos em `data/raw` e intermediários em `data/interim` (ambos fora do versionamento); finais em `data/processed`.
- **LGPD:** nome de aluno em claro apenas em `data/interim`; nunca em `data/processed`.
- **Código:** módulos em `src/`; o notebook Colab é gerado a partir deles.
