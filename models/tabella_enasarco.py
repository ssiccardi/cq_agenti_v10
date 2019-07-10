# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, date
from res_partner import MESI_SELECTION

class TabellaEnasarco(models.Model):

    _name='tabella.enasarco'
    _order='anno desc,trimestre desc,mese desc,agente_id'
    
    @api.multi
    def name_get(self):
        return [(enasarco.id, '%s %s/%s'%(enasarco.agente_id.name,enasarco.mese,enasarco.anno)) for enasarco in self]

    agente_id = fields.Many2one('res.partner','Agente', required=True, domain=[('agente','=',True)])
    tipo_agente = fields.Selection((('persona','Persona Fisica'),('societa','Società di capitali')),'Tipo Agente', default='persona')
    mandato = fields.Selection((('M','Monomandatario'),('P','Plurimandatario')),'Mandato')
    anno = fields.Char('Anno', default=str(datetime.today().year))
    trimestre = fields.Integer('Trimestre')
    mese = fields.Selection(MESI_SELECTION,'Mese')
    provvigione = fields.Float('Provvigione Maturata (€)')
    contributo_mese = fields.Float('Contributo Mensile (€)')
    cont_agenzia = fields.Float('Agenzia (€)')
    cont_mandante = fields.Float('Mandante (€)')
    integrazione = fields.Float('Integrazione Mandante (€)')
    quota_fattura = fields.Float('Quota in fattura (€)')
    fattura_id = fields.Many2one('account.invoice','Fattura', domain=[('type','=','in_invoice')])
    provvigioni_ids = fields.One2many('cq.provvigioni', 'record_enasarco', 'provvigioni')
    company_id = fields.Many2one('res.company', string="Company")

    @api.one
    @api.constrains('anno')
    def check_anno(self):
        try:
            int(self.anno)
        except ValueError:
            raise ValidationError("Controllare l'anno inserito")
