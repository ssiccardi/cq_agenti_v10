# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    #finche il template ha una variante sola i campi sono uguali, altrimenti sono slegati
    noprovvigioni = fields.Boolean('Escludi', compute='_compute_noprovvigioni', inverse='_set_noprovvigioni', store=True, default=False)
    percagente = fields.Float('Provvigione', compute='_compute_percagente', inverse='_set_percagente', store=True, default=0.0)

    @api.one
    @api.constrains('percagente')
    def percagente_constraint(self):
        if self.percagente < 0 or self.percagente > 100:
            raise ValidationError("La percentuale provvigione deve essere compresa tra 0 e 100.")
            
    @api.depends('product_variant_ids', 'product_variant_ids.noprovvigioni')
    def _compute_noprovvigioni(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.noprovvigioni = template.product_variant_ids.noprovvigioni

    @api.one
    def _set_noprovvigioni(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.noprovvigioni = self.noprovvigioni

    @api.depends('product_variant_ids', 'product_variant_ids.percagente')
    def _compute_percagente(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.percagente = template.product_variant_ids.percagente

    @api.one
    def _set_percagente(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.percagente = self.percagente

            
class ProductProduct(models.Model):
    _inherit = "product.product"
    
    noprovvigioni = fields.Boolean('Escludi', default=False)
    percagente = fields.Float('Provvigione', default=0.0)

    @api.one
    @api.constrains('percagente')
    def percagentevar_constraint(self):
        if self.percagente < 0 or self.percagente > 100:
            raise ValidationError("La percentuale provvigione deve essere compresa tra 0 e 100.")
    
    #se il template ha il flag escludi, vengono escluse tutte le varianti
    def getnoprovvigioni(self):
        return self.noprovvigioni or self.product_tmpl_id.noprovvigioni

    #se la variante ha percentuale zero, viene considerata la percentuale del template
    def getpercagente(self):
        return self.percagente or self.product_tmpl_id.percagente
            
class ProductCategory(models.Model):
    _inherit = "product.category"
    
    noprovvigioni = fields.Boolean('Escludi', default=False)
    percagente = fields.Float('Provvigione', default=0.0)

    @api.one
    @api.constrains('percagente')
    def percagentecat_constraint(self):
        if self.percagente < 0 or self.percagente > 100:
            raise ValidationError("La percentuale provvigione deve essere compresa tra 0 e 100.")
    
    #se una categoria padre ha il flag escludi, vengono escluse tutte le sottocategorie
    def getnoprovvigioni(self):
        noprovvigioni = False
        categ = self
        while categ and not noprovvigioni:
            noprovvigioni = categ.noprovvigioni
            categ = categ.parent_id
        return noprovvigioni

    #se una categoria ha percentuale zero, viene considerata la percentuale delle categoria padri
    def getpercagente(self):
        percagente = 0
        categ = self
        while categ and not percagente:
            percagente = categ.percagente
            categ = categ.parent_id
        return percagente
