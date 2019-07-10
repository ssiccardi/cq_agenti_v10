# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date

MESI_SELECTION = [('01','Gen'),('02','Feb'),('03','Mar'),('04','Apr'),('05','Mag'),('06','Giu'),('07','Lug'),('08','Ago'),('09','Set'),('10','Ott'),('11','Nov'),('12','Dic')]
    
class Partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_defatul_perc_acnticipo_provv(self):
        if self.env['ir.values'].get_default('sale.config.settings', 'calcolo_provvigioni') == 1:
            return 100
        else:
            return 0

    agente = fields.Boolean('È un Agente', default=False)
    provvage = fields.Float('Provvigione', default=0.0)
    perc_acnticipo_provv = fields.Float('Su fatturato', default=_get_defatul_perc_acnticipo_provv, 
                                   help="Percentuale della provvigione riconosciuta al momento della validazione della fattura.")
    provvcli = fields.Float('Provvigione', default=0.0)
    agente_id = fields.Many2one('res.partner', 'Agente', domain=[('agente','=',True)])
    #enasarco
    tipo_agente = fields.Selection((('persona','Persona Fisica'),('societa','Società di capitali')),'Tipo Agente', default='persona')
    fisso_mensile = fields.Float('Fisso mensile')
    mandato_history_line = fields.One2many('mandato.history','agente_id','Storico Mandato')

    @api.one
    @api.constrains('supplier')
    def agente_constraint(self):
        if not self.supplier:
            self.agente = False

    @api.one
    @api.constrains('customer')
    def customer_agente_constraint(self):
        if not self.customer:
            self.agente_id = False

    @api.one
    @api.constrains('provvage', 'provvcli', 'perc_acnticipo_provv')
    def perc_constraint(self):
        if self.provvage < 0 or self.provvage > 100:
            raise ValidationError("La percentuale provvigione agente deve essere compresa tra 0 e 100.")
        if self.provvcli < 0 or self.provvcli > 100:
            raise ValidationError("La percentuale provvigione cliente deve essere compresa tra 0 e 100.")
        if self.perc_acnticipo_provv < 0 or self.perc_acnticipo_provv > 100:
            raise ValidationError("La percentuale provvigione su fatturato deve essere compresa tra 0 e 100.")
    

class MandatoHistory(models.Model):

    _name = 'mandato.history'
    _order='anno_start desc,mese_start desc' 

    agente_id = fields.Many2one('res.partner', 'Agente', required=True, domain=[('agente','=',True)])
    mandato = fields.Selection((('M','Monomandatario'),('P','Plurimandatario')),'Mandato')
    mese_start = fields.Selection(
        MESI_SELECTION, 'Mese inizio', default = str(datetime.today().month).zfill(2)
    )
    anno_start = fields.Char('Anno inizio', default=str(datetime.today().year))
    mese_end = fields.Selection(MESI_SELECTION, 'Mese fine')
    anno_end = fields.Char('Anno fine')
    
    @api.one
    @api.constrains('anno_start','anno_end')
    def check_anno(self):
        try:
            int(self.anno_start)
            int(self.anno_end)
        except ValueError:
            raise ValidationError("Controllare l'anno inserito")

