# Importación de IVA Argentino - Odoo 17.0

## Descripción

El módulo **Importación de IVA Argentino** permite importar facturas de proveedores a Odoo desde archivos CSV generados por aplicaciones contables o exportados desde el sitio web de AFIP. El sistema procesa automáticamente las facturas, detecta el tipo de impuesto correcto según los montos, y permite configurar cuentas contables y productos para diferentes tipos de líneas.

## Características principales

- **Importación masiva** de facturas de proveedores desde archivos CSV
- **Detección automática** de tasas de IVA (21%, 10.5%, 27%)
- **Validación y filtrado** de facturas duplicadas antes de la importación
- **Creación automática** de proveedores si no existen en el sistema
- **Soporte para facturas en moneda extranjera** (USD)
- **Gestión inteligente del IVA** (evita crear líneas de IVA duplicadas)
- **Posibilidad de selección manual** de cuentas contables 
- **Sugerencia de cuentas** basada en el historial del proveedor
- **Marcado automático** de facturas que requieren revisión manual
- **Manejo especial** para facturas tipo C y otros documentos específicos

## Requisitos técnicos

- Odoo 17.0
- Módulo de localización Argentina (`l10n_ar`)
- Configuración correcta de impuestos en el sistema

## Instalación

1. Copiar la carpeta `l10n_ar_iva_import` al directorio de addons de Odoo
2. Actualizar la lista de módulos desde el menú Aplicaciones
3. Buscar "Importación de IVA Argentino" e instalar el módulo
4. Reiniciar el servidor Odoo para asegurar el funcionamiento correcto

## Guía de uso

### 1. Formato del archivo CSV

El módulo espera un archivo CSV con el siguiente formato:

| Col | Nombre | Descripción | Ejemplo |
|-----|--------|-------------|---------|
| 0 | Fecha | Fecha de la factura (YYYY-MM-DD) | 2025-04-11 |
| 1 | Tipo | Código del tipo de comprobante | 1 |
| 2 | Punto de Venta | Número de punto de venta | 0001 |
| 3 | Número | Número de comprobante | 00012345 |
| 4 | Número Hasta | Número final (para rangos) | 00012345 |
| 5 | Código de Autorización | CAE o CAI | 12345678901234 |
| 6 | Tipo Doc. Emisor | Tipo de documento del emisor | 80 |
| 7 | CUIT | CUIT del proveedor | 30123456789 |
| 8 | Razón Social | Nombre del proveedor | PROVEEDOR S.A. |
| 9 | Tipo de Cambio | Cambio para moneda extranjera | 1150.5 |
| 10 | Moneda | Código de moneda (PES/DOL) | PES |
| 11 | Imp. Neto Gravado | Monto gravado por IVA | 10000.00 |
| 12 | Imp. Neto No Gravado | Monto no gravado por IVA | 5000.00 |
| 13 | Op. Exentas | Monto operaciones exentas | 0.00 |
| 14 | Otros Tributos | Percepciones, otros impuestos | 800.00 |
| 15 | IVA | Monto del IVA | 2100.00 |
| 16 | Imp. Total | Monto total de la factura | 12900.00 |

### 2. Configuración inicial

1. Ir a **Contabilidad > Configuración > Importación de IVA**
2. Crear un nuevo registro con:
   - **Nombre**: Identificador para la importación
   - **Diario de Compras**: Seleccione el diario donde se crearán las facturas
   - **Archivo**: Seleccione el archivo CSV a importar
   - **Separador**: Indique el separador del archivo (por defecto `;`)
   - **Sugerir cuentas basado en historial**: Activar para usar cuentas históricas del proveedor
   - **Selección manual de cuentas**: Activar para seleccionar manualmente las cuentas
   - **Cuentas/Productos por defecto**: Configurar cuentas para cada tipo de línea

### 3. Importación

1. Después de crear el registro de importación, haga clic en **Procesar Archivo**
2. El sistema mostrará:
   - Facturas existentes (ya en sistema)
   - Facturas nuevas para importar

3. Si hay facturas nuevas, puede:
   - Ver los detalles de las facturas duplicadas
   - Continuar con la importación de facturas nuevas
   - Cancelar la operación

4. Si ha activado "Selección manual de cuentas", se le pedirá:
   - Seleccionar la cuenta contable para cada tipo de línea (gravado, no gravado, otros tributos)
   - Estas cuentas se mostrarán solo si el monto correspondiente es mayor a cero

5. Una vez completada la importación, verá un resumen con:
   - Número de facturas importadas
   - Número de proveedores creados

### 4. Revisión de facturas

Las facturas creadas por la importación:
- Se marcarán con "Requiere revisión" si contienen "Otros Tributos"
- Tendrán el mismo número y tipo de comprobante que en el archivo CSV
- Tendrán el proveedor correspondiente al CUIT del archivo
- En facturas USD, se agregará una nota con el tipo de cambio original

## Características avanzadas

### Sugerencia de cuentas

El módulo puede sugerir cuentas contables basado en facturas anteriores del mismo proveedor. Esta funcionalidad:
- Analiza las últimas 10 facturas del proveedor
- Identifica cuentas utilizadas para líneas gravadas, no gravadas y otros tributos
- Sugiere la cuenta más frecuente para cada tipo de línea

### Manejo de moneda extranjera

Para facturas en USD (marcadas como "DOL" en la columna 10):
- El sistema establece la moneda USD automáticamente
- Utiliza el tipo de cambio del archivo (columna 9)
- Agrega una nota informativa en el chat de la factura

### Validación de IVA

Para cada factura importada:
- Se verifica que el IVA calculado por Odoo coincida con el valor en el archivo CSV
- Se agrega una advertencia en el chat si hay discrepancias significativas
- Se eliminan automáticamente líneas duplicadas de IVA

## Resolución de problemas comunes

### Error: "Separador erróneo"

**Problema**: El sistema muestra el error "Separador erróneo, verifique el archivo y cambielo de ser necesario"

**Solución**:
- Verificar que el separador configurado coincida con el usado en el archivo CSV
- Comprobar que no haya caracteres especiales o comillas que interfieran
- Intentar con separador `;` o `,` según el formato del archivo

### Error: Referencias de impuestos no encontradas

**Problema**: Error "External ID not found" durante la importación

**Solución**:
- Verificar que el módulo `l10n_ar` esté instalado correctamente
- Comprobar que los impuestos para compras existan en el sistema
- Asegurarse de que la compañía tenga correctamente configurados los impuestos de IVA

### Facturas marcadas incorrectamente para revisión

**Problema**: Todas las facturas se marcan como "Requiere revisión" o ninguna se marca

**Solución**:
- Verificar que la columna 14 (Otros Tributos) tenga valores correctos
- Comprobar que los valores del CSV no tengan formatos incorrectos
- Reiniciar el servidor Odoo y limpiar la caché del navegador

## Licencia

Este módulo está licenciado bajo AGPL-3.0

---

## Créditos

Desarrollado por: Zanel Dev

Para soporte o consultas: [contactar al desarrollador](mailto:desarrollador@example.com)

---

*Documentación actualizada: Abril 2025*
