// Favoritos pessoais, associados ao e-mail logado (padrão do specs.md 4.5, ainda [ABERTO] se compartilhados).
// Persistência simples em arquivo JSON, gravado de forma atômica; o projeto tem até 10 usuários simultâneos.
const fs = require("node:fs");
const path = require("node:path");

const LIMITE_POR_USUARIO = 200;

// Backend alternativo para ambientes sem disco gravável (Vercel): Redis via API REST (Upstash / Vercel KV).
function criarFavoritosRedis({ url, token }) {
  async function cmd(...args) {
    const r = await fetch(url, { method: "POST", headers: { Authorization: "Bearer " + token }, body: JSON.stringify(args) });
    if (!r.ok) throw new Error("Redis HTTP " + r.status);
    return (await r.json()).result;
  }
  const chave = (email) => "favoritos:" + String(email).toLowerCase();
  const ler = async (email) => JSON.parse((await cmd("GET", chave(email))) || "[]");
  return {
    listar: ler,
    async adicionar(email, item) {
      const lista = await ler(email);
      if (lista.some((f) => f.tipo === item.tipo && f.id === item.id)) return true;
      if (lista.length >= LIMITE_POR_USUARIO) return false;
      await cmd("SET", chave(email), JSON.stringify([...lista, item]));
      return true;
    },
    async remover(email, tipo, id) {
      const lista = await ler(email);
      await cmd("SET", chave(email), JSON.stringify(lista.filter((f) => !(f.tipo === tipo && f.id === id))));
    },
  };
}

function criarFavoritos(arquivo, redis) {
  if (redis && redis.url && redis.token) return criarFavoritosRedis(redis);

  function ler() {
    try {
      return JSON.parse(fs.readFileSync(arquivo, "utf8"));
    } catch (err) {
      if (err.code === "ENOENT") return {};
      throw err;
    }
  }

  function gravar(dados) {
    fs.mkdirSync(path.dirname(arquivo), { recursive: true });
    const temporario = arquivo + ".tmp";
    fs.writeFileSync(temporario, JSON.stringify(dados));
    fs.renameSync(temporario, arquivo);
  }

  const chave = (email) => String(email).toLowerCase();

  return {
    async listar(email) {
      return ler()[chave(email)] || [];
    },
    // Devolve false quando o usuário já está no limite.
    async adicionar(email, item) {
      const dados = ler();
      const lista = dados[chave(email)] || [];
      if (lista.some((f) => f.tipo === item.tipo && f.id === item.id)) return true;
      if (lista.length >= LIMITE_POR_USUARIO) return false;
      dados[chave(email)] = [...lista, item];
      gravar(dados);
      return true;
    },
    async remover(email, tipo, id) {
      const dados = ler();
      const lista = dados[chave(email)] || [];
      dados[chave(email)] = lista.filter((f) => !(f.tipo === tipo && f.id === id));
      gravar(dados);
    },
  };
}

module.exports = { criarFavoritos };
