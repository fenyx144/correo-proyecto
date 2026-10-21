from odoo import fields, models


class CrmServiceType(models.Model):
    _name = "crm.service.type"
    _description = "Tipo de servicio"
    _order = "sequence, name"

    name = fields.Char("Nombre", required=True, translate=True)
    code = fields.Char("Código", required=True, help="Código que usa la clasificación de correos.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text("Descripción")
    task_ids = fields.One2many("crm.service.type.task", "service_type_id", string="Tareas", copy=True)
    task_count = fields.Integer("N.º de tareas", compute="_compute_task_count")

    _sql_constraints = [
        ("code_unique", "unique(code)", "El código del tipo de servicio debe ser único."),
    ]

    def _compute_task_count(self):
        for record in self:
            record.task_count = len(record.task_ids)


class CrmServiceTypeTask(models.Model):
    _name = "crm.service.type.task"
    _description = "Tarea de plantilla"
    _order = "sequence, id"

    service_type_id = fields.Many2one("crm.service.type", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char("Tarea", required=True)
    days_offset = fields.Integer("Plazo (días)", default=1, help="Días desde la fecha de inicio del proyecto.")
    user_id = fields.Many2one("res.users", string="Responsable", domain=[("share", "=", False)])
    description = fields.Html("Descripción")
