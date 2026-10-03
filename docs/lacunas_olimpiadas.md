# Lacunas — Olimpíadas (T1.8–T1.10)

Regra aplicada: onde bastava HTML simples, coletou-se com as mesmas regras do OBMEP (HTML baixado uma vez, pausa de 1,5 s,
User-Agent identificado, 3 tentativas). Onde exigiria login/interação, **não se forçou**.

## OBMEP (T1.8) — coletada: 2016–2019, 2024, 2025
- **2020–2023 ausentes.** O índice lista as edições 16ª, 17ª e 18ª, mas as páginas delas não informam o ano (só o número da edição) e o ano não foi inferido. Para recuperar: confirmar os anos na fonte oficial e preencher `config/obmep_anos.yaml`, depois rodar `python src/coleta_obmep.py` (mais `python src/medalhistas.py`). Detalhes: `lacunas.md` e `cobertura_obmep.md`.
- Páginas não trazem código INEP da escola (linkage = T2.3). 2016 só tem escolas públicas.
- Premiação *estadual* (segundo menu) não foi coletada.

## OBI (T1.9) — coletada: 2016, 2017, 2019, 2020, 2021, 2022, 2023, 2024, 2025
Fonte: `https://olimpiada.ic.unicamp.br/passadas/` → página de cada edição → "Quadro de Medalhas" por modalidade/nível (tabela HTML: medalha, classificação, nota, nome, escola, cidade, UF). Sem login, sem captcha; `robots.txt` inexistente (devolve página de erro).
- OBI 2018: edição: falha ao baixar https://olimpiada.ic.unicamp.br/passadas/OBI2018/: 404 Client Error: Not Found for url: https://olimpiada.ic.unicamp.br/passadas/OBI2018/
- **2018:** o link da edição consta no índice, mas a página responde 404 (verificado em 02/10/2026). Sem outra fonte identificada; pendente.
- Sem `rede` e sem código INEP; `posicao` vem preenchida (empates repetem o número).
- "HM" (Honra ao Mérito) foi mapeado para `Menção Honrosa` para unificar com a OBMEP; **2025 não traz linhas de HM** no quadro publicado.
- Inclui modalidade Universitária (2016) e Competição Feminina (CF-OBI): fora do perfil EF/EM ou de outra competição; filtrar na T2.x.
- `nivel` é texto (`Júnior`, `1`, `2`, `Sênior`); mapeamento nível → ano escolar ainda a fazer (T2.2 do plano de entregas).

## ONHB (T1.10) — NÃO coletada
Fonte: `https://www.olimpiadadehistoria.com.br/` (Unicamp). `robots.txt` permite tudo, mas:
- A unidade é a **equipe** (3 estudantes + professor), não o aluno individual.
- O site público publica **notícias com contagens agregadas** (ex.: 17 ouros, 27 pratas, 37 bronzes na final; medalhas por estado, em texto e mapas-imagem). Não há tabela/PDF com nome de equipe, escola e município por medalha.
- A relação nominal das equipes medalhistas fica na área logada ("sala da equipe"; exige login) e há um link para uma pasta do Google Drive ("Edições anteriores", na página *Downloads*), que exige acesso/interação. Não foram acessados.
- **Existe, mas não coletado:** totais de medalhas por edição/estado (texto de notícias; não estruturado).
- **Falta:** lista nominal por equipe (nome da equipe/escola/município/UF/medalha) por edição. **Como obter:** pedir à organização (Comissão Organizadora/Unicamp) ou baixar manualmente a pasta "Edições anteriores" e salvar em `data/raw/olimpiadas/onhb/`; o parser seria escrito sobre o formato real.
- Consequência: RF 2.5 cobre OBMEP e OBI, mas **não** ONHB.
