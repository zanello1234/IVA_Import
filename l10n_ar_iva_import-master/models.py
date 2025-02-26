# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unicodedata import name
from dateutil.relativedelta import relativedelta
from datetime import date,datetime,timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
import logging

import base64
import csv
from io import StringIO

_logger = logging.getLogger(__name__)

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

    def _prepare_invoice_line(self, data=[None, 0, 0, 0, 0], sign=1):
        def debug_tax_calculation(base, tax):
            if base:
                rate = (tax / base) * 100
                return f"Base: {base}, IVA: {tax}, Tasa calculada: {rate:.2f}%"
            return f"Base: {base}, IVA: {tax}"

        try:
            # Obtener los valores
            product, base_amount, total_amt, tax_amount = data[:4]
            base_amount = float(base_amount or 0)
            tax_amount = float(tax_amount or 0)

            # Caso 1: Sin impuestos
            if tax_amount == 0 and total_amt == 0:
                tax_ids = [(6, 0, [])]
            
            # Caso 2: Solo base imponible
            elif tax_amount == 0 and total_amt != 0:
                tax_id = self.env['account.tax'].search([
                    '|', '|',
                    ('name', 'ilike', 'IVA 21'),
                    ('amount', '=', 21),
                    ('description', 'ilike', '21%'),
                    ('type_tax_use', '=', 'purchase'),
                    ('active', '=', True)
                ], limit=1)
                
                if not tax_id:
                    raise ValidationError(
                        f'Error buscando IVA 21%\n'
                        f'{debug_tax_calculation(base_amount, tax_amount)}'
                    )
                tax_ids = [(6, 0, tax_id.ids)]
            
            # Caso 3: Con impuesto
            else:
                if base_amount:
                    rate = (tax_amount / base_amount) * 100
                    
                    # Determinar el impuesto basado en la tasa calculada
                    if rate >= 26:
                        tax_id = self.env['account.tax'].search([
                            '|', '|',
                            ('name', 'ilike', 'IVA 27'),
                            ('amount', '=', 27),
                            ('description', 'ilike', '27%'),
                            ('type_tax_use', '=', 'purchase'),
                            ('active', '=', True)
                        ], limit=1)
                    elif rate <= 11:
                        tax_id = self.env['account.tax'].search([
                            '|', '|',
                            ('name', 'ilike', 'IVA 10.5'),
                            ('amount', '=', 10.5),
                            ('description', 'ilike', '10.5%'),
                            ('type_tax_use', '=', 'purchase'),
                            ('active', '=', True)
                        ], limit=1)
                    else:
                        tax_id = self.env['account.tax'].search([
                            '|', '|',
                            ('name', 'ilike', 'IVA 21'),
                            ('amount', '=', 21),
                            ('description', 'ilike', '21%'),
                            ('type_tax_use', '=', 'purchase'),
                            ('active', '=', True)
                        ], limit=1)
                    
                    if not tax_id:
                        raise ValidationError(
                            f'Error buscando IVA correspondiente\n'
                            f'{debug_tax_calculation(base_amount, tax_amount)}'
                        )
                    tax_ids = [(6, 0, tax_id.ids)]
                else:
                    tax_ids = [(6, 0, [])]

            return {
                'product_id': product and product.id or None,
                'quantity': 1 * sign,
                'discount': 0,
                'price_unit': base_amount,
                'tax_ids': tax_ids,
                'name': product and product.display_name or '',
                'product_uom_id': product and product.uom_id.id or None,
            }
        except Exception as e:
            raise ValidationError(f"Error en la preparación de la línea de factura: {str(e)}")

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
        self.ensure_one()
        if not self.iva_file:
            raise ValidationError('No hay archivo cargado')
        
        try:
            csv_data = base64.b64decode(self.iva_file)
            data_file = StringIO(csv_data.decode("utf-8"))
            data_file.seek(0)
            
            # Usar el separador configurado o ; por defecto
            separator = self.separator or ';'
            csv_reader = csv.reader(data_file, delimiter=separator)
            
            # Procesar cada línea del archivo
            for i, items in enumerate(csv_reader):
                if i == 0:  # Saltar encabezado
                    continue
                    
                # Procesar CUIT y tipo de identificación
                cuit = items[7]
                razonsocial = items[8]
                partner_id = self.env['res.partner'].search([('vat', '=', cuit)], limit=1)
                
                identification_type_id = self.env.ref(
                    'l10n_ar.it_cuit' if items[6] == 'CUIT' else 'l10n_ar.it_Sigd'
                ).id
                
                # Crear partner si no existe
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
                
                # Determinar tipo de movimiento
                move_type = 'in_refund' if items[1] in ['3', '8', '13'] else 'in_invoice'
                
                # Preparar número de documento
                document_number = f"{items[2].zfill(5)}-{items[3].zfill(8)}"
                doc_type = items[1].split(' ')[0]
                doc_type_id = self.env['l10n_latam.document.type'].search([('code', '=', doc_type)])
                
                # Limpiar y convertir montos
                for idx in range(11, 17):
                    items[idx] = items[idx].replace(',', '.')
                
                # Preparar líneas de factura
                if items[11]:
                    invoice_line_ids = self._prepare_invoice_lines(
                        float(items[11]), float(items[12]), float(items[13]),
                        float(items[15]), float(items[16])
                    )
                else:
                    invoice_line_ids = self._prepare_invoice_lines(0, 0, 0, 0, float(items[16]))
                
                # Preparar valores del movimiento
                vals_move = {
                    'move_type': move_type,
                    'partner_id': partner_id.id,
                    'invoice_date': items[0],
                    'l10n_latam_document_number': document_number,
                    'account_iva_file_id': self.id,
                    'l10n_latam_document_type_id': doc_type_id.id,
                    'invoice_line_ids': invoice_line_ids,
                    'file_amount': float(items[16]),
                }
                
                # Buscar si ya existe el documento
                domain = [
                    ('move_type', '=', move_type),
                    ('name', 'ilike', document_number),
                    ('partner_id', '=', partner_id.id)
                ]
                existing_move = self.env['account.move'].search(domain)
                
                if not existing_move:
                    self.env['account.move'].create(vals_move)
                else:
                    _logger.info(f"Documento ya existente: {document_number} para partner {partner_id.name}")
                    
            # Marcar como procesado
            self.write({'state': 'done'})
            return True
            
        except Exception as e:
            raise ValidationError(f"Error procesando el archivo: {str(e)}")
