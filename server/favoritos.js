// Favoritos pessoais, associados ao e-mail logado (padrão do specs.md 4.5, ainda [ABERTO] se compartilhados).
// Persistência simples em arquivo JSON, gravado de forma atômica; o projeto tem até 10 usuários simultâneos.
const fs = require("node:fs");
const path = require("node:path");

const LIMITE_POR_USUARIO = 200;

function criarFavoritos(arquivo) {
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
    listar(email) {
      return ler()[chave(email)] || [];
    },
    // Devolve false quando o usuário já está no limite.
    adicionar(email, item) {
      const dados = ler();
      const lista = dados[chave(email)] || [];
      if (lista.some((f) => f.tipo === item.tipo && f.id === item.id)) return true;
      if (lista.length >= LIMITE_POR_USUARIO) return false;
      dados[chave(email)] = [...lista, item];
      gravar(dados);
      return true;
    },
    remover(email, tipo, id) {
      const dados = ler();
      const lista = dados[chave(email)] || [];
      dados[chave(email)] = lista.filter((f) => !(f.tipo === tipo && f.id === id));
      gravar(dados);
    },
  };
}

module.exports = { criarFavoritos };
