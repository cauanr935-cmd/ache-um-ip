// Login com Google verificado no servidor. O front só entrega o ID token; quem valida
// assinatura, audiência, validade e e-mail é o back-end.
const { OAuth2Client } = require("google-auth-library");

function emailAutorizado(email, config) {
  const e = String(email || "").toLowerCase();
  if (config.emailsPermitidos.includes(e)) return true;
  const dominio = e.split("@")[1];
  if (!dominio) return false;
  return config.dominiosPermitidos.some((d) => dominio === d || dominio.endsWith("." + d));
}

function criarVerificadorGoogle(config) {
  const cliente = new OAuth2Client(config.googleClientId);
  return async function verificarToken(credential) {
    const ticket = await cliente.verifyIdToken({ idToken: credential, audience: config.googleClientId });
    return ticket.getPayload();
  };
}

// Converte o payload do Google na sessão guardada no cookie (só o necessário).
function sessaoDoPayload(p, config) {
  return {
    id: p.sub,
    email: p.email,
    nome: p.given_name || (p.name || "").split(" ")[0] || "",
    sobrenome: p.family_name || (p.name || "").split(" ").slice(1).join(" "),
    nomeCompleto: p.name || "",
    fotoPerfil: p.picture || null,
    inicio: Date.now(),
    expira: Date.now() + config.horasSessao * 3600 * 1000,
  };
}

function usuarioPublico(sessao) {
  const { id, email, nome, sobrenome, nomeCompleto, fotoPerfil, inicio, expira } = sessao;
  return { id, email, nome, sobrenome, nomeCompleto, fotoPerfil, inicio, expira };
}

module.exports = { emailAutorizado, criarVerificadorGoogle, sessaoDoPayload, usuarioPublico };
