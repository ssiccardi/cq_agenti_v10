# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"
    
    provvigione = fields.Float('Provvigione (%)', default=0.0)
    agente_id = fields.Many2one('res.partner','Agente', domain=[('agente','=',True)])
    date_invoice = fields.Date('Data fattura', related="invoice_id.date_invoice")
    category_id = fields.Many2one(related='product_id.categ_id', string="Categoria Prodotto", store=True)
    invoice_state = fields.Selection("Stato", related="invoice_id.state")

    def _set_additional_fields(self, invoice):

        res = super(AccountInvoiceLine, self)._set_additional_fields(invoice)

        # compilo i campi agente e provvigione sulle righe della fattura
        if invoice.type in ('out_invoice','out_refund'):
            sale_lines = self.mapped('sale_line_ids')
            # non compilo i campi se il prodotto è di tipo speciale o se è in cessione gratuita
            if not any(sale_line.prodotto_sconto or sale_line.product_id.sp_type for sale_line in sale_lines):
                order = sale_lines.mapped('order_id')
                if not order:
                    return res
                elif len(order) > 1:
                    order = order[0]
                if order.provvigioni and order.agente_id:
                    agente = order.agente_id
                    cliente = order.partner_id
                    prodotto = self.product_id
                    percprovv = 0
                    if prodotto:
                        categoria = prodotto.categ_id
                        prodotto_escluso = prodotto.getnoprovvigioni() or categoria.getnoprovvigioni()
                        if not prodotto_escluso:
                            percprovv = order.percagente or prodotto.getpercagente() or categoria.getpercagente() or cliente.provvcli or agente.provvage
                    else:
                        #non può non esserci il prodotto perchè sul SO è obbligatorio, ma lo lascio per sicurezza
                        percprovv = order.percagente or cliente.provvcli or agente.provvage
                    if percprovv:
                        self.write({'agente_id': agente.id, 'provvigione': percprovv})
        return res

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    provvigioni = fields.One2many('cq.provvigioni', 'invoice_id', 'Provvigioni')
    provvigioni_count = fields.Float('# Provvigioni', compute="_get_provvigioni_count", readonly=True)

    @api.depends('provvigioni')
    def _get_provvigioni_count(self):
        for invoice in self:
            thisinv = invoice.refund_invoice_id or invoice
            invoice.provvigioni_count = len(thisinv.provvigioni) + sum(len(thisref.provvigioni) for thisref in self.search([('refund_invoice_id','=',thisinv.id)]))
            
    @api.multi
    def action_view_provvigioni(self):
        provvigioni_ids = []
        for invoice in self:
            thisinv = invoice.refund_invoice_id or invoice
            for provv in thisinv.provvigioni:
                provvigioni_ids.append(provv.id)
            for thisref in self.search([('refund_invoice_id','=',thisinv.id)]):
                for provv in thisref.provvigioni:
                    provvigioni_ids.append(provv.id)
        agente = self.mapped('invoice_line_ids.agente_id')
        if len(agente) != 1:
            agente = False
        if provvigioni_ids:
            action = self.env.ref('cq_agenti_v10.action_provvigioni').read()[0]
            action['domain'] = [('id','in',provvigioni_ids)]
            action['context'] = {'default_invoice_id': invoice.id, 
                                 'default_agente': agente.id if agente else False, 
                                 'on_invoice': True,
                                 'default_tipo_provv': 'ndc' if invoice.type == 'out_refund' else 'fatt'}
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
        
    @api.multi
    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        for invoice in self:
            self.env['cq.provvigioni'].crea_provvigione_da_fatturato(invoice)
            #segna pagate le provvigioni se si tratta di una fattura agente
            if invoice.type == 'in_invoice' and invoice.partner_id.agente:
                enasarco_records = self.env['tabella.enasarco'].search([('fattura_id','=',invoice.id)])
                if enasarco_records:
                    enasarco_records.mapped('provvigioni_ids').write({'pagato': True, 'data_pag_pro': datetime.today()})
        return res

class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"
    
    @api.model
    def create(self, vals):
        reconcile = super(AccountPartialReconcile, self).create(vals)
        if not self.env['ir.values'].get_default('sale.config.settings', 'provvigione_pagato_tot'):
            self.env['cq.provvigioni'].crea_provvigione_da_pagamento_parziale(reconcile)
        return reconcile

    @api.multi
    def unlink(self):
        for reconcile in self:
            self.env['cq.provvigioni'].elimina_provvigione_da_pagamento_parziale(reconcile)
        return super(AccountPartialReconcile, self).unlink()

class AccountFullReconcile(models.Model):
    _inherit = "account.full.reconcile"

    @api.model
    def create(self, vals):
        reconcile = super(AccountFullReconcile, self).create(vals)
        if self.env['ir.values'].get_default('sale.config.settings', 'provvigione_pagato_tot'):
            self.env['cq.provvigioni'].crea_provvigione_da_pagamento(reconcile)
        return reconcile

    @api.multi
    def unlink(self):
        for reconcile in self:
            self.env['cq.provvigioni'].elimina_provvigione_da_pagamento(reconcile)
        return super(AccountFullReconcile, self).unlink()
