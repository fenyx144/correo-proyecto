-- Cotizaciones y ventas confirmadas por mes
SELECT
    date_trunc('month', o.date_order)::date                          AS mes,
    count(*) FILTER (WHERE o.state IN ('draft', 'sent'))              AS cotizaciones_abiertas,
    count(*) FILTER (WHERE o.state = 'sale')                          AS ventas_confirmadas,
    round(sum(o.amount_total) FILTER (WHERE o.state IN ('draft', 'sent')), 2) AS monto_cotizado,
    round(sum(o.amount_total) FILTER (WHERE o.state = 'sale'), 2)     AS monto_confirmado,
    round(avg(o.amount_total) FILTER (WHERE o.state = 'sale'), 2)     AS ticket_promedio
FROM sale_order o
WHERE o.state <> 'cancel'
GROUP BY 1
ORDER BY 1
