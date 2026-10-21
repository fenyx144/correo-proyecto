-- Productos con stock menor a lo pendiente de entregar en cotizaciones y ventas
WITH stock AS (
    SELECT q.product_id, sum(q.quantity - q.reserved_quantity) AS disponible, sum(q.quantity) AS a_mano
    FROM stock_quant q
    JOIN stock_location loc ON loc.id = q.location_id
    WHERE loc.usage = 'internal'
    GROUP BY q.product_id
),
solicitado AS (
    SELECT
        l.product_id,
        sum(l.product_uom_qty - l.qty_delivered)                      AS cantidad_solicitada,
        count(DISTINCT l.order_id)                                    AS pedidos,
        string_agg(DISTINCT o.name, ', ' ORDER BY o.name)             AS documentos
    FROM sale_order_line l
    JOIN sale_order o ON o.id = l.order_id
    WHERE o.state IN ('draft', 'sent', 'sale')
      AND l.product_id IS NOT NULL
      AND l.display_type IS NULL
      AND l.product_uom_qty > l.qty_delivered
    GROUP BY l.product_id
)
SELECT
    p.default_code                                                    AS codigo,
    COALESCE(t.name->>'es_PE', t.name->>'en_US')                      AS producto,
    sol.cantidad_solicitada,
    COALESCE(st.a_mano, 0)                                            AS stock_a_mano,
    sol.cantidad_solicitada - COALESCE(st.a_mano, 0)                  AS faltante,
    sol.pedidos,
    sol.documentos
FROM solicitado sol
JOIN product_product p  ON p.id = sol.product_id
JOIN product_template t ON t.id = p.product_tmpl_id
LEFT JOIN stock st      ON st.product_id = sol.product_id
WHERE t.type = 'consu' AND t.is_storable
  AND sol.cantidad_solicitada > COALESCE(st.a_mano, 0)
ORDER BY faltante DESC
