#!/usr/bin/env python3
"""Configura Metabase y publica el tablero "Del correo al proyecto"."""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SQL = RAIZ / "sql"

MB_URL = os.environ.get("MB_URL", "http://localhost:3000").rstrip("/")
MB_ADMIN_EMAIL = os.environ["MB_ADMIN_EMAIL"]
MB_ADMIN_PASSWORD = os.environ["MB_ADMIN_PASSWORD"]
MB_ADMIN_NOMBRE = os.environ.get("MB_ADMIN_NOMBRE", "Administrador")
MB_EMPRESA = os.environ.get("MB_EMPRESA", "Empresa")
ODOO_DB = os.environ["ODOO_DB"]
LECTOR_HOST = os.environ.get("LECTOR_HOST", "db")
LECTOR_PORT = int(os.environ.get("LECTOR_PORT", "5432"))
LECTOR_USER = os.environ.get("LECTOR_USER", "lector")
LECTOR_PASSWORD = os.environ["LECTOR_PASSWORD"]

TABLERO = "Del correo al proyecto"
COLECCION = "Del correo al proyecto"
BASE = "Odoo"

PRIMARIO = "#3B6EA5"
SECUNDARIO = "#9DB3CF"
NEUTRO = "#8A94A6"
COLORES_ESTADO = {"En curso": PRIMARIO, "En espera": "#B7791F", "Vencida": "#C53030",
                  "Hecha": "#2F855A", "Cancelada": "#9AA3AF"}

# Encabezados de sección del tablero: (fila, texto).
SECCIONES = [
    (0, "Resumen"),
    (4, "Comercial"),
    (17, "Inventario"),
    (23, "Proyectos"),
]

TARJETAS = [
    {"archivo": "08_resumen.sql", "nombre": "Resumen", "display": "table",
     "pos": (0, 1, 24, 3), "viz": {}},
    {"archivo": "01_oportunidades_por_mes.sql", "nombre": "Oportunidades por mes y origen", "display": "bar",
     "pos": (0, 5, 12, 6),
     "viz": {"graph.dimensions": ["mes", "origen"], "graph.metrics": ["oportunidades"],
             "stackable.stack_type": "stacked",
             "series_settings": {"Correo automático": {"color": PRIMARIO}, "Manual": {"color": SECUNDARIO}}}},
    {"archivo": "02_conversion_por_origen.sql", "nombre": "Conversión por origen", "display": "table",
     "pos": (12, 5, 12, 6), "viz": {}},
    {"archivo": "03_ventas_por_mes.sql", "nombre": "Ventas confirmadas por mes", "display": "combo",
     "pos": (0, 11, 12, 6),
     "viz": {"graph.dimensions": ["mes"], "graph.metrics": ["monto_confirmado", "monto_cotizado"],
             "series_settings": {"monto_confirmado": {"color": PRIMARIO, "display": "bar", "title": "Monto confirmado"},
                                 "monto_cotizado": {"color": NEUTRO, "display": "line", "title": "Monto cotizado"}}}},
    {"archivo": "07_tiempos_ciclo.sql", "nombre": "Tiempos del ciclo (minutos)", "display": "table",
     "pos": (12, 11, 12, 6), "viz": {}},
    {"archivo": "04_stock_insuficiente.sql", "nombre": "Productos con stock insuficiente", "display": "table",
     "pos": (0, 18, 24, 5), "viz": {}},
    {"archivo": "06_tareas_por_estado.sql", "nombre": "Tareas por estado", "display": "pie",
     "pos": (0, 24, 8, 7), "viz": {"pie.dimension": "estado", "pie.metric": "tareas", "pie.colors": COLORES_ESTADO}},
    {"archivo": "05_proyectos_tareas.sql", "nombre": "Avance de proyectos", "display": "table",
     "pos": (8, 24, 16, 7), "viz": {}},
]


class Metabase:
    def __init__(self, url):
        self.url = url
        self.sesion = None

    def pedir(self, metodo, ruta, datos=None):
        cuerpo = json.dumps(datos).encode() if datos is not None else None
        req = urllib.request.Request(self.url + ruta, data=cuerpo, method=metodo)
        req.add_header("Content-Type", "application/json")
        if self.sesion:
            req.add_header("X-Metabase-Session", self.sesion)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                texto = r.read().decode()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{metodo} {ruta}: {e.code} {e.read().decode()[:500]}") from None
        return json.loads(texto) if texto else None


def esperar(mb):
    for _ in range(90):
        try:
            if mb.pedir("GET", "/api/health").get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(5)
    sys.exit("Metabase no respondió en el tiempo esperado")


def iniciar_sesion(mb):
    props = mb.pedir("GET", "/api/session/properties")
    token = props.get("setup-token")
    if token and not props.get("has-user-setup"):
        r = mb.pedir("POST", "/api/setup", {
            "token": token,
            "user": {"email": MB_ADMIN_EMAIL, "password": MB_ADMIN_PASSWORD,
                     "first_name": MB_ADMIN_NOMBRE, "site_name": MB_EMPRESA},
            "prefs": {"site_name": MB_EMPRESA, "site_locale": "es", "allow_tracking": False},
        })
        mb.sesion = r["id"]
        print("Usuario administrador creado")
    else:
        mb.sesion = mb.pedir("POST", "/api/session",
                             {"username": MB_ADMIN_EMAIL, "password": MB_ADMIN_PASSWORD})["id"]


def base_odoo(mb):
    detalles = {"host": LECTOR_HOST, "port": LECTOR_PORT, "dbname": ODOO_DB,
                "user": LECTOR_USER, "password": LECTOR_PASSWORD, "ssl": False}
    for db in mb.pedir("GET", "/api/database")["data"]:
        if db["name"] == BASE:
            mb.pedir("PUT", f"/api/database/{db['id']}", {"details": detalles})
            return db["id"]
    db = mb.pedir("POST", "/api/database", {"engine": "postgres", "name": BASE, "details": detalles,
                                           "is_full_sync": True})
    print("Conexión a Odoo registrada")
    return db["id"]


def coleccion(mb):
    for c in mb.pedir("GET", "/api/collection"):
        if c.get("name") == COLECCION and not c.get("archived"):
            return c["id"]
    return mb.pedir("POST", "/api/collection", {"name": COLECCION, "color": PRIMARIO})["id"]


def tarjetas(mb, db_id, col_id):
    existentes = {c["name"]: c["id"] for c in mb.pedir("GET", "/api/card")
                  if c.get("collection_id") == col_id and not c.get("archived")}
    ids = []
    for t in TARJETAS:
        datos = {
            "name": t["nombre"],
            "display": t["display"],
            "collection_id": col_id,
            "visualization_settings": t["viz"],
            "dataset_query": {"type": "native", "database": db_id,
                              "native": {"query": (SQL / t["archivo"]).read_text().strip().rstrip(";")}},
        }
        if t["nombre"] in existentes:
            card_id = existentes[t["nombre"]]
            mb.pedir("PUT", f"/api/card/{card_id}", datos)
        else:
            card_id = mb.pedir("POST", "/api/card", datos)["id"]
        filas = mb.pedir("POST", f"/api/card/{card_id}/query")
        if filas.get("status") != "completed":
            sys.exit(f"{t['nombre']}: {filas.get('error')}")
        print(f"{t['nombre']}: {len(filas['data']['rows'])} filas")
        ids.append(card_id)
    return ids


def tablero(mb, col_id, ids):
    dash_id = next((d["id"] for d in mb.pedir("GET", "/api/dashboard")
                    if d["name"] == TABLERO and d.get("collection_id") == col_id and not d.get("archived")), None)
    if dash_id is None:
        dash_id = mb.pedir("POST", "/api/dashboard", {"name": TABLERO, "collection_id": col_id,
                                                     "description": "Solicitudes por correo, ventas, stock y proyectos"})["id"]
    cards = []
    for i, (t, card_id) in enumerate(zip(TARJETAS, ids)):
        col, fila, ancho, alto = t["pos"]
        cards.append({"id": -(i + 1), "card_id": card_id, "col": col, "row": fila,
                      "size_x": ancho, "size_y": alto, "parameter_mappings": [],
                      "visualization_settings": {}})
    for j, (fila, texto) in enumerate(SECCIONES):
        cards.append({"id": -(len(cards) + 1), "card_id": None, "col": 0, "row": fila,
                      "size_x": 24, "size_y": 1, "parameter_mappings": [],
                      "visualization_settings": {
                          "virtual_card": {"name": None, "display": "heading", "visualization_settings": {},
                                           "dataset_query": {}, "archived": False},
                          "text": texto, "dashcard.background": False}})
    mb.pedir("PUT", f"/api/dashboard/{dash_id}", {"dashcards": cards, "width": "full"})
    return dash_id


def main():
    mb = Metabase(MB_URL)
    esperar(mb)
    iniciar_sesion(mb)
    db_id = base_odoo(mb)
    col_id = coleccion(mb)
    ids = tarjetas(mb, db_id, col_id)
    dash_id = tablero(mb, col_id, ids)
    print(f"Tablero disponible en {MB_URL}/dashboard/{dash_id}")


if __name__ == "__main__":
    main()
