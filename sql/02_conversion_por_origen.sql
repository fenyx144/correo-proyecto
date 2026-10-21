-- Tasa de conversión e ingreso esperado por origen
WITH base AS (
    SELECT
        CASE l.request_origin WHEN 'email' THEN 'Correo automático' ELSE 'Manual' END AS origen,
        COALESCE(s.is_won, false)                                     AS ganada,
        l.active,
        l.expected_revenue,
        l.probability,
        so.monto_confirmado
    FROM crm_lead l
    LEFT JOIN crm_stage s ON s.id = l.stage_id
    LEFT JOIN LATERAL (
        SELECT sum(o.amount_total) AS monto_confirmado
        FROM sale_order o
        WHERE o.opportunity_id = l.id AND o.state = 'sale'
    ) so ON true
    WHERE l.type = 'opportunity'
)
SELECT
    origen,
    count(*)                                                          AS oportunidades,
    count(*) FILTER (WHERE ganada)                                    AS ganadas,
    count(*) FILTER (WHERE NOT active AND NOT ganada)                 AS perdidas,
    round(100.0 * count(*) FILTER (WHERE ganada) / NULLIF(count(*), 0), 1) AS tasa_conversion_pct,
    round((sum(expected_revenue * probability / 100.0) FILTER (WHERE active AND NOT ganada))::numeric, 2) AS ingreso_ponderado_abierto,
    round(COALESCE(sum(monto_confirmado), 0), 2)                      AS monto_vendido
FROM base
GROUP BY origen
ORDER BY oportunidades DESC
