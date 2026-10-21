-- Indicadores generales
SELECT
    (SELECT count(*) FROM crm_lead WHERE type = 'opportunity' AND request_origin = 'email') AS oportunidades_por_correo,
    (SELECT count(*) FROM sale_order WHERE state = 'sale')                               AS ventas_confirmadas,
    (SELECT round(COALESCE(sum(amount_total), 0), 2) FROM sale_order WHERE state = 'sale') AS monto_confirmado,
    (SELECT count(*) FROM project_project WHERE active)                                  AS proyectos_activos
