from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="C.I.A. Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# MODELOS
# =========================

class CriarInvestigador(BaseModel):
    codinome: str
    chave_acesso: str
    nome_exibicao: str | None = None


class LoginInvestigador(BaseModel):
    codinome: str
    chave_acesso: str


class AtualizarFoto(BaseModel):
    codinome: str
    foto_url: str


class AceiteCaso(BaseModel):
    codinome: str
    caso_id: str


class ProgressoCaso(BaseModel):
    codinome: str
    caso_id: str
    voto: str | None = None
    teorias: list[str] = []
    pistas_liberadas: int = 0
    revelacao_liberada: bool = False
    missoes_concluidas: list[str] = []

class NovoAcesso(BaseModel):
    codigo_acesso: str
    nome_cliente: str
    caso_id: str = "arquivo001"
    ativo: bool = True

class AdicionarXP(BaseModel):
    codinome: str
    xp: int


# =========================
# FUNÇÕES AUXILIARES
# =========================

def conectar():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não foi configurada.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def calcular_patente(xp: int):
    if xp >= 2000:
        return "Chefe de Investigação"
    if xp >= 1200:
        return "Analista de Casos"
    if xp >= 700:
        return "Investigador Nível 3"
    if xp >= 350:
        return "Investigador Nível 2"
    if xp >= 100:
        return "Investigador Nível 1"
    return "Recruta"


def calcular_semana(data_inicio):
    if not data_inicio:
        return 1

    agora = datetime.utcnow()
    dias_passados = (agora - data_inicio).days

    if dias_passados >= 22:
        return 4
    if dias_passados >= 15:
        return 3
    if dias_passados >= 8:
        return 2

    return 1


def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acessos (
            codigo_acesso TEXT PRIMARY KEY,
            nome_cliente TEXT NOT NULL,
            caso_id TEXT NOT NULL,
            ativo BOOLEAN DEFAULT TRUE,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_inicio TIMESTAMP,
            data_final TIMESTAMP
        )
    """)

    def criar_acessos_iniciais(cursor, conn):
    acessos_iniciais = [
        ("CIA001-ANA2026", "Ana", "arquivo001"),
        ("CIA002-MARIA2026", "Maria", "arquivo001"),
        ("CIA003-JULIA2026", "Julia", "arquivo001"),
        ("CIA004-CARLA2026", "Carla", "arquivo001"),
        ("CIA005-AMANDA2026", "Amanda", "arquivo001"),
        ("CIA006-LUCAS2026", "Lucas", "arquivo001"),
        ("CIA007-PAULA2026", "Paula", "arquivo001"),
        ("CIA008-RAFA2026", "Rafa", "arquivo001"),
        ("CIA009-BIA2026", "Bia", "arquivo001"),
        ("CIA010-TESTE2026", "Teste", "arquivo001"),
    ]

    for codigo, nome, caso_id in acessos_iniciais:
        cursor.execute("""
            INSERT INTO acessos (
                codigo_acesso,
                nome_cliente,
                caso_id,
                ativo
            )
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (codigo_acesso)
            DO NOTHING
        """, (codigo, nome, caso_id))

    conn.commit()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progresso (
            codigo_acesso TEXT NOT NULL,
            nome TEXT NOT NULL,
            caso_id TEXT NOT NULL,
            voto TEXT,
            teorias TEXT,
            pistas_liberadas INTEGER DEFAULT 0,
            revelacao_liberada BOOLEAN DEFAULT FALSE,
            data_inicio TIMESTAMP,
            data_final TIMESTAMP,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (codigo_acesso, caso_id)
        )
    """)

    conn.commit()

    criar_acessos_iniciais(cursor, conn)

    cursor.close()
    conn.close()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progresso_casos (
            id SERIAL PRIMARY KEY,
            codinome TEXT NOT NULL,
            caso_id TEXT NOT NULL,
            voto TEXT,
            teorias TEXT,
            pistas_liberadas INTEGER DEFAULT 0,
            revelacao_liberada BOOLEAN DEFAULT FALSE,
            missoes_concluidas TEXT,
            data_inicio TIMESTAMP,
            data_final TIMESTAMP,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (codinome, caso_id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


@app.on_event("startup")
def iniciar():
    criar_tabelas()


# =========================
# ROTAS PRINCIPAIS
# =========================

@app.get("/")
def home():
    return {
        "status": "Backend da C.I.A. funcionando no Render",
        "sistema": "Central de Investigação Autônoma"
    }


# =========================
# INVESTIGADORES
# =========================

@app.post("/criar-investigador")
def criar_investigador(dados: CriarInvestigador):
    conn = conectar()
    cursor = conn.cursor()

    codinome = dados.codinome.strip()
    chave = dados.chave_acesso.strip()
    nome = dados.nome_exibicao.strip() if dados.nome_exibicao else codinome

    cursor.execute("""
        SELECT codinome
        FROM investigadores
        WHERE codinome = %s
    """, (codinome,))

    existente = cursor.fetchone()

    if existente:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Este codinome já existe.")

    cursor.execute("""
        INSERT INTO investigadores (
            codinome,
            chave_acesso,
            nome_exibicao,
            patente,
            xp,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        codinome,
        chave,
        nome,
        "Recruta",
        0,
        "ativo"
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "mensagem": "Credencial de investigador criada com sucesso.",
        "codinome": codinome,
        "chave_acesso": chave,
        "patente": "Recruta",
        "xp": 0,
        "status": "ativo"
    }


@app.post("/login")
def login(dados: LoginInvestigador):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM investigadores
        WHERE codinome = %s AND chave_acesso = %s
    """, (
        dados.codinome.strip(),
        dados.chave_acesso.strip()
    ))

    investigador = cursor.fetchone()

    cursor.close()
    conn.close()

    if not investigador:
        raise HTTPException(status_code=401, detail="Codinome ou chave de acesso inválidos.")

    if investigador["status"] != "ativo":
        raise HTTPException(status_code=403, detail="Credencial inativa.")

    return {
        "autenticado": True,
        "mensagem": "Credencial localizada.",
        "investigador": {
            "codinome": investigador["codinome"],
            "nome_exibicao": investigador["nome_exibicao"],
            "foto_url": investigador["foto_url"],
            "patente": investigador["patente"],
            "xp": investigador["xp"],
            "status": investigador["status"]
        }
    }


@app.get("/investigador/{codinome}")
def buscar_investigador(codinome: str):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT codinome, nome_exibicao, foto_url, patente, xp, status, criado_em
        FROM investigadores
        WHERE codinome = %s
    """, (codinome,))

    investigador = cursor.fetchone()

    cursor.close()
    conn.close()

    if not investigador:
        raise HTTPException(status_code=404, detail="Investigador não encontrado.")

    return investigador


@app.post("/atualizar-foto")
def atualizar_foto(dados: AtualizarFoto):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE investigadores
        SET foto_url = %s,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE codinome = %s
    """, (
        dados.foto_url,
        dados.codinome
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "mensagem": "Foto da credencial atualizada com sucesso."
    }


@app.post("/adicionar-xp")
def adicionar_xp(dados: AdicionarXP):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT xp
        FROM investigadores
        WHERE codinome = %s
    """, (dados.codinome,))

    investigador = cursor.fetchone()

    if not investigador:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Investigador não encontrado.")

    novo_xp = investigador["xp"] + dados.xp
    nova_patente = calcular_patente(novo_xp)

    cursor.execute("""
        UPDATE investigadores
        SET xp = %s,
            patente = %s,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE codinome = %s
    """, (
        novo_xp,
        nova_patente,
        dados.codinome
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "mensagem": "XP atualizado com sucesso.",
        "xp": novo_xp,
        "patente": nova_patente
    }


# =========================
# CASOS / PROGRESSO
# =========================

@app.post("/aceitar-caso")
def aceitar_caso(dados: AceiteCaso):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM acessos
        WHERE codigo_acesso = %s
        AND caso_id = %s
        AND ativo = TRUE
    """, (dados.codigo_acesso, dados.caso_id))

    acesso = cursor.fetchone()

    if not acesso:
        cursor.close()
        conn.close()
        return {
            "autorizado": False,
            "mensagem": "Código inválido, inativo ou sem acesso a este caso."
        }

    if acesso["data_inicio"]:
        cursor.close()
        conn.close()
        return {
            "autorizado": True,
            "mensagem": "Caso já havia sido aceito",
            "data_inicio": acesso["data_inicio"],
            "data_final": acesso["data_final"]
        }

    data_inicio = datetime.utcnow()
    data_final = data_inicio + timedelta(days=28)

    cursor.execute("""
        UPDATE acessos
        SET data_inicio = %s,
            data_final = %s
        WHERE codigo_acesso = %s
        AND caso_id = %s
    """, (
        data_inicio,
        data_final,
        dados.codigo_acesso,
        dados.caso_id
    ))

    cursor.execute("""
        INSERT INTO progresso (
            codigo_acesso,
            nome,
            caso_id,
            teorias,
            pistas_liberadas,
            revelacao_liberada,
            data_inicio,
            data_final
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (codigo_acesso, caso_id)
        DO NOTHING
    """, (
        dados.codigo_acesso,
        dados.nome,
        dados.caso_id,
        "",
        0,
        False,
        data_inicio,
        data_final
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "autorizado": True,
        "mensagem": "Caso aceito com sucesso",
        "data_inicio": data_inicio,
        "data_final": data_final
    }


@app.post("/progresso")
def salvar_progresso(dados: ProgressoCaso):
    conn = conectar()
    cursor = conn.cursor()

    teorias_texto = "||".join(dados.teorias)
    missoes_texto = "||".join(dados.missoes_concluidas)

    cursor.execute("""
        SELECT data_inicio, data_final
        FROM progresso_casos
        WHERE codinome = %s AND caso_id = %s
    """, (
        dados.codinome,
        dados.caso_id
    ))

    existente = cursor.fetchone()

    if existente:
        data_inicio = existente["data_inicio"]
        data_final = existente["data_final"]
    else:
        data_inicio = datetime.utcnow()
        data_final = data_inicio + timedelta(days=28)

    cursor.execute("""
        INSERT INTO progresso_casos (
            codinome,
            caso_id,
            voto,
            teorias,
            pistas_liberadas,
            revelacao_liberada,
            missoes_concluidas,
            data_inicio,
            data_final,
            atualizado_em
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (codinome, caso_id)
        DO UPDATE SET
            voto = EXCLUDED.voto,
            teorias = EXCLUDED.teorias,
            pistas_liberadas = EXCLUDED.pistas_liberadas,
            revelacao_liberada = EXCLUDED.revelacao_liberada,
            missoes_concluidas = EXCLUDED.missoes_concluidas,
            atualizado_em = CURRENT_TIMESTAMP
    """, (
        dados.codinome,
        dados.caso_id,
        dados.voto,
        teorias_texto,
        dados.pistas_liberadas,
        dados.revelacao_liberada,
        missoes_texto,
        data_inicio,
        data_final
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "mensagem": "Progresso salvo com sucesso."
    }


@app.get("/progresso/{codinome}/{caso_id}")
def buscar_progresso(codinome: str, caso_id: str):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM progresso_casos
        WHERE codinome = %s AND caso_id = %s
    """, (
        codinome,
        caso_id
    ))

    progresso = cursor.fetchone()

    cursor.close()
    conn.close()

    if not progresso:
        return {
            "encontrado": False,
            "mensagem": "Nenhum progresso encontrado."
        }

    teorias = progresso["teorias"].split("||") if progresso["teorias"] else []
    missoes = progresso["missoes_concluidas"].split("||") if progresso["missoes_concluidas"] else []

    agora = datetime.utcnow()
    data_inicio = progresso["data_inicio"]
    data_final = progresso["data_final"]

    dias_passados = (agora - data_inicio).days if data_inicio else 0
    dias_restantes = max(28 - dias_passados, 0)
    semana_atual = calcular_semana(data_inicio)
    revelacao_disponivel = bool(data_final and agora >= data_final)

    return {
        "encontrado": True,
        "codinome": progresso["codinome"],
        "caso_id": progresso["caso_id"],
        "voto": progresso["voto"],
        "teorias": teorias,
        "pistas_liberadas": progresso["pistas_liberadas"],
        "revelacao_liberada": progresso["revelacao_liberada"],
        "missoes_concluidas": missoes,
        "data_inicio": data_inicio,
        "data_final": data_final,
        "dias_passados": dias_passados,
        "dias_restantes": dias_restantes,
        "semana_atual": semana_atual,
        "revelacao_disponivel": revelacao_disponivel
    }
@app.get("/validar-acesso/{codigo_acesso}/{caso_id}")
def validar_acesso(codigo_acesso: str, caso_id: str):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM acessos
        WHERE codigo_acesso = %s
        AND caso_id = %s
        AND ativo = TRUE
    """, (codigo_acesso, caso_id))

    acesso = cursor.fetchone()

    cursor.close()
    conn.close()

    if not acesso:
        return {
            "valido": False,
            "mensagem": "Código inválido, inativo ou sem acesso a este caso."
        }

    return {
        "valido": True,
        "mensagem": "Acesso autorizado.",
        "codigo_acesso": acesso["codigo_acesso"],
        "nome_cliente": acesso["nome_cliente"],
        "caso_id": acesso["caso_id"],
        "data_inicio": acesso["data_inicio"],
        "data_final": acesso["data_final"]
    }


@app.get("/acessos")
def listar_acessos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT codigo_acesso, nome_cliente, caso_id, ativo, data_criacao, data_inicio, data_final
        FROM acessos
        ORDER BY codigo_acesso ASC
    """)

    acessos = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "total": len(acessos),
        "acessos": acessos
    }


@app.post("/criar-acesso")
def criar_acesso(dados: NovoAcesso):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO acessos (
            codigo_acesso,
            nome_cliente,
            caso_id,
            ativo
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (codigo_acesso)
        DO UPDATE SET
            nome_cliente = EXCLUDED.nome_cliente,
            caso_id = EXCLUDED.caso_id,
            ativo = EXCLUDED.ativo
    """, (
        dados.codigo_acesso,
        dados.nome_cliente,
        dados.caso_id,
        dados.ativo
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "mensagem": "Acesso criado ou atualizado com sucesso.",
        "codigo_acesso": dados.codigo_acesso,
        "nome_cliente": dados.nome_cliente,
        "caso_id": dados.caso_id,
        "ativo": dados.ativo
    }
