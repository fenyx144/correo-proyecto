#!/usr/bin/env python3
"""Carga datos de ejemplo de los últimos 12 meses en Odoo: clientes, oportunidades, cotizaciones, ventas y proyectos."""
import argparse
import json
import os
import random
import shlex
import subprocess
import sys
import urllib.request
from datetime import date, datetime, time, timedelta

ODOO_URL = os.environ.get("ODOO_PUBLIC_URL", "http://localhost:8069").rstrip("/")
ODOO_DB = os.environ["ODOO_DB"]
ODOO_USER = os.environ["ODOO_USER"]
ODOO_API_KEY = os.environ["ODOO_API_KEY"]
PSQL = os.environ.get("DATOS_PSQL", f"docker compose exec -T db psql -U odoo -d {ODOO_DB} -v ON_ERROR_STOP=1 -q")

PREFIJO = "EJ-"
UTC_LIMA = timedelta(hours=5)

EMPRESAS = [
    ("Agroexportadora Sur Andino S.A.C.", "20455128731", "Arequipa", "Rosa Huamán", "Jefa de Logística"),
    ("Clínica San Gabriel S.A.", "20498765412", "Arequipa", "Luis Paredes", "Administrador"),
    ("Constructora Misti E.I.R.L.", "20601234875", "Arequipa", "Martín Salas", "Gerente de Obras"),
    ("Colegio Santa Rosa de Lima", "20187654329", "Arequipa", "Ana Torres", "Directora"),
    ("Hotel Plaza Yanahuara S.A.C.", "20539871246", "Arequipa", "Jorge Cáceres", "Gerente General"),
    ("Transportes Chachani S.R.L.", "20412398765", "Arequipa", "Elena Quispe", "Jefa de Operaciones"),
    ("Ferretería El Inca S.A.C.", "20605478123", "Cusco", "Pedro Mamani", "Propietario"),
    ("Laboratorio Clínico Andes S.A.C.", "20567812349", "Arequipa", "Carmen Flores", "Coordinadora de TI"),
    ("Textil Alpaca del Sur S.A.", "20100987654", "Arequipa", "Ricardo Benavides", "Jefe de Planta"),
    ("Minera Cerro Azul S.A.A.", "20334567891", "Moquegua", "Julio Ccama", "Superintendente de Seguridad"),
    ("Panificadora Yanahuara E.I.R.L.", "20609871234", "Arequipa", "Sofía Delgado", "Administradora"),
    ("Estudio Contable Vargas y Asociados", "20481237659", "Arequipa", "Raúl Vargas", "Socio"),
    ("Farmacias Selva Alegre S.A.C.", "20553219876", "Arequipa", "Lucía Ponce", "Jefa de Compras"),
    ("Inmobiliaria Cayma S.A.C.", "20578123456", "Arequipa", "Fernando Chávez", "Gerente de Proyectos"),
    ("Universidad Privada del Sur", "20203456781", "Arequipa", "Patricia Linares", "Jefa de Infraestructura"),
    ("Distribuidora Ccori S.A.C.", "20612345098", "Puno", "Wilber Condori", "Gerente Comercial"),
    ("Municipalidad Distrital de Sachaca", "20154321987", "Arequipa", "Gladys Apaza", "Subgerente de TI"),
    ("Grifo Los Andes S.R.L.", "20587612398", "Arequipa", "Hugo Zegarra", "Administrador"),
    ("Corporación Lechera Majes S.A.", "20398761245", "Arequipa", "Miriam Rojas", "Jefa de Sistemas"),
    ("Restaurante La Nueva Palomino", "20543219870", "Arequipa", "Óscar Palomino", "Propietario"),
    ("Centro Comercial Real Plaza Sur", "20509876123", "Arequipa", "Diana Medina", "Jefa de Mantenimiento"),
    ("Almacenes Tacna Sur S.A.C.", "20619876543", "Tacna", "Edwin Choque", "Jefe de Almacén"),
    ("Instituto Técnico Arequipa", "20176543218", "Arequipa", "Karina Salinas", "Coordinadora Académica"),
    ("Notaría Gutiérrez Rivera", "20591234567", "Arequipa", "Alberto Gutiérrez", "Notario"),
    ("Pesquera Ilo Mar S.A.C.", "20478123965", "Moquegua", "Verónica Ticona", "Jefa de Planta"),
]

SOLICITUDES = {
    "instalacion_red": [
        "Cableado estructurado para {n} puntos de red",
        "Renovación de red y WiFi en oficinas",
        "Ampliación de red para nuevo piso",
        "Instalación de gabinete y switch PoE",
    ],
    "videovigilancia": [
        "Sistema de videovigilancia con {n} cámaras",
        "Cámaras IP para almacén y patio de maniobras",
        "Ampliación de CCTV y acceso remoto",
        "Reemplazo de cámaras analógicas por IP",
    ],
}

PRODUCTOS_SERVICIO = {
    "instalacion_red": [("UTP-C6", 150, 600), ("SW-24P", 1, 2), ("AP-AX", 2, 6), ("RK-12U", 1, 1)],
    "videovigilancia": [("CAM-4MP", 4, 12), ("NVR-8", 1, 2), ("UTP-C6", 80, 300)],
}

MOTIVOS_PERDIDA = ["Precio", "Eligió otro proveedor", "Proyecto postergado", "Sin presupuesto"]


class Odoo:
    def __init__(self):
        self.uid = self.rpc("common", "login", [ODOO_DB, ODOO_USER, ODOO_API_KEY])
        if not self.uid:
            sys.exit("Odoo: usuario o API key incorrectos")

    def rpc(self, servicio, metodo, args):
        cuerpo = json.dumps({"jsonrpc": "2.0", "method": "call",
                             "params": {"service": servicio, "method": metodo, "args": args}}).encode()
        req = urllib.request.Request(f"{ODOO_URL}/jsonrpc", cuerpo, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            respuesta = json.load(resp)
        if "error" in respuesta:
            error = respuesta["error"]
            raise RuntimeError(error.get("data", {}).get("message") or error.get("message"))
        return respuesta.get("result")

    def __call__(self, modelo, metodo, args, **kwargs):
        return self.rpc("object", "execute_kw", [ODOO_DB, self.uid, ODOO_API_KEY, modelo, metodo, args, kwargs])

    def ref(self, xmlid):
        modulo, nombre = xmlid.split(".")
        datos = self("ir.model.data", "search_read", [[("module", "=", modulo), ("name", "=", nombre)]],
                     fields=["res_id"], limit=1)
        return datos[0]["res_id"] if datos else None


def utc(momento):
    return (momento + UTC_LIMA).strftime("%Y-%m-%d %H:%M:%S")


def habil(dia):
    while dia.weekday() >= 5:
        dia += timedelta(days=1)
    return dia


def momento_laboral(dia):
    dia = habil(dia)
    return datetime.combine(dia, time(random.randint(8, 17), random.randint(0, 59)))


def fecha_creacion(hoy, indice, total):
    meses = 11 - min(int(12 * indice / total), 11)
    inicio = (hoy.replace(day=1) - timedelta(days=30 * meses)).replace(day=1)
    fin = min(hoy - timedelta(days=1), (inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1))
    return momento_laboral(inicio + timedelta(days=random.randint(0, max((fin - inicio).days, 0))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oportunidades", type=int, default=80)
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument("--sin-fechas", action="store_true",
                        help="No ajusta las fechas históricas en PostgreSQL")
    parser.add_argument("--eliminar", action="store_true", help="Elimina los datos de ejemplo cargados")
    opciones = parser.parse_args()
    random.seed(opciones.semilla)

    odoo = Odoo()
    if opciones.eliminar:
        eliminar(odoo)
        return
    if odoo("res.partner", "search_count", [[("ref", "=like", f"{PREFIJO}%")]]):
        print("Los datos de ejemplo ya están cargados.")
        return

    hoy = date.today()
    ahora = datetime.now()
    automatizacion = odoo.ref("correo_proyecto.automation_oportunidad_ganada")
    productos = {p["default_code"]: p for p in odoo(
        "product.product", "search_read", [[("default_code", "in", ["UTP-C6", "SW-24P", "AP-AX", "CAM-4MP", "NVR-8", "RK-12U"])]],
        fields=["default_code", "lst_price"])}
    servicios = {s["code"]: s for s in odoo("crm.service.type", "search_read", [[]], fields=["code", "name"])}
    plantillas = {codigo: odoo("crm.service.type.task", "search_read", [[("service_type_id", "=", s["id"])]],
                               fields=["name", "days_offset", "user_id"], order="sequence, id")
                  for codigo, s in servicios.items()}
    etapas = odoo("crm.stage", "search_read", [[]], fields=["name", "is_won"], order="sequence")
    etapa_ganada = next(e["id"] for e in etapas if e["is_won"])
    etapas_abiertas = [e["id"] for e in etapas if not e["is_won"]]
    motivos = {m["name"]: m["id"] for m in odoo("crm.lost.reason", "search_read", [[]], fields=["name"])}
    for nombre in MOTIVOS_PERDIDA:
        if nombre not in motivos:
            motivos[nombre] = odoo("crm.lost.reason", "create", [{"name": nombre}])

    fechas = []

    def fecha_sql(tabla, registro, **campos):
        asignaciones = ", ".join(f"{campo} = '{valor}'" for campo, valor in campos.items())
        fechas.append(f"UPDATE {tabla} SET {asignaciones} WHERE id = {registro};")

    if automatizacion:
        odoo("base.automation", "write", [[automatizacion], {"active": False}])
    try:
        clientes = []
        for i, (empresa, ruc, ciudad, contacto, cargo) in enumerate(EMPRESAS, start=1):
            dominio = empresa.lower().split()[0].replace("ó", "o").replace("í", "i").replace("é", "e")
            empresa_id = odoo("res.partner", "create", [{
                "name": empresa, "is_company": True, "vat": ruc, "ref": f"{PREFIJO}{i:03d}",
                "city": ciudad, "country_id": odoo.ref("base.pe"),
                "phone": f"+51 54 {random.randint(200000, 499999)}", "email": f"contacto@{dominio}.com.pe",
            }])
            nombre_pila = contacto.split()[0].lower().replace("ó", "o").replace("í", "i").replace("é", "e").replace("ú", "u")
            contacto_id = odoo("res.partner", "create", [{
                "name": contacto, "parent_id": empresa_id, "function": cargo,
                "email": f"{nombre_pila}@{dominio}.com.pe", "mobile": f"+51 9{random.randint(10000000, 99999999)}",
            }])
            clientes.append((empresa_id, contacto_id, empresa))

        total = opciones.oportunidades
        ganadas = []
        for i in range(total):
            empresa_id, contacto_id, empresa = clientes[i % len(clientes)] if i < len(clientes) else random.choice(clientes)
            codigo = random.choice(list(servicios))
            creada = fecha_creacion(hoy, i, total)
            antiguedad = (ahora - creada).days
            por_correo = random.random() < 0.72
            n = random.choice([8, 12, 16, 24, 32])
            titulo = random.choice(SOLICITUDES[codigo]).format(n=n)

            sorteo = random.random()
            if antiguedad < 20:
                resultado = "abierta" if sorteo < 0.75 else "ganada"
            elif antiguedad < 60:
                resultado = "ganada" if sorteo < 0.35 else "perdida" if sorteo < 0.55 else "abierta"
            else:
                resultado = "ganada" if sorteo < 0.42 else "perdida" if sorteo < 0.8 else "abierta"

            lineas = []
            for producto, minimo, maximo in PRODUCTOS_SERVICIO[codigo]:
                if random.random() < 0.85:
                    cantidad = random.randint(minimo, maximo)
                    if resultado == "abierta" and producto in ("SW-24P", "CAM-4MP", "AP-AX") and random.random() < 0.25:
                        cantidad *= 4
                    lineas.append((producto, cantidad))
            importe = sum(productos[p]["lst_price"] * c for p, c in lineas) * 1.18

            lead_id = odoo("crm.lead", "create", [{
                "name": f"{empresa.split(' S.')[0]}: {titulo}",
                "type": "opportunity",
                "partner_id": contacto_id,
                "request_origin": "email" if por_correo else "manual",
                "service_type_id": servicios[codigo]["id"],
                "urgency": random.choice(["baja", "media", "media", "alta"]),
                "expected_revenue": round(importe, 2),
                "probability": random.choice([20, 35, 50, 65, 80]) if resultado == "abierta" else 50,
                "stage_id": random.choice(etapas_abiertas) if resultado == "abierta" else etapas_abiertas[0],
                "desired_date": (creada.date() + timedelta(days=random.randint(10, 45))).isoformat(),
                "requested_items": "\n".join(f"{c} x {p}" for p, c in lineas),
                "ai_summary": f"{titulo}. Solicitud recibida de {empresa}." if por_correo else False,
            }])
            fecha_sql("crm_lead", lead_id, create_date=utc(creada), date_open=utc(creada),
                      date_last_stage_update=utc(creada))

            pedido_id = None
            if lineas and (resultado == "ganada" or (resultado == "abierta" and random.random() < 0.6)):
                pedido_id = odoo("sale.order", "create", [{
                    "partner_id": empresa_id,
                    "partner_invoice_id": empresa_id,
                    "partner_shipping_id": empresa_id,
                    "opportunity_id": lead_id,
                    "origin": f"Oportunidad {lead_id}",
                    "order_line": [(0, 0, {"product_id": productos[p]["id"], "product_uom_qty": c}) for p, c in lineas],
                }])
                cotizada = creada + timedelta(minutes=random.randint(1, 4) if por_correo else random.randint(120, 2880))
                fecha_sql("sale_order", pedido_id, create_date=utc(cotizada), date_order=utc(cotizada))

            if resultado == "ganada":
                cierre = momento_laboral(creada.date() + timedelta(days=random.randint(3, min(25, max(antiguedad - 1, 3)))))
                cierre = min(cierre, ahora - timedelta(hours=2))
                odoo("crm.lead", "write", [[lead_id], {"stage_id": etapa_ganada, "probability": 100}])
                fecha_sql("crm_lead", lead_id, date_closed=utc(cierre), date_last_stage_update=utc(cierre))
                if pedido_id:
                    odoo("sale.order", "action_confirm", [[pedido_id]])
                    fecha_sql("sale_order", pedido_id, date_order=utc(cierre + timedelta(minutes=1)))
                if pedido_id:
                    ganadas.append((cierre, pedido_id, lead_id, empresa_id, codigo, f"{empresa.split(' S.')[0]}: {titulo}"))
            elif resultado == "perdida":
                cierre = momento_laboral(creada.date() + timedelta(days=random.randint(5, 30)))
                odoo("crm.lead", "write", [[lead_id], {"lost_reason_id": motivos[random.choice(MOTIVOS_PERDIDA)]}])
                odoo("crm.lead", "action_set_lost", [[lead_id]])
                fecha_sql("crm_lead", lead_id, date_closed=utc(min(cierre, ahora)))

        entregar(odoo, [g[1] for g in ganadas if g[0] < ahora - timedelta(days=21)])

        ganadas.sort()
        con_proyecto = ganadas[-12:]
        for cierre, _pedido, lead_id, empresa_id, codigo, nombre in con_proyecto:
            proyecto_id = crear_proyecto(odoo, fecha_sql, plantillas[codigo], lead_id, empresa_id, nombre, cierre, ahora)
            odoo("crm.lead", "write", [[lead_id], {"project_id": proyecto_id}])
    finally:
        if automatizacion:
            odoo("base.automation", "write", [[automatizacion], {"active": True}])

    print(f"Clientes: {len(clientes)}. Oportunidades: {opciones.oportunidades}. Ventas: {len(ganadas)}. Proyectos: {len(con_proyecto)}.")
    if opciones.sin_fechas:
        return
    print("Ajustando fechas históricas en PostgreSQL...")
    subprocess.run(shlex.split(PSQL), input="BEGIN;\n" + "\n".join(fechas) + "\nCOMMIT;\n",
                   text=True, check=True)
    print("Listo.")


def entregar(odoo, pedidos):
    if not pedidos:
        return
    movimientos = odoo("stock.move", "search_read",
                       [[("sale_line_id.order_id", "in", pedidos), ("state", "not in", ["done", "cancel"])]],
                       fields=["product_id", "product_uom_qty", "picking_id", "location_id"])
    ubicacion = movimientos[0]["location_id"][0] if movimientos else None
    reposicion = {}
    for movimiento in movimientos:
        producto = movimiento["product_id"][0]
        reposicion[producto] = reposicion.get(producto, 0) + movimiento["product_uom_qty"]
    for producto, cantidad in reposicion.items():
        quants = odoo("stock.quant", "search_read", [[("product_id", "=", producto), ("location_id", "=", ubicacion)]],
                      fields=["quantity"], limit=1)
        disponible = quants[0]["quantity"] if quants else 0
        quant_id = odoo("stock.quant", "create", [{"product_id": producto, "location_id": ubicacion,
                                                    "inventory_quantity": disponible + cantidad}],
                        context={"inventory_mode": True})
        odoo("stock.quant", "action_apply_inventory", [[quant_id]])
    for movimiento in movimientos:
        odoo("stock.move", "write", [[movimiento["id"]], {"quantity": movimiento["product_uom_qty"], "picked": True}])
    albaranes = sorted({m["picking_id"][0] for m in movimientos if m["picking_id"]})
    for albaran in albaranes:
        odoo("stock.picking", "button_validate", [[albaran]], context={"skip_backorder": True, "skip_sms": True})


def eliminar(odoo):
    empresas = odoo("res.partner", "search", [[("ref", "=like", f"{PREFIJO}%")]], context={"active_test": False})
    if not empresas:
        print("No hay datos de ejemplo cargados.")
        return
    socios = odoo("res.partner", "search", [["|", ("id", "in", empresas), ("parent_id", "in", empresas)]],
                  context={"active_test": False})
    pedidos = odoo("sale.order", "search", [[("partner_id", "in", socios)]])
    if pedidos:
        odoo("sale.order", "action_cancel", [pedidos], context={"disable_cancel_warning": True})
        odoo("sale.order", "unlink", [pedidos])
    proyectos = odoo("project.project", "search", [[("partner_id", "in", socios)]], context={"active_test": False})
    if proyectos:
        odoo("project.project", "unlink", [proyectos])
    oportunidades = odoo("crm.lead", "search", [[("partner_id", "in", socios)]], context={"active_test": False})
    if oportunidades:
        odoo("crm.lead", "unlink", [oportunidades])
    odoo("res.partner", "unlink", [socios])
    print(f"Eliminados {len(empresas)} clientes, {len(oportunidades)} oportunidades, "
          f"{len(pedidos)} pedidos y {len(proyectos)} proyectos de ejemplo.")


def crear_proyecto(odoo, fecha_sql, plantilla, lead_id, cliente_id, nombre, inicio, ahora):
    plazo = max([t["days_offset"] for t in plantilla] or [0])
    proyecto_id = odoo("project.project", "create", [{
        "name": nombre,
        "partner_id": cliente_id,
        "date_start": inicio.date().isoformat(),
        "date": habil(inicio.date() + timedelta(days=plazo)).isoformat(),
    }])
    fecha_sql("project_project", proyecto_id, create_date=utc(inicio + timedelta(minutes=2)))
    for tarea in plantilla:
        limite = datetime.combine(habil(inicio.date() + timedelta(days=tarea["days_offset"])), time(18))
        if limite < ahora - timedelta(days=14):
            estado = "1_done" if random.random() < 0.95 else "1_canceled"
        elif limite < ahora:
            estado = "1_done" if random.random() < 0.8 else "1_canceled" if random.random() < 0.15 else "01_in_progress"
        else:
            estado = "04_waiting_normal" if random.random() < 0.2 else "01_in_progress"
        tarea_id = odoo("project.task", "create", [{
            "project_id": proyecto_id,
            "name": tarea["name"],
            "partner_id": cliente_id,
            "user_ids": [(6, 0, [tarea["user_id"][0]] if tarea["user_id"] else [])],
            "date_deadline": utc(limite),
            "state": estado,
        }])
        fecha_sql("project_task", tarea_id, create_date=utc(inicio + timedelta(minutes=2)))
    return proyecto_id


if __name__ == "__main__":
    main()
