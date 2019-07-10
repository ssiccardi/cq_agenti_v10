# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, date
import base64
from cStringIO import StringIO

try:
    import xlwt
except ImportError:
    xlwt = None

class CQEstraiProvvigioni(models.TransientModel):
    _name = 'cq.estrai.provvigioni'

    def _get_data_ult_pag_provv(self):
        return self.env['cq.provvigioni'].search([('pagato','=',True)], order="data_pag_pro desc", limit=1).data_pag_pro
   
    data = fields.Binary(readonly=True)
    state = fields.Selection([('choose','Choose'),('get','Get')], default='choose')
    name = fields.Char('Nome file esportato', size=32, readonly=True)
    fino_al = fields.Date('Fino al', required=True, default=fields.Date.today())
    data_ultimo_pag_provv = fields.Date('Data ultimo pagamento provvigioni', readonly=True, default=_get_data_ult_pag_provv,
                                        help="Data in cui è stata pagata l'ultima provvigione")
   
    def write_header(self, worksheet, head_style, total_style, agente):
        worksheet.write(0, 0, agente, total_style)
        worksheet.write(1, 0, 'Fattura', head_style)
        worksheet.col(0).width = 8000
        worksheet.write(1, 1, 'Cliente', head_style)
        worksheet.col(1).width = 10000
        worksheet.write(1, 2, 'Data Fattura', head_style)
        worksheet.col(2).width = 3000
        worksheet.write(1, 3, 'Termine di Pagamento', head_style)
        worksheet.col(3).width = 5000
        worksheet.write(1, 4, 'Totale Fattura', head_style)
        worksheet.col(4).width = 4000
        worksheet.write(1, 5, 'Imponibile per Provvigione', head_style)
        worksheet.col(5).width = 6000
        worksheet.write(1, 6, 'Totale Provvigione', head_style)
        worksheet.col(6).width = 5500
        worksheet.write(1, 7, 'Tipo Provvigione', head_style)
        worksheet.col(7).width = 4000
        worksheet.write(1, 8, 'Pagamento', head_style)
        worksheet.col(8).width = 7000
        worksheet.write(1, 9, 'Data Pagamento', head_style)
        worksheet.col(9).width = 3800
        worksheet.write(1, 10, 'Importo Pagamento', head_style)
        worksheet.col(10).width = 5000
        worksheet.write(1, 11, 'Provvigione Maturata', head_style)
        worksheet.col(11).width = 5000
        return 2

    def write_invoice(self, worksheet, provv, i, base_style, currency_style, date_style):
        worksheet.write(i, 0, provv.invoice_id.display_name, base_style)
        worksheet.write(i, 1, provv.cliente.display_name, base_style)
        worksheet.write(i, 2, datetime.strptime(provv.date_invoice, DEFAULT_SERVER_DATE_FORMAT), date_style)
        worksheet.write(i, 3, provv.tipo_pagamento.display_name, base_style)
        worksheet.write(i, 4, provv.tot_fatt, currency_style)
        worksheet.write(i, 5, provv.imponibile_provv, currency_style)
        worksheet.write(i, 6, provv.tot_provv, currency_style)

    def write_provv(self, worksheet, provv, i, base_style, currency_style, date_style):
        selection_vals = dict(self.env['cq.provvigioni']._fields['tipo_provv']._description_selection(self.env))
        worksheet.write(i, 7, selection_vals[provv.tipo_provv], base_style)
        if provv.payment_id:
            worksheet.write(i, 8, provv.payment_id.display_name, base_style)
            worksheet.write(i, 9, datetime.strptime(provv.data_pag, DEFAULT_SERVER_DATE_FORMAT), date_style)
            worksheet.write(i, 10, provv.importo_pag, currency_style)
        worksheet.write(i, 11, provv.da_pagare, currency_style)

    def get_report(self):
        if not xlwt:
            raise ValidationError("Per questa funzionalità è necessario installare la libreria python xlwt")
        user = self.env.user
        company_id = user.company_id
        round_cur = company_id.currency_id.decimal_places
        fino_al = self.fino_al
        filename = 'provvigioni_%s.xls'%datetime.strftime(datetime.strptime(fino_al, DEFAULT_SERVER_DATE_FORMAT), '%d-%m-%Y')
        file_data = ''

        head_style = xlwt.easyxf('font: bold on;align: wrap yes;pattern: pattern solid, fore_color 27;')
        base_style = xlwt.easyxf('align: wrap yes')
        currency_style = xlwt.easyxf(num_format_str=u"[$€-410]#,##0." + "0"*round_cur)
        date_style = xlwt.easyxf(num_format_str='dd/mm/yyyy')
        total_style = xlwt.easyxf('font: bold on;align: wrap yes;')
        currency_style_total = xlwt.easyxf('font: bold on;align: wrap yes;', num_format_str=u"[$€-410]#,##0." + "0"*round_cur)

        workbook = xlwt.Workbook(encoding='utf8')
        agente = False
        for provv in self.env['cq.provvigioni'].search([('pagato','=',False)], order="agente asc, invoice_id asc, payment_id asc"):
            if provv.tipo_provv in ('fatt','ndc') and provv.date_invoice > fino_al:
                continue
            elif provv.tipo_provv == 'pag' and provv.data_pag and provv.data_pag > fino_al:
                continue
            
            if agente != provv.agente:
                if agente != False:
                    worksheet.write(i, 10, 'Totale', total_style)
                    worksheet.write(i, 11, totagente, currency_style_total)
                agente = provv.agente
                worksheet = workbook.add_sheet(agente.name)
                totagente = 0.
                fattura = False
                i = self.write_header(worksheet, head_style, total_style, agente.name)
            if fattura != provv.invoice_id:
                fattura = provv.invoice_id
                self.write_invoice(worksheet, provv, i, base_style, currency_style, date_style)
            self.write_provv(worksheet, provv, i, base_style, currency_style, date_style)
            totagente += provv.da_pagare
            i += 1
        if agente != False:
            worksheet.write(i, 10, 'Totale', total_style)
            worksheet.write(i, 11, totagente, currency_style_total)
            action_name = 'Esportazione Completata'
            fp = StringIO()
            workbook.save(fp)
            fp.seek(0)
            file_data = fp.read()
            fp.close()
        else:
            action_name = 'Nessuna Provvigione'
        self.write({'state':'get', 'data': base64.encodestring(file_data), 'name': filename})
        
        return {
            'type': 'ir.actions.act_window',
            'name': action_name,
            'res_model': 'cq.estrai.provvigioni',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new',
        }
