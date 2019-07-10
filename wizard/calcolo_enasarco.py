# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime


class CalcoloEnasarco(models.TransientModel):

    _name = "calcolo.enasarco"

    anno = fields.Char('Anno', required=True, default=str(datetime.today().year))

    @api.one
    @api.constrains('anno')
    def check_anno(self):
        try:
            int(self.anno)
        except ValueError:
            raise ValidationError("Controllare l'anno inserito")

    @api.multi
    def calcola_enasarco(self):
        cr = self._cr
        tab_enasarco_pool=self.env['tabella.enasarco']
        conf_enasarco_pool=self.env['config.enasarco']

        anno_attuale=self.anno
        cmd="SELECT * FROM config_enasarco WHERE anno='%s' ORDER BY id DESC" %anno_attuale
        cr.execute(cmd)
        conf_enasarco=cr.dictfetchone()
        if not conf_enasarco:
            raise ValidationError("Effettuare la configurazione del calcolo Enasarco per l'anno %s!"%anno_attuale)


        partner_pool=self.env['res.partner']
        provvigioni_pool=self.env['cq.provvigioni']
        invoice_pool=self.env['account.invoice']
        mandato_history_pool=self.env['mandato.history']

        agenti=partner_pool.search([('agente','=',True),('supplier','=',True)])

        #cancello tutti i record di tabella_enasarco dell'anno in oggetto tranne quelle che hanno già una fattura collegata
        cmd1="DELETE FROM tabella_enasarco WHERE anno='%s' AND fattura_id is null" %anno_attuale
        cr.execute(cmd1)

        mesi_array=[]
        #se anno è uguale all'anno corrente, da gennaio al mese attuale, riempio la tabella mesi
        if anno_attuale == str(datetime.today().year):
            mese_attuale = datetime.today().month
            for i in range(1, mese_attuale+1):   #se vuoi anche il mese attuale -> range(1,month+1)
                mese_i = str(i).zfill(2)
                mesi_array.append(mese_i)
        #se anno è precedente a quello corrente, prendo tutti i mesi
        else:
            for i in range(1, 13):
                mese_i = str(i).zfill(2)
                mesi_array.append(mese_i)


        for agente in agenti:
            provvigioni=provvigioni_pool.search([('agente','=',agente.id)])

            provv_trim1=0.0
            provv_trim2=0.0
            provv_trim3=0.0
            provv_trim4=0.0
            provv_tot=0.0
            check_pluri=False
            for mese in mesi_array:
                #definisco tipo agente, mandato, trimestre

                if not agente.tipo_agente:
                    raise ValidationError("Specificare se l'agente %s e' persona fisica o societa'!"%agente.name)

                tipo_agente=agente.tipo_agente
                mandato=False

                sql="SELECT * FROM mandato_history WHERE agente_id=%s AND anno_start='%s' ORDER BY mese_start ASC" %(agente.id,anno_attuale)
                cr.execute(sql)
                mandato_righe=cr.dictfetchall()

                for riga in mandato_righe:
                    if not riga['mese_end'] and riga['mese_start']:
                        riga['mese_end'] = '12'

                    if riga['mese_start'] == mese:
                        mandato = str(riga['mandato'])
                        break
                    if riga['mese_end'] == mese:
                        mandato = str(riga['mandato'])
                        break
                    if riga['mese_start'] < mese and riga['mese_end'] > mese:
                        mandato = str(riga['mandato'])
                        break

                #se non è stato individuato il mandato del mese, ulteriore controllo sull'anno precedente, magari il mandato valido è ancora l'ultimo dell'anno precedente
                if not mandato:
                    sql2 = "SELECT * FROM mandato_history WHERE agente_id=%s" \
                        " AND anno_start = '%s' ORDER BY mese_start DESC" \
                        % (agente.id, int(anno_attuale)-1)
                    cr.execute(sql2)
                    mandato_righe2=cr.dictfetchall()
                    if mandato_righe2 and mandato_righe2[0]:
                        if not mandato_righe2[0]['mese_end']:
                            mandato=str(mandato_righe2[0]['mandato'])

                    if not mandato:
                        continue

                #raggruppo per mese prendendo la data di pagamento se c'è altrimenti la data della fattura associata
                provv_mese=0.0
                provvigioni_ids = []
                for provvigione in provvigioni:
                    if provvigione.data_pag:
                        if provvigione.data_pag[5:7] == mese and \
                           provvigione.data_pag[:4] == anno_attuale:
                            provv_mese += provvigione.da_pagare
                            provvigioni_ids.append(provvigione.id)
                    else:
                        invoice = provvigione.invoice_id
                        if invoice.date_invoice[5:7] == mese and \
                           invoice.date_invoice[:4] == anno_attuale:
                            provv_mese += provvigione.da_pagare
                            provvigioni_ids.append(provvigione.id)

                #ora divido per casi: se agente è società, provv_mese rimane invariato, altrimenti devo confrontare col plafond
                if tipo_agente=='persona':
                    if mese== '01':
                        if mandato=='M':
                             plafond=float(conf_enasarco['provv_max_mono'])
                             if provv_mese>plafond:
                                 provv_mese=plafond
                        else:
                             plafond=float(conf_enasarco['provv_max_pluri'])
                             if provv_mese>plafond:
                                 provv_mese=plafond
                    else:
                        if mandato=='M':
                             plafond=float(conf_enasarco['provv_max_mono'])
                             if plafond>provv_tot:
                                 if provv_mese>(plafond-provv_tot):
                                     provv_mese=plafond-provv_tot
                             else:
                                 provv_mese=0.0

                        else:
                             plafond=float(conf_enasarco['provv_max_pluri'])
                             if plafond>provv_tot:
                                 if provv_mese>(plafond-provv_tot):
                                     provv_mese=plafond-provv_tot
                             else:
                                 provv_mese=0.0

                provv_tot=provv_tot+provv_mese
                if mese <= '03':
                    trimestre=1
                if mese > '03' and mese <= '06':
                    trimestre=2
                if mese > '06' and mese <= '09':
                    trimestre=3
                if mese > '09':
                    trimestre=4

                enasarco_data={
                    'anno': anno_attuale,
                    'mese': str(mese),
                    'agente_id': agente.id,
                    'provvigione': provv_mese,
                    'trimestre': int(trimestre),
                    'tipo_agente': tipo_agente,
                    'mandato': mandato,
                    'provvigioni_ids': [(6,0,provvigioni_ids)],
                    'company_id': provvigioni and provvigioni[0].company_id.id or False,
                }

                #agente società di capitali
                if tipo_agente=='societa':
                    if mandato=='M':
                        enasarco_data['contributo_mese']=provv_mese*float(conf_enasarco['aliquota_soc_mono'])/100.0
                        enasarco_data['cont_agenzia']=provv_mese*float(conf_enasarco['carico_soc_mono_agen'])/100.0
                        enasarco_data['cont_mandante']=provv_mese*float(conf_enasarco['carico_soc_mono_mand'])/100.0
                        enasarco_data['quota_fattura']=provv_mese*float(conf_enasarco['carico_soc_mono_agen'])/100.0
                    else:
                        #check_pluri=True  ## non dovrebbe servire per le società
                        enasarco_data['contributo_mese']=provv_mese*float(conf_enasarco['aliquota_soc_pluri'])/100.
                        enasarco_data['cont_agenzia']=provv_mese*float(conf_enasarco['carico_soc_pluri_agen'])/100.0
                        enasarco_data['cont_mandante']=provv_mese*float(conf_enasarco['carico_soc_pluri_mand'])/100.0
                        enasarco_data['quota_fattura']=provv_mese*float(conf_enasarco['carico_soc_pluri_agen'])/100.0
                #agente persona fisica
                else:
                    if mandato=='M':
                        enasarco_data['contributo_mese']=provv_mese*float(conf_enasarco['aliquota_per_mono'])/100.0
                        enasarco_data['cont_agenzia']=provv_mese*float(conf_enasarco['carico_per_mono_agen'])/100.0
                        enasarco_data['cont_mandante']=provv_mese*float(conf_enasarco['carico_per_mono_mand'])/100.0
                        enasarco_data['quota_fattura']=provv_mese*float(conf_enasarco['carico_per_mono_agen'])/100.0
                    else:
                        check_pluri=True
                        enasarco_data['contributo_mese']=provv_mese*float(conf_enasarco['aliquota_per_pluri'])/100.
                        enasarco_data['cont_agenzia']=provv_mese*float(conf_enasarco['carico_per_pluri_agen'])/100.0
                        enasarco_data['cont_mandante']=provv_mese*float(conf_enasarco['carico_per_pluri_mand'])/100.0
                        enasarco_data['quota_fattura']=provv_mese*float(conf_enasarco['carico_per_pluri_agen'])/100.0

                ## se siamo alla fine di un trimestre, devo calcolare anche il contributo integrativo eventuale

                    if mese <= '03':
                        provv_trim1=provv_trim1+enasarco_data['contributo_mese']
                    if mese > '03' and mese <= '06':
                        provv_trim2=provv_trim2+enasarco_data['contributo_mese']
                    if mese > '06' and mese <= '09':
                        provv_trim3=provv_trim3+enasarco_data['contributo_mese']
                    if mese > '09':
                        provv_trim4=provv_trim4+enasarco_data['contributo_mese']

                    if mese == '03':
                        if not check_pluri:
                            cont_trim=provv_trim1-float(conf_enasarco['cont_min_mono'])
                            if cont_trim<0:
                                enasarco_data['integrazione'] =-cont_trim
                        else:
                            cont_trim=provv_trim1-float(conf_enasarco['cont_min_pluri'])
                            if cont_trim<0:
                                enasarco_data['integrazione'] =-cont_trim
                        check_pluri=False


                    if mese == '06':
                        if not check_pluri:
                            cont_trim=provv_trim2-float(conf_enasarco['cont_min_mono'])
                            if cont_trim<0:
                                enasarco_data['integrazione'] =-cont_trim
                        else:
                            cont_trim=provv_trim2-float(conf_enasarco['cont_min_pluri'])
                            if cont_trim<0:
                                enasarco_data['integrazione'] =-cont_trim
                        check_pluri=False

                    if mese == '09':
                        if not check_pluri:
                            cont_trim=provv_trim3-float(conf_enasarco['cont_min_mono'])
                            if cont_trim<0:
                                enasarco_data['integrazione'] =-cont_trim
                        else:
                            cont_trim=provv_trim3-float(conf_enasarco['cont_min_pluri'])
                            if cont_trim<0:
                                enasarco_data['integrazione'] =-cont_trim
                        check_pluri=False

                    if mese == '12':
                        if not check_pluri:
                            cont_trim=provv_trim4-float(conf_enasarco['cont_min_mono'])
                            if cont_trim<0:
                                enasarco_data['integrazione'] =-cont_trim
                        else:
                            cont_trim=provv_trim4-float(conf_enasarco['cont_min_pluri'])
                        if cont_trim<0:
                            enasarco_data['integrazione'] =-cont_trim
                        check_pluri=False

                #Controllo che non esista già una riga per il dato agente, anno, mese e con fattura. Se esiste, non la ri-creo
                existing_id=tab_enasarco_pool.search([('agente_id','=',agente.id),('mese','=',str(mese)),('anno','=',anno_attuale),('fattura_id','!=',False)])

                if not existing_id:
                    tab_enasarco_pool.create(enasarco_data)


        return self.env.ref('cq_agenti_v10.action_tabella_enasarco_list').read()[0]



