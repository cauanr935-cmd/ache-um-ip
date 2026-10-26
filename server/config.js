// Configuração lida do ambiente (.env, que não vai para o git). Nenhum segredo vai para o front.
const path = require("node:path");

try {
  process.loadEnvFile(path.resolve(__dirname, "../.env"));
} catch (err) {
  if (err.code !== "ENOENT") throw err; // sem .env, vale o ambiente do processo
}

function lista(valor, padrao) {
  return (valor ?? padrao).split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
}

const config = {
  porta: Number(process.env.PORT) || 3000,
  producao: process.env.NODE_ENV === "production",
  // ID de cliente OAuth do Google. É público (o botão de login precisa dele).
  googleClientId: process.env.GOOGLE_CLIENT_ID || "",
  // Assina o cookie de sessão. Em produção é obrigatório.
  segredoSessao: process.env.SESSION_SECRET || "",
  horasSessao: Number(process.env.SESSION_HOURS) || 8,
  // Domínios institucionais aceitos. "institutoponte.org.br" também aceita subdomínios
  // como aluno.institutoponte.org.br.
  dominiosPermitidos: lista(process.env.ALLOWED_EMAIL_DOMAINS, "institutoponte.org.br"),
  // Lista opcional de e-mails autorizados além do domínio (specs.md 7).
  emailsPermitidos: lista(process.env.ALLOWED_EMAILS, ""),
  raizFront: path.resolve(__dirname, "../screens"),
  raizMalha: path.resolve(__dirname, "../data/malha"),
  // JSON pré-computado por src/api_precompute.py (fora do git).
  raizApi: path.resolve(__dirname, "../data/api"),
  // Dados privados (fora do git): medalhistas com nome, favoritos e log de auditoria.
  raizPrivado: path.resolve(__dirname, "../data/privado"),
  // Com false (padrão) a lista de medalhistas mostra só o pseudônimo; true libera o nome completo (specs.md 7).
  // Vercel: disco somente leitura (sem auditoria nem dados privados).
  somenteLeitura: Boolean(process.env.VERCEL),
  redis: {
    url: process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL,
    token: process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN,
  },
  alunoIdentificado: process.env.ALUNO_IDENTIFICADO === "true",
};

if (config.producao && (!config.segredoSessao || !config.googleClientId)) {
  throw new Error("Em produção, defina SESSION_SECRET e GOOGLE_CLIENT_ID no ambiente.");
}
if (!config.segredoSessao) {
  // Em desenvolvimento, um segredo aleatório por execução (as sessões caem ao reiniciar).
  config.segredoSessao = require("node:crypto").randomBytes(32).toString("hex");
}

module.exports = config;
