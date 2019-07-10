# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, date


class FatturaAgente(models.TransientModel):

    def _get_journal(self):
        journal_obj = self.env['account.journal']
        journal_type = self._get_journal_type()
        journals = journal_obj.search([('type', '=', journal_type)])
        return journals and journals.ids[0] or False
    
    def _get_journal_type(self):
        return 'purchase'

    _name = "fattura.agente"
    _description = "Fattura Agente"

    journal_id = fields.Many2one('account.journal', 'Sezionale', required=True, default=_get_journal)
    journal_type = fields.Selection([('purchase_refund', 'Refund Purchase'), ('purchase', 'Create Supplier Invoice'), 
                                     ('sale_refund', 'Refund Sale'), ('sale', 'Create Customer Invoice')], 'Tipo Sezionale', readonly=True, default=_get_journal_type)
    invoice_date = fields.Date('Data Fattura', default=datetime.today())

    @api.multi
    def create_fattura_agente(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])

        invoice_pool=self.env['account.invoice']
        tab_enasarco_pool=self.env['tabella.enasarco']
        product_pool=self.env['product.product']
        campo_prezzo=self.env['config.enasarco'].search([]).campo_prezzo

        #prodotti fissi in fattura       
        prod_enasarco=self.env.ref('cq_agenti_v10.prodotto_quota_enasarco')
        if prod_enasarco:
            prod_enasarco = product_pool.browse(prod_enasarco.id)
        else:
            prod_enasarco = product_pool.search([('default_code','=','QtEnsrc')], limit=1)
        prod_fisso=self.env.ref('cq_agenti_v10.prodotto_fisso_agente')
        if prod_fisso:
            prod_fisso = product_pool.browse(prod_fisso.id)
        else:
            prod_fisso = product_pool.search([('default_code','=','FssAgnt')], limit=1)
        prod_prov=self.env.ref('cq_agenti_v10.prodotto_provvigioni_agente')
        if prod_prov:
            prod_prov = product_pool.browse(prod_prov.id)
        else:
            prod_prov = product_pool.search([('default_code','=','PrvvgnAgnt')], limit=1)
        
        if not prod_enasarco or not prod_fisso or not prod_prov:
            raise ValidationError("Bisogna creare i prodotti 'Quota Enasarco', 'Fisso Agente', 'Provvigioni Agente'!")
        
        enasarco_prods = prod_enasarco | prod_fisso | prod_prov
        
        invoice_data = {        
            'journal_id': self.journal_id.id,
            'type':'in_invoice',
            'withholding_tax':True,
            'date_invoice': self.invoice_date,
        }

        enasarco_lines = tab_enasarco_pool.browse(active_ids)

        ###controllo che sia lo stesso agente
        partner=enasarco_lines[0].agente_id
        for riga_enasarco in enasarco_lines:
            if riga_enasarco.agente_id != partner:
                raise ValidationError("L'agente deve essere lo stesso!")
        
        fp = partner.property_account_position_id
        invoice_data['partner_id']=partner.id
        invoice_data['account_id']=partner.property_account_payable_id.id               
        invoice_data['fiscal_position_id']=fp.id
        invoice_data['payment_term_id']=partner.property_supplier_payment_term_id.id
        invoice_data['partner_bank_id']=partner.bank_ids and partner.bank_ids.ids[0] or False

        #calcolo i totali quote enasarco, provvigioni, fisso mensile, ritenuta d'acconto
        tot_quota_enasarco=0.0
        tot_provv=0.0
        tot_fisso=0.0
        mesi=''
        for riga_enasarco in enasarco_lines:
            tot_provv=tot_provv+riga_enasarco.provvigione
            tot_fisso=tot_fisso+partner.fisso_mensile
            tot_quota_enasarco=tot_quota_enasarco+riga_enasarco.quota_fattura
            month=str(riga_enasarco.mese)
            mesi += ' - '+month+'/'+str(riga_enasarco.anno)
        invoice_lines = []
        for prod in enasarco_prods:
            invoice_line_data={
                'partner_id': partner.id,
                'invoice_line_tax_wt_ids': fp and [(6,0,fp.withholding_tax_ids.mapped('id'))] or []
            }
            invoice_line_data['product_id']=prod.id
            invoice_line_data['name']=str(prod.name)+mesi
            invoice_line_data['quantity']=1.0
            invoice_line_data['uom_id']=prod.uom_id.id
            invoice_line_data['account_id']=prod.property_account_expense_id.id
            invoice_line_data['invoice_line_tax_ids'] = prod.supplier_taxes_id and [(6, 0, prod.supplier_taxes_id.ids)] or []
                     
            if prod==prod_enasarco:                    
                invoice_line_data[campo_prezzo]=-tot_quota_enasarco
            if prod==prod_prov:                       
                invoice_line_data[campo_prezzo]=tot_provv                        
            if prod==prod_fisso:                        
                invoice_line_data[campo_prezzo]=tot_fisso                         
            
            invoice_lines.append(invoice_line_data)
        invoice_data['invoice_line_ids']=map(lambda x: (0,0,x), invoice_lines)

        #creazione unica fattura
        new_invoice=invoice_pool.create(invoice_data)  
        enasarco_lines.write({'fattura_id':new_invoice.id})

        #aggiunta ritenute
        new_invoice.withholding_tax_line_ids = map(lambda x: (0,0,x), new_invoice.get_wt_taxes_values().values())

        new_invoice.compute_taxes()

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'view_id': self.env.ref('account.invoice_supplier_form').id,
            'type': 'ir.actions.act_window',
            'res_id': new_invoice.id
        }

