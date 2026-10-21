STOCK_INICIAL = {
    "correo_proyecto.product_cable_utp": 1500,
    "correo_proyecto.product_switch_24": 6,
    "correo_proyecto.product_ap_wifi6": 10,
    "correo_proyecto.product_camara_ip": 4,
    "correo_proyecto.product_nvr_8": 2,
    "correo_proyecto.product_rack_12u": 3,
}


def post_init_hook(env):
    _configurar_moneda(env)
    _cargar_stock(env)


def _configurar_moneda(env):
    pen = env.ref("base.PEN")
    if not pen.active:
        pen.active = True
    for company in env["res.company"].search([]):
        if company.currency_id == pen:
            continue
        if env["account.move.line"].search_count([("company_id", "=", company.id)], limit=1):
            continue
        anterior = company.currency_id
        company.currency_id = pen
        env["product.pricelist"].search([
            ("company_id", "in", [company.id, False]),
            ("currency_id", "=", anterior.id),
        ]).currency_id = pen


def _cargar_stock(env):
    Quant = env["stock.quant"].with_context(inventory_mode=True)
    for warehouse in env["stock.warehouse"].search([], limit=1):
        for xmlid, cantidad in STOCK_INICIAL.items():
            product = env.ref(xmlid, raise_if_not_found=False)
            if not product:
                continue
            variant = product.product_variant_id
            if variant.with_company(warehouse.company_id).qty_available:
                continue
            Quant.create({
                "product_id": variant.id,
                "location_id": warehouse.lot_stock_id.id,
                "inventory_quantity": cantidad,
            }).action_apply_inventory()
