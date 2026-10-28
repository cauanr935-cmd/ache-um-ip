// Elegibilidade para o processo seletivo do Instituto Ponte (config/elegibilidade.yaml).
// O IP só aceita aluno do 2º ano do ensino médio em diante, mas ainda não no 3º. O ano da medalha não diz a série,
// então vale o critério otimista: quem ganhou no ensino médio no ano X só é elegível em X ou X + 1.
// Medalhista do ensino fundamental não entra nessa regra.
const ANOS_DE_ELEGIBILIDADE = 1;

function elegivel(medalhista, anoAtual = new Date().getFullYear()) {
  if (!medalhista.ensino_medio) return true;
  return medalhista.ano >= anoAtual - ANOS_DE_ELEGIBILIDADE;
}

module.exports = { elegivel, ANOS_DE_ELEGIBILIDADE };
