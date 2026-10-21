-- Tareas por estado
SELECT
    CASE
        WHEN t.state = '1_done'                      THEN 'Hecha'
        WHEN t.state = '1_canceled'                  THEN 'Cancelada'
        WHEN t.date_deadline < now()                 THEN 'Vencida'
        WHEN t.state = '04_waiting_normal'           THEN 'En espera'
        WHEN t.state = '02_changes_requested'        THEN 'Cambios solicitados'
        WHEN t.state = '03_approved'                 THEN 'Aprobada'
        ELSE 'En curso'
    END                                                               AS estado,
    count(*)                                                          AS tareas
FROM project_task t
JOIN project_project pr ON pr.id = t.project_id
WHERE t.active
GROUP BY 1
ORDER BY 2 DESC
