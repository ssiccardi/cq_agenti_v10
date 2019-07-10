# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleConfiguration(models.TransientModel):

    _inherit = 'sale.config.settings'
    
    calcolo_provvigioni = fields.Selection([
        (0, 'Sul pagato'),
        (1, 'Sul fatturato')
        ], "Politica Provvigioni",
        help="Questa configurazione serve per il default della 'Percentuale anticipo' sulla scheda dell'agente")
    provvigione_pagato_tot = fields.Boolean("Provvigione fattura pagata", help="Riconosci la provvigione sul pagato solo quando la fattura è stata completamente pagata")
    group_enasarco = fields.Selection([
        (0, "No enasarco"),
        (1, 'Includi gestione enasarco')
        ], "Gestione Enasarco",
        implied_group='cq_agenti_v10.group_enasarco')
    
    @api.multi
    def set_calcolo_provvigioni_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'calcolo_provvigioni', self.calcolo_provvigioni)
            
    @api.multi
    def set_provvigione_pagato_tot_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'provvigione_pagato_tot', self.provvigione_pagato_tot)
