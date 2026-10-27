// Cliente mínimo do Redis via API REST (Upstash / Vercel KV), para ambientes sem disco gravável.
function criarRedis({ url, token }) {
  async function chamar(corpo, caminho = "") {
    const r = await fetch(url + caminho, { method: "POST", headers: { Authorization: "Bearer " + token }, body: JSON.stringify(corpo) });
    if (!r.ok) throw new Error("Redis HTTP " + r.status);
    return r.json();
  }
  return {
    async cmd(...args) {
      return (await chamar(args)).result;
    },
    // Vários comandos em uma ida só; devolve os resultados na mesma ordem.
    async pipeline(comandos) {
      const resp = await chamar(comandos, "/pipeline");
      return resp.map((x) => {
        if (x.error) throw new Error("Redis: " + x.error);
        return x.result;
      });
    },
  };
}

const redisConfigurado = (redis) => Boolean(redis && redis.url && redis.token);

module.exports = { criarRedis, redisConfigurado };
