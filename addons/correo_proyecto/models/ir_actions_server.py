from odoo import models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    def _run_action_webhook(self, eval_context=None):
        action = self.env.ref("correo_proyecto.action_webhook_oportunidad_ganada", raise_if_not_found=False)
        if action and self == action:
            url = self.env["ir.config_parameter"].sudo().get_param("correo_proyecto.webhook_url")
            if url and url != self.webhook_url:
                self.sudo().webhook_url = url
        return super()._run_action_webhook(eval_context=eval_context)
