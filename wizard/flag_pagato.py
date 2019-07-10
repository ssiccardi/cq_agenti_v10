# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ActionFlagPagamenti(models.TransientModel):
    _name = "action.flag.pagamenti"
    _description = "Segna come pagate le provvigioni"
    
    pay_date = fields.Date(string='Data pagamento', default=fields.Date.today())
        
    @api.multi
    def action_flag_pagati(self):
        context = self._context or {}
        provv_ids = context.get('active_ids', False)
        if not provv_ids:
            raise ValidationError('Selezionare almeno una riga')
        
        self.env['cq.provvigioni'].browse(provv_ids).write({'pagato': True, 'data_pag_pro': self.pay_date})

        return {'type': 'ir.actions.act_window_close'}  
