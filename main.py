from fastapi import FastAPI
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
    allow_origins=["*"],  # depois podemos limitar para seu domínio do Netlify
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Progresso(BaseModel):
    codigo_acesso: str
    nome: str
    caso_id: str
    voto: str | None = None
    teorias: list[str] = []
    pistas_liberadas: int = 0
    revelacao_liberada: bool = False


class AceiteCaso(BaseModel):
    codigo_acesso: str
    nome: str
    caso_id: str


def conectar():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não foi configurada.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

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
    cursor.close()
    conn.close()


@app.on_event("startup")
def iniciar():
    criar_tabelas()


@app.get("/")
def home():
    return {"status": "Backend da C.I.A. funcionando no Render"}


@app.post("/aceitar-caso")
def aceitar_caso(dados: AceiteCaso):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM progresso
        WHERE codigo_acesso = %s AND caso_id = %s
    """, (dados.codigo_acesso, dados.caso_id))

    existente = cursor.fetchone()

    if existente:
        cursor.close()
        conn.close()
        return {
            "mensagem": "Caso já havia sido aceito",
            "data_inicio": existente["data_inicio"],
            "data_final": existente["data_final"]
        }

    data_inicio = datetime.utcnow()
    data_final = data_inicio + timedelta(days=28)

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
        "mensagem": "Caso aceito com sucesso",
        "data_inicio": data_inicio,
        "data_final": data_final
    }


@app.post("/progresso")
def salvar_progresso(dados: Progresso):
    conn = conectar()
    cursor = conn.cursor()

    teorias_texto = "||".join(dados.teorias)

    cursor.execute("""
        SELECT data_inicio, data_final
        FROM progresso
        WHERE codigo_acesso = %s AND caso_id = %s
    """, (dados.codigo_acesso, dados.caso_id))

    existente = cursor.fetchone()

    if existente:
        data_inicio = existente["data_inicio"]
        data_final = existente["data_final"]
    else:
        data_inicio = datetime.utcnow()
        data_final = data_inicio + timedelta(days=28)

    cursor.execute("""
        INSERT INTO progresso (
            codigo_acesso,
            nome,
            caso_id,
            voto,
            teorias,
            pistas_liberadas,
            revelacao_liberada,
            data_inicio,
            data_final,
            atualizado_em
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (codigo_acesso, caso_id)
        DO UPDATE SET
            nome = EXCLUDED.nome,
            voto = EXCLUDED.voto,
            teorias = EXCLUDED.teorias,
            pistas_liberadas = EXCLUDED.pistas_liberadas,
            revelacao_liberada = EXCLUDED.revelacao_liberada,
            atualizado_em = CURRENT_TIMESTAMP
    """, (
        dados.codigo_acesso,
        dados.nome,
        dados.caso_id,
        dados.voto,
        teorias_texto,
        dados.pistas_liberadas,
        dados.revelacao_liberada,
        data_inicio,
        data_final
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return {"mensagem": "Progresso salvo com sucesso"}


@app.get("/progresso/{codigo_acesso}/{caso_id}")
def buscar_progresso(codigo_acesso: str, caso_id: str):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM progresso
        WHERE codigo_acesso = %s AND caso_id = %s
    """, (codigo_acesso, caso_id))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not row:
        return {
            "encontrado": False,
            "mensagem": "Nenhum progresso encontrado"
        }

    teorias = row["teorias"].split("||") if row["teorias"] else []

    agora = datetime.utcnow()
    data_inicio = row["data_inicio"]
    data_final = row["data_final"]

    if data_inicio:
        dias_passados = (agora - data_inicio).days
    else:
        dias_passados = 0

    semana_atual = 1

    if dias_passados >= 22:
        semana_atual = 4
    elif dias_passados >= 15:
        semana_atual = 3
    elif dias_passados >= 8:
        semana_atual = 2

    revelacao_disponivel = False

    if data_final and agora >= data_final:
        revelacao_disponivel = True

    return {
        "encontrado": True,
        "codigo_acesso": row["codigo_acesso"],
        "nome": row["nome"],
        "caso_id": row["caso_id"],
        "voto": row["voto"],
        "teorias": teorias,
        "pistas_liberadas": row["pistas_liberadas"],
        "revelacao_liberada": row["revelacao_liberada"],
        "data_inicio": row["data_inicio"],
        "data_final": row["data_final"],
        "dias_passados": dias_passados,
        "semana_atual": semana_atual,
        "revelacao_disponivel": revelacao_disponivel
    }
