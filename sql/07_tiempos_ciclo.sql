-- Tiempo promedio desde el correo hasta la oportunidad ganada y el proyecto
WITH ciclo AS (
    SELECT
        l.id,
        l.create_date                                                 AS creada,
        l.date_closed                                                 AS ganada,
        (SELECT min(o.date_order) FROM sale_order o
          WHERE o.opportunity_id = l.id AND o.state = 'sale')         AS venta,
        pr.create_date                                                AS proyecto
    FROM crm_lead l
    JOIN crm_stage s ON s.id = l.stage_id AND s.is_won
    LEFT JOIN project_project pr ON pr.id = l.project_id
    WHERE l.type = 'opportunity' AND l.request_origin = 'email'
)
SELECT
    count(*)                                                          AS oportunidades_ganadas,
    round(avg(extract(epoch FROM ganada - creada)) / 60.0, 1)         AS minutos_correo_a_ganada,
    round(avg(extract(epoch FROM venta - creada)) / 60.0, 1)          AS minutos_correo_a_venta,
    round(avg(extract(epoch FROM proyecto - creada)) / 60.0, 1)       AS minutos_correo_a_proyecto
FROM ciclo
