-- Proyectos generados y estado de sus tareas
SELECT
    COALESCE(pr.name->>'es_PE', pr.name->>'en_US')                    AS proyecto,
    pa.name                                                           AS cliente,
    pr.create_date::date                                              AS creado,
    count(t.id)                                                       AS tareas,
    count(t.id) FILTER (WHERE t.state = '1_done')                     AS hechas,
    count(t.id) FILTER (WHERE t.state NOT IN ('1_done', '1_canceled')) AS pendientes,
    count(t.id) FILTER (WHERE t.state NOT IN ('1_done', '1_canceled')
                          AND t.date_deadline < now())                AS vencidas,
    min(t.date_deadline) FILTER (WHERE t.state NOT IN ('1_done', '1_canceled'))::date AS proximo_vencimiento,
    round(100.0 * count(t.id) FILTER (WHERE t.state = '1_done') / NULLIF(count(t.id), 0), 1) AS avance_pct
FROM project_project pr
LEFT JOIN res_partner pa ON pa.id = pr.partner_id
LEFT JOIN project_task t ON t.project_id = pr.id AND t.active
WHERE pr.active
GROUP BY pr.id, pa.name
ORDER BY pr.create_date DESC
