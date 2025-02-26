# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unicodedata import name
from dateutil.relativedelta import relativedelta
from datetime import date,datetime,timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import ValidationError

import base64
import csv
from io import StringIO

class AccountMove(models.Model):
    _inherit = 'account.move'

    account_iva_file_id = fields.Many2one('account.iva.file',string='Archivo de IVA')
    file_amount = fields.Float('Monto Archivo IVA')

class ResPartner(models.Model):
    _inherit = 'res.partner'

    account_iva_file_id = fields.Many2one('account.iva.file',string='Archivo de IVA')

class AccountIvaFile(models.Model):
    _name = "account.iva.file"
    _inherit = ['mail.thread','mail.activity.mixin']  
    _description = "Importacion IVA"

    name            = fields.Char('Nombre',tracking=True)
    product_vat_id      = fields.Many2one('product.product',string='Producto IVA',states={"draft": [("readonly", False)]})
    product_novat_id      = fields.Many2one('product.product',string='Producto No Gravado',states={"draft": [("readonly", False)]})
    product_exempt_id      = fields.Many2one('product.product',string='Producto Exento',states={"draft": [("readonly", False)]})
    product_other_taxes_id      = fields.Many2one('product.product',string='Producto Otros Tributos',states={"draft": [("readonly", False)]})
    date   = fields.Date('Fecha Ingreso',default=fields.Date.today(),readonly=True)
    iva_file    = fields.Binary('Archivo',tracking=True,
        states={"draft": [("readonly", False)]})
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("done", "Procesado"),
        ],
        default="draft",
        tracking=True
    )
    partner_ids     = fields.One2many(comodel_name="res.partner", inverse_name="account_iva_file_id",string='Proveedores creados',readonly=True)
    move_ids    = fields.One2many(comodel_name="account.move", inverse_name="account_iva_file_id",string='Facturas creadas',readonly=True)
    separator = fields.Char('Separador',default=';')

    def _prepare_invoice_line(self, data = [None,0,0,0,0], sign = 1):
        if data[2] == 0 and data[3] == 0:
            tax_ids = [(6,0,[])]
        elif data[3] == 0 and data[2] != 0:
            tax_id = self.env.ref('l10n_ar.1_ri_tax_vat_21_compras')
            tax_ids = [(6,0,tax_id.ids)]
        else:
            #if data[1] == 6008.39:
            #    raise ValidationError(str(data))
            if (data[1] and (data[3] / data[1]) > 0.26):
                tax_id = self.env.ref('l10n_ar.1_ri_tax_vat_27_compras')
            elif (data[1] and (data[3] / data[1]) < 0.11):
                tax_id = self.env.ref('l10n_ar.1_ri_tax_vat_10_compras')
            else:
                tax_id = self.env.ref('l10n_ar.1_ri_tax_vat_21_compras')
            tax_ids = [(6,0,tax_id.ids)]

        return {
            'product_id': data[0] and data[0].id or None,
            'quantity': 1 * sign,
            'discount': 0,
            'price_unit': data[1],
            'tax_ids': tax_ids,
            'name': data[0] and data[0].display_name or '',
            'product_uom_id': data[0] and data[0].uom_id.id or None,
        }

    def _prepare_invoice_lines(self, monto_neto = 0, monto_no_gravado = 0, monto_exento = 0, monto_iva = 0, monto_total = 0):
        invoice_lines = []
        if monto_neto != 0 or monto_exento != 0 or monto_no_gravado != 0:
            data_items = [[self.product_vat_id,monto_neto,monto_total,monto_iva],[self.product_novat_id,monto_no_gravado,0,0],[self.product_exempt_id,monto_exento,0,0]]
        else:
            data_items = [[self.product_vat_id,monto_total,0,0]]
        for product,amount,total_amt,monto_iva in data_items:
            if amount > 0:
                invoice_lines.append((0, None, self._prepare_invoice_line([product,amount,total_amt,monto_iva],1)))

        return invoice_lines

    def btn_process_file(self):
        self.ensure_one()           #Se asegura que el recordset sea de un solo registro
        if not self.iva_file:
            raise ValidationError('No hay archivo cargado')
        csv_data = base64.b64decode(self.iva_file)
        data_file = StringIO(csv_data.decode("utf-8"))
        data_file.seek(0)
        file_reader = []
        if not self.separator:
            csv_reader = csv.reader(data_file, delimiter=';')
        else:
            csv_reader = csv.reader(data_file, delimiter=self.separator)
        #file_reader.extend(csv_reader)
        for i,items in enumerate(csv_reader):
            if i == 0:
                continue
            cuit = items[7]
            razonsocial = items[8]
            partner_id = self.env['res.partner'].search([('vat','=',cuit)],limit=1)
            if items[6] == 'CUIT':
                identification_type_id = self.env.ref('l10n_ar.it_cuit').id
            else:
                identification_type_id = self.env.ref('l10n_ar.it_Sigd').id
            if not partner_id:
                vals_partner = {
                        'name': razonsocial,
                        'company_type': 'company',
                        'l10n_latam_identification_type_id': identification_type_id,
                        'l10n_ar_afip_responsibility_type_id': self.env.ref('l10n_ar.res_IVARI').id,
                        'supplier_rank': 1,
                        'account_iva_file_id': self.id,
                        }
                partner_id = self.env['res.partner'].create(vals_partner)
                partner_id.write({'vat': cuit})
            if items[1] in ['3','8','13']:
                move_type = 'in_refund'
            else:
                move_type = 'in_invoice'
            document_number = '%s-%s'%(items[2].zfill(5),items[3].zfill(8))
            doc_type = items[1].split(' ')
            doc_type_id = self.env['l10n_latam.document.type'].search([('code','=',doc_type[0])])
            items[11] = items[11].replace(',','.')
            items[12] = items[12].replace(',','.')
            items[13] = items[13].replace(',','.')
            items[14] = items[14].replace(',','.')
            items[15] = items[15].replace(',','.')
            items[16] = items[16].replace(',','.')
            if items[11] != '':
                invoice_line_ids = self._prepare_invoice_lines(float(items[11]),float(items[12]),float(items[13]),float(items[15]),float(items[16]))
            else:
                invoice_line_ids = self._prepare_invoice_lines(0,0,0,0,float(items[16]))
            vals_move = {
                    'move_type': move_type,
                    'partner_id': partner_id.id,
                    #'invoice_date': datetime.strptime(items[0], "%d/%m/%Y"),
                    'invoice_date': items[0],
                    'l10n_latam_document_number': document_number,
                    'account_iva_file_id': self.id,
                    'l10n_latam_document_type_id': doc_type_id.id,
                    'invoice_line_ids': invoice_line_ids,
                    'file_amount': float(items[16]),
                    }
            domain = [('move_type','=',move_type),('name','ilike',document_number),('partner_id','=',partner_id.id)]
            move_id = self.env['account.move'].search(domain)
            if not move_id:
                move_id = self.env['account.move'].create(vals_move)
            else:
                import pdb;pdb.set_trace()
