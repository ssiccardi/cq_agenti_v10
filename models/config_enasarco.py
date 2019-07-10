# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, date

class ConfigEnasarco(models.Model):

    _name='config.enasarco'
    _order='anno desc'

    @api.multi
    def name_get(self):
        return [(config.id, 'Configurazione Enasarco %s'%config.anno) for config in self]

    anno = fields.Char('Anno', required=True, default=str(datetime.today().year))
    aliquota_soc_mono  = fields.Float('Aliquota contributiva Società (Monomand.)')
    aliquota_per_mono = fields.Float('Aliquota contributiva Persona Fisica (Monomand.)')
    aliquota_soc_pluri = fields.Float('Aliquota contributiva Società (Plurimand.)')
    aliquota_per_pluri = fields.Float('Aliquota contributiva Persona Fisica (Plurimand.)')
    carico_soc_mono_agen = fields.Float('Carico Agenzia Società (Monomand.)')
    carico_soc_mono_mand = fields.Float('Carico Mandante Società (Monomand.)')
    carico_soc_pluri_agen = fields.Float('Carico Agenzia Società (Plurimand.)')
    carico_soc_pluri_mand = fields.Float('Carico Mandante Società (Plurimand.)')
    carico_per_mono_agen = fields.Float('Carico Agenzia Persona Fisica (Monomand.)')
    carico_per_mono_mand = fields.Float('Carico Mandante Persona Fisica (Monomand.)')
    carico_per_pluri_agen = fields.Float('Carico Agenzia Persona Fisica (Plurimand.)')
    carico_per_pluri_mand = fields.Float('Carico Mandante Persona Fisica (Plurimand.)')
    provv_max_mono = fields.Float('Provvigione massima annuale (Monomand.)')
    provv_max_pluri = fields.Float('Provvigione massima annuale (Plurimand.)')
    cont_min_mono = fields.Float('Contributo minimo trimestrale (Monomand.)')
    cont_min_pluri = fields.Float('Contributo minimo trimestrale (Plurimand.)')
    campo_prezzo = fields.Char('Campo della fattura da usare per il prezzo', size=32, default='price_unit')

    @api.one
    @api.constrains('anno')
    def check_anno(self):
        try:
            int(self.anno)
        except ValueError:
            raise ValidationError("Controllare l'anno inserito")
