class Usuario {
    static STORAGE_KEY = "usuario_logado";

    constructor({
        id,
        nome,
        sobrenome,
        nomeCompleto,
        email,
        fotoPerfil,
        emailVerificado,
        comecoSessao,
        vencimentoSessao,
    }) {
        this.id = id;
        this.nome = nome;
        this.sobrenome = sobrenome;
        this.nomeCompleto = nomeCompleto;
        this.email = email;
        this.fotoPerfil = fotoPerfil;
        this.emailVerificado = emailVerificado;
        this.comecoSessao = comecoSessao;
        this.vencimentoSessao = vencimentoSessao;
    }


    static fromJWTPayload(payload) {
        const nomeCompleto = payload.name || "";
        const nome = payload.given_name || nomeCompleto.split(" ")[0] || "";
        const sobrenome =
            payload.family_name || nomeCompleto.split(" ").slice(1).join(" ") || "";

        return new Usuario({
            id: payload.sub,
            nome,
            sobrenome,
            nomeCompleto,
            email: payload.email,
            fotoPerfil: payload.picture,
            emailVerificado: payload.email_verified === true,
            comecoSessao: new Date(payload.iat * 1000),
            vencimentoSessao: new Date(payload.exp * 1000),
        });
    }

    isTokenValid() {
        return this.vencimentoSessao instanceof Date && this.vencimentoSessao.getTime() > Date.now();
    }


    toJSON() {
        return {
            id: this.id,
            nome: this.nome,
            sobrenome: this.sobrenome,
            nomeCompleto: this.nomeCompleto,
            email: this.email,
            fotoPerfil: this.fotoPerfil,
            emailVerificado: this.emailVerificado,
            comecoSessao: this.comecoSessao?.toISOString() ?? null,
            vencimentoSessao: this.vencimentoSessao?.toISOString() ?? null,
        };
    }

    static fromJSON(obj) {
        return new Usuario({
            ...obj,
            comecoSessao: obj.comecoSessao ? new Date(obj.comecoSessao) : null,
            vencimentoSessao: obj.vencimentoSessao ? new Date(obj.vencimentoSessao) : null,
        });
    }


    salvar() {
        try {
            localStorage.setItem(Usuario.STORAGE_KEY, JSON.stringify(this.toJSON()));
            return true;
        } catch (err) {
            console.error("Falha ao salvar usuário no localStorage:", err);
            return false;
        }
    }

    static carregar() {
        try {
            const raw = localStorage.getItem(Usuario.STORAGE_KEY);
            if (!raw) return null;

            const user = Usuario.fromJSON(JSON.parse(raw));

            if (!user.isTokenValid()) {
                Usuario.remover();
                return null;
            }
            return user;
        } catch (err) {
            console.error("Falha ao carregar usuário do localStorage:", err);
            Usuario.remover();
            return null;
        }
    }

    static remover() {
        localStorage.removeItem(Usuario.STORAGE_KEY);
    }
}