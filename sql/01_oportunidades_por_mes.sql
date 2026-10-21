-- Oportunidades creadas por mes, origen y etapa
SELECT
    date_trunc('month', l.create_date)::date                         AS mes,
    CASE l.request_origin WHEN 'email' THEN 'Correo automático' ELSE 'Manual' END AS origen,
    COALESCE(s.name->>'es_PE', s.name->>'en_US')                      AS etapa,
    count(*)                                                          AS oportunidades
FROM crm_lead l
LEFT JOIN crm_stage s ON s.id = l.stage_id
WHERE l.type = 'opportunity'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
