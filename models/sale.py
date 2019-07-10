# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    provvigioni = fields.Boolean('Calcola provvigioni', default=False)
    agente_id = fields.Many2one('res.partner', 'Agente', domain=[('agente','=',True)])
    percagente = fields.Float('Provvigione speciale', 
                   help="Inserisci una percentuale se quest'ordine non rispetta le regole standard per il calcolo delle provvigioni.", default=0.0)
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(SaleOrder, self).onchange_partner_id()
        if self.partner_id.agente_id:
            self.provvigioni = True
            self.agente_id = self.partner_id.agente_id.id
        else:
            self.provvigioni = False
            self.agente_id = False

    @api.one
    @api.constrains('percagente')
    def percagente_constraint(self):
        if self.percagente < 0 or self.percagente > 100:
            raise ValidationError("La percentuale provvigione deve essere compresa tra 0 e 100.")

