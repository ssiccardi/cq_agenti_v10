# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CQRicalcolaCampi(models.TransientModel):

    _inherit = 'cq.ricalcola.campi'

#// Wizard per valorizzare campo Categoria Prodotto su sulle righe fatture prendendola dalla scheda
#// del prodotto inserito in riga (problema legato al campo related category_id di account.invoice.line
#// che se vuoto non permetta la creazione di nota credito dalla fattura)
    @api.multi
    def recompute_category_id_invoice_line(self):
        ProductProduct = self.env['product.product']
        ProductTemplate = self.env['product.template']
        AccountInvoiceLine = self.env['account.invoice.line']

        invoice_lines = AccountInvoiceLine.search(
            [('category_id','=',False), ('product_id','!=',False)]
        )
        for line in invoice_lines:
            if line.product_id.categ_id:
                line.write({'category_id': line.product_id.categ_id.id})
        return {'type': 'ir.actions.act_window_close'}
