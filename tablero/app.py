import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row

SQL_DIR = Path(os.environ.get("SQL_DIR", "/app/sql"))
STATIC_DIR = Path(__file__).parent / "static"

CONSULTAS = {
    "resumen": "08_resumen.sql",
    "oportunidades-por-mes": "01_oportunidades_por_mes.sql",
    "conversion-por-origen": "02_conversion_por_origen.sql",
    "ventas-por-mes": "03_ventas_por_mes.sql",
    "stock-insuficiente": "04_stock_insuficiente.sql",
    "proyectos": "05_proyectos_tareas.sql",
    "tareas-por-estado": "06_tareas_por_estado.sql",
    "tiempos-ciclo": "07_tiempos_ciclo.sql",
}

app = FastAPI(title="Tablero Del correo al proyecto", docs_url=None, redoc_url=None)


def conninfo() -> str:
    return psycopg.conninfo.make_conninfo(
        host=os.environ.get("PGHOST", "db"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ.get("PGUSER", "lector"),
        password=os.environ["PGPASSWORD"],
        connect_timeout=5,
        application_name="tablero",
    )


def serializar(valor):
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return valor


def ejecutar(archivo: str) -> list[dict]:
    consulta = (SQL_DIR / archivo).read_text(encoding="utf-8")
    with psycopg.connect(conninfo(), row_factory=dict_row) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute(consulta)
            return [{k: serializar(v) for k, v in fila.items()} for fila in cur.fetchall()]


@app.get("/api/salud")
def salud():
    try:
        with psycopg.connect(conninfo()) as conn:
            conn.execute("SELECT 1")
    except psycopg.Error as exc:
        return JSONResponse({"estado": "error", "detalle": str(exc).strip()}, status_code=503)
    return {"estado": "ok"}


@app.get("/api/tablero")
def tablero():
    try:
        datos = {clave: ejecutar(archivo) for clave, archivo in CONSULTAS.items()}
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail=str(exc).strip())
    datos["actualizado"] = datetime.now().astimezone().isoformat(timespec="seconds")
    datos["metabase_url"] = os.environ.get("METABASE_URL", "http://localhost:3000")
    return datos


@app.get("/api/{indicador}")
def indicador(indicador: str):
    archivo = CONSULTAS.get(indicador)
    if archivo is None:
        raise HTTPException(status_code=404, detail="Indicador no encontrado")
    try:
        return ejecutar(archivo)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail=str(exc).strip())


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
