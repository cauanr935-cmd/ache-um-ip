// Busca única com autocomplete por UF, município e escola (specs.md 4.5). O índice vem de data/api/busca.json.
const { NOMES_UF } = require("./ufs");

function normalizar(texto) {
  return String(texto).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

function criarIndice({ municipios, escolas }) {
  return {
    municipios: new Map(municipios.map(([codigo, nome, uf]) => [codigo, { codigo, nome, uf, norm: normalizar(nome) }])),
    escolas: new Map(escolas.map(([inep, nome, municipio, uf]) => [inep, { inep, nome, municipio, uf, norm: normalizar(nome) }])),
    ufs: Object.entries(NOMES_UF).map(([sigla, nome]) => ({ sigla, nome, norm: normalizar(nome) })),
  };
}

// Prioriza nome que começa com o termo, depois palavra que começa, depois qualquer trecho.
function pontuar(norm, termo) {
  if (norm.startsWith(termo)) return 0;
  if (norm.includes(" " + termo)) return 1;
  return norm.includes(termo) ? 2 : -1;
}

function buscar(indice, consulta, limite = 5) {
  const q = normalizar(consulta);
  if (q.length < 2) return [];
  const achados = [];

  for (const u of indice.ufs) {
    if (u.sigla.toLowerCase() === q || pontuar(u.norm, q) >= 0) achados.push({ tipo: "uf", id: u.sigla, nome: u.nome, uf: u.sigla });
  }

  const ordenados = (itens) => itens.sort((a, b) => a.p - b.p || a.item.nome.localeCompare(b.item.nome, "pt-BR")).slice(0, limite).map((x) => x.item);

  const municipios = [];
  for (const m of indice.municipios.values()) {
    const p = /^\d+$/.test(q) ? (m.codigo.startsWith(q) ? 0 : -1) : pontuar(m.norm, q);
    if (p >= 0) municipios.push({ p, item: m });
  }
  for (const m of ordenados(municipios)) achados.push({ tipo: "municipio", id: m.codigo, nome: m.nome, uf: m.uf });

  const palavras = q.split(/\s+/);
  const escolas = [];
  for (const e of indice.escolas.values()) {
    let p;
    if (/^\d+$/.test(q)) p = e.inep.startsWith(q) ? 0 : -1;
    else p = palavras.every((w) => e.norm.includes(w)) ? pontuar(e.norm, palavras[0]) : -1;
    if (p >= 0) escolas.push({ p: Math.max(p, 0), item: e });
  }
  for (const e of ordenados(escolas)) {
    achados.push({ tipo: "escola", id: e.inep, nome: e.nome, uf: e.uf, municipio: indice.municipios.get(e.municipio)?.nome || null, codigo_municipio: e.municipio });
  }
  return achados;
}

module.exports = { criarIndice, buscar, normalizar };
