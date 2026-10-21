from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    request_origin = fields.Selection(
        [("manual", "Manual"), ("email", "Correo automático")],
        string="Origen de la solicitud", default="manual", tracking=True,
    )
    urgency = fields.Selection(
        [("baja", "Baja"), ("media", "Media"), ("alta", "Alta")],
        string="Urgencia", tracking=True,
    )
    service_type_id = fields.Many2one("crm.service.type", string="Tipo de servicio", tracking=True)
    desired_date = fields.Date("Fecha deseada")
    ai_summary = fields.Text("Resumen de la solicitud")
    requested_items = fields.Text("Productos solicitados")
    gmail_message_id = fields.Char("ID de mensaje Gmail", index=True, copy=False, readonly=True)
    project_id = fields.Many2one("project.project", string="Proyecto", copy=False, tracking=True)

    _sql_constraints = [
        ("gmail_message_unique", "unique(gmail_message_id)", "Este correo ya generó una oportunidad."),
    ]

    def action_open_project(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "res_id": self.project_id.id,
            "view_mode": "form",
        }
