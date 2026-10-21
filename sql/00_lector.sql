-- Rol de solo lectura para Metabase. Ejecutar como superusuario sobre la base de Odoo:
--   docker compose exec -T db psql -U odoo -d empresa -v lector_password="'Lector2026Rpt'" -f - < sql/00_lector.sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lector') THEN
        CREATE ROLE lector LOGIN;
    END IF;
END
$$;

ALTER ROLE lector PASSWORD :lector_password;
ALTER ROLE lector SET default_transaction_read_only = on;

GRANT CONNECT ON DATABASE :"DBNAME" TO lector;
GRANT USAGE ON SCHEMA public TO lector;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM lector;
GRANT SELECT ON
    crm_lead,
    crm_stage,
    crm_tag,
    crm_tag_rel,
    crm_service_type,
    res_partner,
    res_users,
    sale_order,
    sale_order_line,
    product_product,
    product_template,
    stock_quant,
    stock_location,
    project_project,
    project_task,
    project_task_type
TO lector;
