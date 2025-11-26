#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para crear archivo Excel con todos los requisitos de Google Merchant Center
Genera un archivo XLSX con todos los campos categorizados por prioridad
"""

import pandas as pd
import os
from datetime import datetime

def create_google_merchant_requirements_excel():
    """Crea archivo Excel con todos los requisitos de Google Merchant Center"""
    
    # Datos de campos obligatorios (CRÍTICOS)
    campos_criticos = [
        {
            'Campo': 'id',
            'Categoría': 'CRÍTICO',
            'Descripción': 'Identificador único del producto',
            'Formato': 'String (máx 50 chars)',
            'Ejemplo': 'odoo_12345',
            'Estado en Odoo': '✅ Implementado',
            'Campo Odoo': 'id',
            'Prioridad': 1,
            'Acción Requerida': 'Ninguna - Ya implementado',
            'Impacto': 'Sin este campo el producto NO se indexa'
        },
        {
            'Campo': 'title',
            'Categoría': 'CRÍTICO',
            'Descripción': 'Nombre del producto',
            'Formato': 'String (máx 150 chars)',
            'Ejemplo': 'Camiseta Azul Algodón',
            'Estado en Odoo': '✅ Implementado',
            'Campo Odoo': 'name',
            'Prioridad': 1,
            'Acción Requerida': 'Ninguna - Ya implementado',
            'Impacto': 'Sin este campo el producto NO se indexa'
        },
        {
            'Campo': 'description',
            'Categoría': 'CRÍTICO',
            'Descripción': 'Descripción detallada del producto',
            'Formato': 'String (500+ chars recomendado)',
            'Ejemplo': 'Camiseta 100% algodón con cuello redondo...',
            'Estado en Odoo': '✅ Implementado',
            'Campo Odoo': 'website_description',
            'Prioridad': 1,
            'Acción Requerida': 'Ninguna - Ya implementado',
            'Impacto': 'Sin este campo el producto NO se indexa'
        },
        {
            'Campo': 'link',
            'Categoría': 'CRÍTICO',
            'Descripción': 'URL de la página del producto',
            'Formato': 'URL válida con https://',
            'Ejemplo': 'https://klavier.es/product/123',
            'Estado en Odoo': '✅ Implementado',
            'Campo Odoo': 'Construido automáticamente',
            'Prioridad': 1,
            'Acción Requerida': 'Ninguna - Ya implementado',
            'Impacto': 'Sin este campo el producto NO se indexa'
        },
        {
            'Campo': 'image_link',
            'Categoría': 'CRÍTICO',
            'Descripción': 'URL de la imagen principal',
            'Formato': 'URL válida de imagen',
            'Ejemplo': 'http://localhost:8081/product_123.jpg',
            'Estado en Odoo': '✅ Implementado',
            'Campo Odoo': 'image_1920 (convertido a URL)',
            'Prioridad': 1,
            'Acción Requerida': 'Ninguna - Ya implementado',
            'Impacto': 'Sin este campo el producto NO se indexa'
        },
        {
            'Campo': 'availability',
            'Categoría': 'CRÍTICO',
            'Descripción': 'Estado de disponibilidad del producto',
            'Formato': 'in stock | out of stock | preorder',
            'Ejemplo': 'in stock',
            'Estado en Odoo': '✅ Implementado',
            'Campo Odoo': 'Fijo: "in stock"',
            'Prioridad': 1,
            'Acción Requerida': 'Mejorar: mapear desde qty_available',
            'Impacto': 'Sin este campo el producto NO se indexa'
        },
        {
            'Campo': 'price',
            'Categoría': 'CRÍTICO',
            'Descripción': 'Precio del producto',
            'Formato': '{amount_micros, currency_code}',
            'Ejemplo': '{29990000, "EUR"}',
            'Estado en Odoo': '✅ Implementado',
            'Campo Odoo': 'list_price',
            'Prioridad': 1,
            'Acción Requerida': 'Ninguna - Ya implementado',
            'Impacto': 'Sin este campo el producto NO se indexa'
        },
        {
            'Campo': 'condition',
            'Categoría': 'CRÍTICO',
            'Descripción': 'Estado del producto',
            'Formato': 'new | used | refurbished',
            'Ejemplo': 'new',
            'Estado en Odoo': '✅ Implementado',
            'Campo Odoo': 'Fijo: "new"',
            'Prioridad': 1,
            'Acción Requerida': 'Opcional: mapear desde campo personalizado',
            'Impacto': 'Sin este campo el producto NO se indexa'
        },
        {
            'Campo': 'brand',
            'Categoría': 'CRÍTICO',
            'Descripción': 'Marca del producto',
            'Formato': 'String',
            'Ejemplo': 'Klavier',
            'Estado en Odoo': '✅ Implementado',
            'Campo Odoo': 'Fijo: "Klavier"',
            'Prioridad': 1,
            'Acción Requerida': 'Mejorar: mapear desde atributos de marca',
            'Impacto': 'Sin este campo el producto NO se indexa'
        },
        {
            'Campo': 'gtin',
            'Categoría': 'CRÍTICO',
            'Descripción': 'Código de barras global (EAN/UPC)',
            'Formato': 'Número de 8-14 dígitos',
            'Ejemplo': '1234567890123',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'x_studio_gtin (crear campo personalizado)',
            'Prioridad': 1,
            'Acción Requerida': 'CRÍTICO: Implementar o usar identifier_exists',
            'Impacto': 'Productos nuevos requieren GTIN o identifier_exists'
        },
        {
            'Campo': 'identifier_exists',
            'Categoría': 'CRÍTICO',
            'Descripción': 'Indica si el producto tiene identificadores únicos',
            'Formato': 'true | false',
            'Ejemplo': 'false',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Lógica: false si no hay GTIN/MPN',
            'Prioridad': 1,
            'Acción Requerida': 'CRÍTICO: Implementar inmediatamente',
            'Impacto': 'Requerido si no se proporciona GTIN'
        }
    ]

    # Author: AGomeroR

    # Campos condicionales para ropa y accesorios
    campos_ropa = [
        {
            'Campo': 'gender',
            'Categoría': 'CONDICIONAL ROPA',
            'Descripción': 'Género objetivo del producto',
            'Formato': 'male | female | unisex',
            'Ejemplo': 'unisex',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Atributo de producto: Género',
            'Prioridad': 2,
            'Acción Requerida': 'Crear atributo Género en Odoo',
            'Impacto': 'Obligatorio para ropa y accesorios'
        },
        {
            'Campo': 'age_group',
            'Categoría': 'CONDICIONAL ROPA',
            'Descripción': 'Grupo de edad objetivo',
            'Formato': 'newborn | infant | toddler | kids | adult',
            'Ejemplo': 'adult',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Atributo de producto: Grupo de Edad',
            'Prioridad': 2,
            'Acción Requerida': 'Crear atributo Grupo de Edad en Odoo',
            'Impacto': 'Obligatorio para ropa y accesorios'
        },
        {
            'Campo': 'color',
            'Categoría': 'CONDICIONAL ROPA',
            'Descripción': 'Color del producto',
            'Formato': 'Nombre estándar del color',
            'Ejemplo': 'Azul',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Variante de producto o atributo Color',
            'Prioridad': 2,
            'Acción Requerida': 'Configurar variantes por color',
            'Impacto': 'Obligatorio para productos con color'
        },
        {
            'Campo': 'size',
            'Categoría': 'CONDICIONAL ROPA',
            'Descripción': 'Talla del producto',
            'Formato': 'String (S, M, L, 42, etc.)',
            'Ejemplo': 'L',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Variante de producto o atributo Talla',
            'Prioridad': 2,
            'Acción Requerida': 'Configurar variantes por talla',
            'Impacto': 'Obligatorio para productos con tallas'
        },
        {
            'Campo': 'material',
            'Categoría': 'CONDICIONAL ROPA',
            'Descripción': 'Material principal del producto',
            'Formato': 'String',
            'Ejemplo': 'Algodón',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Atributo de producto: Material',
            'Prioridad': 2,
            'Acción Requerida': 'Crear atributo Material en Odoo',
            'Impacto': 'Obligatorio para productos textiles'
        }
    ]
    
    # Campos opcionales importantes
    campos_opcionales = [
        {
            'Campo': 'mpn',
            'Categoría': 'OPORTUNIDAD ALTA',
            'Descripción': 'Número de parte del fabricante',
            'Formato': 'String',
            'Ejemplo': 'SKU-12345',
            'Estado en Odoo': '✅ Implementado',
            'Campo Odoo': 'default_code',
            'Prioridad': 2,
            'Acción Requerida': 'Ninguna - Ya implementado',
            'Impacto': 'Mejora identificación del producto'
        },
        {
            'Campo': 'google_product_category',
            'Categoría': 'OPORTUNIDAD ALTA',
            'Descripción': 'Categoría estándar de Google',
            'Formato': 'ID numérico o texto',
            'Ejemplo': '1604 (Apparel & Accessories)',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Mapear desde categ_id',
            'Prioridad': 2,
            'Acción Requerida': 'Crear mapeo categorías Odoo → Google',
            'Impacto': 'Mejor clasificación y visibilidad'
        },
        {
            'Campo': 'product_type',
            'Categoría': 'OPORTUNIDAD MEDIA',
            'Descripción': 'Categoría personalizada',
            'Formato': 'String con jerarquía',
            'Ejemplo': 'Ropa > Camisetas > Manga Corta',
            'Estado en Odoo': '✅ Disponible',
            'Campo Odoo': 'categ_id (complete_name)',
            'Prioridad': 3,
            'Acción Requerida': 'Mapear desde categorías de Odoo',
            'Impacto': 'Organización interna mejorada'
        },
        {
            'Campo': 'sale_price',
            'Categoría': 'OPORTUNIDAD ALTA',
            'Descripción': 'Precio de oferta/descuento',
            'Formato': '{amount_micros, currency_code}',
            'Ejemplo': '{24990000, "EUR"}',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Pricelist con descuentos',
            'Prioridad': 2,
            'Acción Requerida': 'Implementar desde listas de precios',
            'Impacto': 'Promociones y ofertas visibles'
        },
        {
            'Campo': 'sale_price_effective_date',
            'Categoría': 'OPORTUNIDAD MEDIA',
            'Descripción': 'Fechas de validez de la oferta',
            'Formato': 'YYYY-MM-DD/YYYY-MM-DD',
            'Ejemplo': '2024-01-01/2024-01-31',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Fechas de pricelist',
            'Prioridad': 3,
            'Acción Requerida': 'Implementar fechas de promociones',
            'Impacto': 'Promociones temporales'
        },
        {
            'Campo': 'shipping_weight',
            'Categoría': 'OPORTUNIDAD MEDIA',
            'Descripción': 'Peso para cálculo de envío',
            'Formato': 'Número + unidad',
            'Ejemplo': '0.5 kg',
            'Estado en Odoo': '✅ Disponible',
            'Campo Odoo': 'weight',
            'Prioridad': 3,
            'Acción Requerida': 'Mapear campo weight',
            'Impacto': 'Cálculo preciso de envíos'
        },
        {
            'Campo': 'shipping',
            'Categoría': 'OPORTUNIDAD MEDIA',
            'Descripción': 'Configuración de envío específica',
            'Formato': 'Objeto con precio y país',
            'Ejemplo': '{price: 5.99, country: "ES"}',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Configuración manual',
            'Prioridad': 3,
            'Acción Requerida': 'Configurar políticas de envío',
            'Impacto': 'Control granular de envíos'
        },
        {
            'Campo': 'item_group_id',
            'Categoría': 'OPORTUNIDAD MEDIA',
            'Descripción': 'Agrupación de variantes',
            'Formato': 'String identificador',
            'Ejemplo': 'camiseta_azul_grupo',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'product_tmpl_id',
            'Prioridad': 3,
            'Acción Requerida': 'Mapear desde template de producto',
            'Impacto': 'Agrupa variantes relacionadas'
        },
        {
            'Campo': 'custom_label_0',
            'Categoría': 'OPORTUNIDAD BAJA',
            'Descripción': 'Etiqueta personalizada para organización',
            'Formato': 'String',
            'Ejemplo': 'Temporada Verano',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Tags o campos personalizados',
            'Prioridad': 4,
            'Acción Requerida': 'Configurar etiquetas personalizadas',
            'Impacto': 'Organización y segmentación interna'
        },
        {
            'Campo': 'ads_redirect',
            'Categoría': 'OPORTUNIDAD BAJA',
            'Descripción': 'URL alternativa para anuncios',
            'Formato': 'URL válida',
            'Ejemplo': 'https://klavier.es/promo/producto123',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Campo personalizado URL promocional',
            'Prioridad': 4,
            'Acción Requerida': 'Crear campo URL promocional',
            'Impacto': 'URLs específicas para campañas'
        }
    ]
    
    # Campos de las novedades 2024-2025
    campos_novedades = [
        {
            'Campo': 'structured_title',
            'Categoría': 'NOVEDAD 2024',
            'Descripción': 'Título generado por IA (obligatorio si se usa IA)',
            'Formato': 'String con marcador de IA',
            'Ejemplo': 'Camiseta Azul [AI-Generated]',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'N/A - Solo si se usa IA',
            'Prioridad': 5,
            'Acción Requerida': 'Implementar si se genera contenido con IA',
            'Impacto': 'Transparencia en contenido generado por IA'
        },
        {
            'Campo': 'structured_description',
            'Categoría': 'NOVEDAD 2024',
            'Descripción': 'Descripción generada por IA (obligatorio si se usa IA)',
            'Formato': 'String con marcador de IA',
            'Ejemplo': 'Descripción detallada... [AI-Generated]',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'N/A - Solo si se usa IA',
            'Prioridad': 5,
            'Acción Requerida': 'Implementar si se genera contenido con IA',
            'Impacto': 'Transparencia en contenido generado por IA'
        },
        {
            'Campo': 'loyalty_program',
            'Categoría': 'NOVEDAD 2024',
            'Descripción': 'Configuración de programa de fidelización',
            'Formato': 'Objeto con precios de miembro',
            'Ejemplo': '{member_price: 25.99, points: 100}',
            'Estado en Odoo': '❌ FALTA',
            'Campo Odoo': 'Sistema de puntos/fidelización',
            'Prioridad': 5,
            'Acción Requerida': 'Implementar si hay programa de fidelización',
            'Impacto': 'Precios especiales para miembros'
        }
    ]
    
    # Combinar todos los datos
    todos_campos = campos_criticos + campos_ropa + campos_opcionales + campos_novedades
    
    # Crear DataFrame
    df = pd.DataFrame(todos_campos)
    
    # Reordenar columnas para mejor legibilidad
    columnas_ordenadas = [
        'Campo', 'Categoría', 'Prioridad', 'Estado en Odoo', 'Descripción',
        'Formato', 'Ejemplo', 'Campo Odoo', 'Acción Requerida', 'Impacto'
    ]
    df = df[columnas_ordenadas]
    
    # Crear archivo Excel con múltiples hojas
    archivo_excel = 'Google_Merchant_Requirements.xlsx'
    
    with pd.ExcelWriter(archivo_excel, engine='openpyxl') as writer:
        # Hoja 1: Todos los campos
        df.to_excel(writer, sheet_name='Todos los Campos', index=False)
        
        # Hoja 2: Solo campos críticos
        df_criticos = df[df['Categoría'].isin(['CRÍTICO'])]
        df_criticos.to_excel(writer, sheet_name='Campos CRÍTICOS', index=False)
        
        # Hoja 3: Campos faltantes
        df_faltantes = df[df['Estado en Odoo'].str.contains('❌', na=False)]
        df_faltantes.to_excel(writer, sheet_name='Campos FALTANTES', index=False)
        
        # Hoja 4: Oportunidades de mejora
        df_oportunidades = df[df['Categoría'].str.contains('OPORTUNIDAD', na=False)]
        df_oportunidades.to_excel(writer, sheet_name='Oportunidades', index=False)
        
        # Hoja 5: Resumen por prioridad
        resumen_prioridad = df.groupby(['Prioridad', 'Categoría']).size().reset_index(name='Cantidad')
        resumen_prioridad.to_excel(writer, sheet_name='Resumen por Prioridad', index=False)
        
        # Hoja 6: Resumen por estado
        resumen_estado = df.groupby(['Estado en Odoo', 'Categoría']).size().reset_index(name='Cantidad')
        resumen_estado.to_excel(writer, sheet_name='Resumen por Estado', index=False)
    
    print(f"✅ Archivo Excel creado: {archivo_excel}")
    print(f"📊 Total de campos analizados: {len(df)}")
    print(f"❌ Campos faltantes: {len(df_faltantes)}")
    print(f"🔴 Campos críticos faltantes: {len(df[(df['Categoría'] == 'CRÍTICO') & (df['Estado en Odoo'].str.contains('❌', na=False))])}")
    
    return archivo_excel

if __name__ == "__main__":
    print("🚀 Generando archivo Excel con requisitos de Google Merchant Center...")
    archivo = create_google_merchant_requirements_excel()
    print(f"🎉 ¡Archivo creado exitosamente: {archivo}!")