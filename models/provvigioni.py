# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare

class CQProvvigioni(models.Model):

    _name = "cq.provvigioni"
    _description = "Provvigioni agenti"
    _order = "agente, invoice_id, payment_id"

    @api.multi
    def name_get(self):
        return [(provv.id, (provv.agente.name or '') + '  ' + (provv.invoice_id.number or '')) for provv in self]
    
    @api.multi
    @api.depends('credit_move_id', 'payment_id', 'company_currency_id')
    def _get_importo_pagamento(self):
        for provv in self:
            if provv.credit_move_id:
                provv.importo_pag = abs(provv.credit_move_id.debit - provv.credit_move_id.credit)
            elif provv.payment_id:
                payment = provv.payment_id
                provv.importo_pag = payment.currency_id.with_context(date=payment.payment_date).compute(payment.amount, provv.company_currency_id)
        
    agente = fields.Many2one('res.partner', 'Agente', domain=[('agente','=',True)], required=True)
    country_id = fields.Many2one('res.country', 'Nazione', related="agente.country_id", store=True, readonly=True)
    credit_move_id = fields.Many2one("account.move.line", "riga pagamento")
    invoice_id = fields.Many2one('account.invoice', 'Fattura', domain=[('type','in',['out_invoice','out_refund'])], required=True, ondelete="cascade")
    cliente = fields.Many2one('res.partner', 'Cliente', related="invoice_id.partner_id", store=True, readonly=True)
    tot_fatt = fields.Monetary('Totale Fattura', related="invoice_id.amount_total_company_signed", currency_field='company_currency_id')
    date_invoice = fields.Date('Data Fattura', related="invoice_id.date_invoice", readonly=True)
    tipo_pagamento = fields.Many2one('account.payment.term','Termini di pagamento', related="invoice_id.payment_term_id")
    payment_id = fields.Many2one('account.payment', 'Pagamento')
    data_pag = fields.Date('Data pagamento', related="payment_id.payment_date", readonly=True)
    importo_pag = fields.Monetary('Importo Pagamento', compute="_get_importo_pagamento", currency_field='company_currency_id')
    imponibile_provv = fields.Monetary('Imponibile per provvigione', currency_field='company_currency_id', group_operator='avg')
    tot_provv = fields.Monetary('Totale provvigione', currency_field='company_currency_id', group_operator='avg')
    da_pagare = fields.Monetary('Importo provvigione maturato', currency_field='company_currency_id')
    pagato = fields.Boolean('Provvigione pagata')
    data_pag_pro = fields.Date('Data pagamento provvigione')
    record_enasarco = fields.Many2one('tabella.enasarco','record enasarco')
    company_id = fields.Many2one('res.company', related='invoice_id.company_id', string="Company", readonly=True, store=True)
    company_currency_id = fields.Many2one('res.currency', related='invoice_id.company_currency_id', string="Valuta", readonly=True)
    tipo_provv = fields.Selection([('fatt', 'Da Fatturato'),('pag', 'Da Pagato'),('ndc','Da NdC')], "Tipo", default="fatt")

    @api.onchange('pagato')
    def change_flag_pagato(self):
        if self.pagato:
            self.data_pag_pro = fields.Date.today()
        else:
            self.data_pag_pro = False

    def get_provv_data(self, invoice):
        result = []
        agente_lines = {}
        for line in invoice.invoice_line_ids:
            agente = line.agente_id
            if agente:
                if agente not in agente_lines:
                    agente_lines[agente] = line
                else:
                    agente_lines[agente] += line
        for agente, lines in agente_lines.iteritems():
            imponibile_provv = tot_provv = 0.
            for line in lines:
                imponibile_provv += line.price_subtotal
                tot_provv += line.price_subtotal*line.provvigione/100.
            result.append((agente, imponibile_provv, tot_provv))
        return result

    def crea_provvigione_da_fatturato(self, invoice):
        to_currency = invoice.company_currency_id.with_context(date=invoice.date_invoice)
        from_currency = (invoice.currency_id and invoice.currency_id.with_context(date=invoice.date_invoice)) or to_currency
        digits_rounding_precision = to_currency.rounding

        if invoice.type == 'out_invoice':
            agenti_ids = []
            for (agente, imponibile_provv, tot_provv) in self.get_provv_data(invoice):
                agenti_ids.append(agente.id)
                da_pagare = tot_provv*agente.perc_acnticipo_provv/100.
                da_pagare = from_currency.compute(da_pagare, to_currency)
                old_provv = invoice.provvigioni.filtered(lambda x: x.agente == agente and x.tipo_provv == 'fatt')
                old_da_pagare = sum([provv.da_pagare for provv in old_provv])
                if not float_is_zero(da_pagare - old_da_pagare, precision_rounding=digits_rounding_precision):
                    old_provv.unlink()
                    if not float_is_zero(da_pagare, precision_rounding=digits_rounding_precision):
                        self.create({'invoice_id': invoice.id,
                                     'agente': agente.id,
                                     'imponibile_provv': from_currency.compute(imponibile_provv, to_currency),
                                     'tot_provv': from_currency.compute(tot_provv, to_currency),
                                     'da_pagare': da_pagare,
                                     'tipo_provv': 'fatt'})
            invoice.provvigioni.filtered(lambda x: x.agente.id not in agenti_ids and x.pagato == False and x.tipo_provv == 'fatt').unlink()
        elif invoice.type == 'out_refund':
            agenti_ids = []
            for (agente, imponibile_provv, tot_provv) in self.get_provv_data(invoice):
                agenti_ids.append(agente.id)
                da_pagare = tot_provv*agente.perc_acnticipo_provv/100.
                da_pagare = from_currency.compute(da_pagare, to_currency)
                old_provv = invoice.provvigioni.filtered(lambda x: x.agente == agente and x.tipo_provv == 'ndc')
                old_da_pagare = sum([provv.da_pagare for provv in old_provv])
                if not float_is_zero(da_pagare + old_da_pagare, precision_rounding=digits_rounding_precision):
                    old_provv.unlink()
                    if not float_is_zero(da_pagare, precision_rounding=digits_rounding_precision):
                        self.create({'invoice_id': invoice.id,
                                     'agente': agente.id,
                                     'imponibile_provv': -1*from_currency.compute(imponibile_provv, to_currency),
                                     'tot_provv': -1*from_currency.compute(tot_provv, to_currency),
                                     'da_pagare': -1*da_pagare,
                                     'tipo_provv': 'ndc'})
            invoice.provvigioni.filtered(lambda x: x.agente.id not in agenti_ids and x.pagato == False and x.tipo_provv == 'ndc').unlink()
        return True

    def crea_provvigione_da_pagamento(self, reconcile):
        for partial_reconcile in reconcile.partial_reconcile_ids:
            self.crea_provvigione_da_pagamento_parziale(partial_reconcile)
        return True

    def crea_provvigione_da_pagamento_parziale(self, reconcile):
        credit_move_id, debit_move_id = reconcile.credit_move_id, reconcile.debit_move_id
        invoice = debit_move_id.invoice_id
        account = invoice.account_id
        if invoice.type == 'out_invoice' and credit_move_id.account_id == account and debit_move_id.account_id == account:
            if not credit_move_id in invoice.mapped('provvigioni.credit_move_id'):
                payment = ndc = False
                if credit_move_id.payment_id:
                    payment = credit_move_id.payment_id
                elif credit_move_id.invoice_id and credit_move_id.invoice_id.type == 'out_refund':
                    ndc = credit_move_id.invoice_id

                to_currency = invoice.company_currency_id.with_context(date=invoice.date_invoice)
                from_currency = (invoice.currency_id and invoice.currency_id.with_context(date=invoice.date_invoice)) or to_currency
                digits_rounding_precision = to_currency.rounding
                importo_pagamento = abs(credit_move_id.debit - credit_move_id.credit)
                if getattr(invoice, 'split_payment', None):
                    totale_fattura = invoice.amount_untaxed_signed
                else:
                    totale_fattura = invoice.amount_total_company_signed
                if float_is_zero(totale_fattura, precision_rounding=digits_rounding_precision):
                    percentuale_pagamento = 1
                else:
                    percentuale_pagamento = importo_pagamento / totale_fattura

                for (agente, imponibile_provv, tot_provv) in self.get_provv_data(invoice):
                    da_pagare = tot_provv*percentuale_pagamento*(1-agente.perc_acnticipo_provv/100.)
                    if not float_is_zero(da_pagare, precision_rounding=digits_rounding_precision):
                        self.create({'invoice_id': invoice.id,
                                     'payment_id': payment.id if payment else False,
                                     'credit_move_id': credit_move_id.id,
                                     'agente': agente.id,
                                     'imponibile_provv': from_currency.compute(imponibile_provv, to_currency),
                                     'tot_provv': from_currency.compute(tot_provv, to_currency),
                                     'da_pagare': from_currency.compute(da_pagare, to_currency),
                                     'tipo_provv': 'pag'})
                        # se la compensazione della fattura avviene per una nota di credito creo anche le righe negative
                        if ndc:
                            self.create({'invoice_id': ndc.id,
                                         'credit_move_id': credit_move_id.id,
                                         'agente': agente.id,
                                         'imponibile_provv': -1*from_currency.compute(imponibile_provv, to_currency),
                                         'tot_provv': -1*from_currency.compute(tot_provv, to_currency),
                                         'da_pagare': -1*from_currency.compute(da_pagare, to_currency),
                                         'tipo_provv': 'ndc'})
        return True

    def elimina_provvigione_da_pagamento(self, reconcile):
        for partial_reconcile in reconcile.partial_reconcile_ids:
            self.elimina_provvigione_da_pagamento_parziale(partial_reconcile)
        return True
    
    def elimina_provvigione_da_pagamento_parziale(self, reconcile):
        credit_move_id, debit_move_id = reconcile.credit_move_id, reconcile.debit_move_id
        invoice = debit_move_id.invoice_id
        if invoice.type == 'out_invoice':
            self.search([('credit_move_id','=',credit_move_id.id),('invoice_id','=',invoice.id)]).unlink()
            if credit_move_id.invoice_id and credit_move_id.invoice_id.type == 'out_refund':
                self.search([('credit_move_id','=',credit_move_id.id),('invoice_id','=',credit_move_id.invoice_id.id)]).unlink()
        return True
