#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google Merchant API Sync Script (New Merchant API v1)
Sincroniza productos de Odoo con Google Merchant Center usando la nueva Merchant API

NOTA: Esta versión usa la nueva Merchant API que reemplaza la Content API for Shopping
La Content API será descontinuada en agosto 2026.

REQUISITOS DE PRODUCTOS:
- website_published = True
- image_1920 no vacío
- website_description no vacío
- list_price > 0

MAPEO DE CAMPOS MERCHANT API:
- name → title
- website_description → description
- image_1920 → imageLink (convertido a URL)
- list_price → price (formato: amountMicros + currencyCode)
- id → offerId (unique identifier)
"""

import xmlrpc.client
import os
import sys
import json
import time
import base64
import tempfile
import threading
import http.server
import socketserver
from datetime import datetime
from dotenv import load_dotenv
import argparse

# New Merchant API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2 import service_account
    from google.shopping.merchant_products_v1 import ProductInputsServiceClient, ProductsServiceClient, InsertProductInputRequest
    from google.shopping.merchant_products_v1.types import ProductInput, ProductAttributes, Availability, Condition
    from google.shopping.merchant_products_v1.types.products_common import ShippingWeight
    from google.shopping.type import Price, Weight
    from google.api_core import exceptions as api_exceptions
    MERCHANT_API_AVAILABLE = True
except ImportError:
    MERCHANT_API_AVAILABLE = False

# Cargar variables de entorno
load_dotenv()

# Configuración de archivos
PROGRESS_FILE = os.path.join("Workflow", "merchant_sync_progress.json")
ERROR_LOG_FILE = os.path.join("Workflow", "merchant_sync_errors.json")
IMAGES_DIR = os.path.join("Workflow", "temp_images")

# Configuración de Odoo desde .env
ODOO_URL = os.getenv('ODOO_URL')
ODOO_DATABASE = os.getenv('ODOO_DB')
ODOO_USERNAME = os.getenv('ODOO_USER')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')
ODOO_API_KEY = os.getenv('ODOO_API_KEY')

# Configuración de Google Merchant desde .env
GOOGLE_MERCHANT_ID = os.getenv('GOOGLE_MERCHANT_ID')
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')
GOOGLE_DATA_SOURCE_ID = os.getenv('GOOGLE_DATA_SOURCE_ID')
WEBSITE_BASE_URL = os.getenv('WEBSITE_BASE_URL', 'https://www.klavier.es')
DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'EUR')
DEFAULT_COUNTRY = os.getenv('DEFAULT_COUNTRY', 'ES')
DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'es')
GTIN_PREFIX = os.getenv('GTIN_PREFIX', '748')

# Configuración del servidor HTTP temporal para imágenes
HTTP_SERVER_PORT = 8081
HTTP_SERVER_HOST = 'localhost'

# Variable global para el servidor HTTP
http_server = None
server_thread = None

class TemporaryImageServer:
    """Servidor HTTP temporal para servir imágenes convertidas de base64"""
    
    def __init__(self, port=HTTP_SERVER_PORT, host=HTTP_SERVER_HOST):
        self.port = port
        self.host = host
        self.server = None
        self.thread = None
        self.images_dir = IMAGES_DIR
        
    def start(self):
        """Inicia el servidor HTTP en un hilo separado"""
        try:
            # Crear directorio de imágenes temporales
            os.makedirs(self.images_dir, exist_ok=True)
            
            # Cambiar al directorio de imágenes para servir archivos
            original_dir = os.getcwd()
            os.chdir(self.images_dir)
            
            # Crear servidor HTTP
            handler = http.server.SimpleHTTPRequestHandler
            self.server = socketserver.TCPServer((self.host, self.port), handler)
            
            # Restaurar directorio original
            os.chdir(original_dir)
            
            # Iniciar servidor en hilo separado
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            
            print(f"🌐 Servidor HTTP iniciado en http://{self.host}:{self.port}")
            return True
            
        except Exception as e:
            print(f"❌ Error iniciando servidor HTTP: {e}")
            return False
    
    def stop(self):
        """Detiene el servidor HTTP"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("🛑 Servidor HTTP detenido")
    
    def save_image_from_base64(self, base64_data, filename):
        """Guarda una imagen base64 como archivo y retorna la URL"""
        try:
            # Decodificar base64
            image_data = base64.b64decode(base64_data)
            
            # Guardar archivo
            file_path = os.path.join(self.images_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            # Retornar URL del servidor HTTP
            url = f"http://{self.host}:{self.port}/{filename}"
            return url
            
        except Exception as e:
            print(f"❌ Error guardando imagen {filename}: {e}")
            return None

# Author: AGomeroR

class OdooMerchantAPISync:
    """Clase principal para sincronización Odoo -> Google Merchant API"""

    def __init__(self):
        self.odoo_url = None
        self.odoo_db = None
        self.odoo_username = None
        self.odoo_password = None
        self.odoo_uid = None
        self.odoo_models = None
        self.odoo_common = None
        
        self.merchant_client = None
        self.merchant_id = None
        self.data_source_id = None
        
        # self.image_server = TemporaryImageServer()  # Ya no necesario - usando URLs directas
        
    def connect_odoo(self):
        """Establece conexión con Odoo"""
        print("🔗 Conectando a Odoo...")
        
        # Validar configuración
        if not all([ODOO_URL, ODOO_DATABASE]):
            raise Exception("Faltan ODOO_URL y ODOO_DB en el archivo .env")
        
        # Validar autenticación
        if not ((ODOO_USERNAME and ODOO_PASSWORD) or ODOO_API_KEY):
            raise Exception("Falta autenticación: especifica ODOO_API_KEY o (ODOO_USER + ODOO_PASSWORD)")
        
        self.odoo_url = ODOO_URL
        self.odoo_db = ODOO_DATABASE
        
        try:
            # Conexión a Odoo
            self.odoo_common = xmlrpc.client.ServerProxy(f'{self.odoo_url}/xmlrpc/2/common')
            self.odoo_models = xmlrpc.client.ServerProxy(f'{self.odoo_url}/xmlrpc/2/object')
            
            # Autenticación
            if ODOO_API_KEY:
                # Usar API key
                self.odoo_username = ODOO_USERNAME or 'admin'
                self.odoo_password = ODOO_API_KEY
                print("🔑 Usando autenticación por API Key")
            else:
                # Usar username/password
                self.odoo_username = ODOO_USERNAME
                self.odoo_password = ODOO_PASSWORD
                print("🔑 Usando autenticación por usuario/contraseña")
            
            self.odoo_uid = self.odoo_common.authenticate(
                self.odoo_db, self.odoo_username, self.odoo_password, {}
            )
            
            if not self.odoo_uid:
                raise Exception("Error de autenticación. Verifica las credenciales.")
            
            print(f"✅ Conectado exitosamente a Odoo como usuario ID: {self.odoo_uid}")
            return True
            
        except Exception as e:
            print(f"❌ Error conectando a Odoo: {e}")
            return False
    
    def authenticate_merchant_api(self):
        """Autentica con Google Merchant API (nueva versión)"""
        print("🔐 Autenticando con Google Merchant API...")
        
        if not MERCHANT_API_AVAILABLE:
            raise Exception("Merchant API no disponible. Instala: pip install google-shopping-merchant-products")
        
        if not GOOGLE_MERCHANT_ID:
            raise Exception("GOOGLE_MERCHANT_ID no configurado en .env")
        
        if not GOOGLE_DATA_SOURCE_ID:
            raise Exception("GOOGLE_DATA_SOURCE_ID no configurado en .env")
        
        if not GOOGLE_CREDENTIALS_FILE or not os.path.exists(GOOGLE_CREDENTIALS_FILE):
            raise Exception(f"Archivo de credenciales no encontrado: {GOOGLE_CREDENTIALS_FILE}")
        
        try:
            # Cargar credenciales de service account
            credentials = service_account.Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_FILE
            )
            
            # Crear clientes de Merchant API
            self.merchant_client = ProductInputsServiceClient(credentials=credentials)
            self.products_client = ProductsServiceClient(credentials=credentials)
            self.merchant_id = GOOGLE_MERCHANT_ID
            self.data_source_id = GOOGLE_DATA_SOURCE_ID
            
            print(f"✅ Autenticado con Google Merchant API")
            print(f"   - Merchant ID: {self.merchant_id}")
            print(f"   - Data Source ID: {self.data_source_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error autenticando con Google Merchant API: {e}")
            return False
    
    def register_developer_if_needed(self):
        """Registra el desarrollador con el Merchant Center (requerido para nueva API)"""
        print("📝 Verificando registro de desarrollador...")
        
        # NOTA: La nueva Merchant API requiere que el Merchant Center esté vinculado
        # al proyecto de Google Cloud. Esto normalmente se hace una vez a través de la UI
        # o con una llamada de registro específica.
        
        # Por ahora, asumimos que el registro ya está hecho.
        # En implementaciones futuras, se puede agregar la llamada de registro automática.
        
        print("ℹ️ Asumiendo que el Merchant Center ya está vinculado al proyecto GCP")
        print("   Si hay errores de autorización, vincular manualmente en Merchant Center > Settings > Developer Registration")
        return True
    
    def calculate_gtin_check_digit(self, gtin_13):
        """
        Calcula el dígito de control para un GTIN de 13 dígitos según el algoritmo GS1 oficial
        """
        # Algoritmo GS1 correcto:
        # Paso 1: Sumar posiciones impares (índices 0,2,4,6...) y multiplicar por 3
        odd_sum = sum(int(gtin_13[i]) for i in range(0, len(gtin_13), 2)) * 3
        
        # Paso 2: Sumar posiciones pares (índices 1,3,5,7...)
        even_sum = sum(int(gtin_13[i]) for i in range(1, len(gtin_13), 2))
        
        # Paso 3: Calcular check digit
        total = odd_sum + even_sum
        remainder = total % 10
        check_digit = 0 if remainder == 0 else (10 - remainder)
        
        return str(check_digit)
    
    def convert_barcode_to_gtin14(self, barcode_11):
        """
        Convierte un código de barras de 11 dígitos a GTIN-14 válido
        usando el prefijo configurado y calculando el dígito de control
        """
        # Para GTIN-14, necesitamos exactamente 14 dígitos
        # Formato: [prefijo 3 dígitos] + [código reducido 10 dígitos] + [check digit 1 dígito]
        
        # Tomar solo los últimos 10 dígitos del barcode de 11 para que encaje
        barcode_10 = barcode_11[-10:]  # Últimos 10 dígitos
        
        # Combinar prefijo + 10 dígitos = 13 dígitos
        gtin_13 = GTIN_PREFIX + barcode_10
        
        # Calcular dígito de control GS1
        check_digit = self.calculate_gtin_check_digit(gtin_13)
        
        # GTIN-14 final (exactamente 14 dígitos)
        gtin_14 = gtin_13 + check_digit
        return gtin_14
    
    def validate_and_format_gtin(self, barcode):
        """
        Valida y formatea un código de barras como GTIN válido
        GTIN puede ser de 8, 12, 13, o 14 dígitos
        Para códigos de 11 dígitos, los convierte automáticamente a GTIN-14
        """
        if not barcode:
            return None
            
        # Limpiar el código: solo dígitos
        clean_barcode = ''.join(filter(str.isdigit, str(barcode).strip()))
        
        # Verificar que no sea solo ceros
        if clean_barcode == '0' * len(clean_barcode):
            return None
        
        # Verificar longitud y manejar conversiones
        if len(clean_barcode) == 11:
            # Convertir código de 11 dígitos a GTIN-14 válido
            gtin_14 = self.convert_barcode_to_gtin14(clean_barcode)
            print(f"    🔄 Barcode convertido: {clean_barcode} → GTIN-14: {gtin_14} (prefijo {GTIN_PREFIX} + últimos 10 dígitos)")
            return gtin_14
        elif len(clean_barcode) in [8, 12, 13, 14]:
            # Longitudes válidas, usar tal como está
            return clean_barcode
        else:
            # Longitud inválida
            return None
    
    def get_brand_from_attributes(self, odoo_product):
        """Obtiene la marca desde los atributos del producto en Odoo"""
        try:
            # Según Excel: "Coger the attribute_id el atributo Marca y usar el value_ids de esta mima"
            # Esta lógica requiere hacer una consulta adicional a Odoo para obtener atributos
            
            # Por ahora, devolver marca por defecto
            # TODO: Implementar consulta a product.template.attribute.line para obtener marca real
            return "Klavier"
            
        except Exception as e:
            print(f"    ⚠️ Error obteniendo marca: {e}")
            return "Klavier"
    
    def get_google_category_from_public_categ(self, odoo_product):
        """Mapea public_categ_ids de Odoo a categorías de Google"""
        try:
            # Según Excel: usar public_categ_ids
            public_categ_ids = odoo_product.get('public_categ_ids', [])
            
            if not public_categ_ids:
                return None
            
            # Mapeo básico de categorías (se puede expandir según necesidades)
            # Por ahora, devolver una categoría genérica
            return "1604"  # Apparel & Accessories - categoría genérica
            
        except Exception as e:
            print(f"    ⚠️ Error mapeando categoría Google: {e}")
            return None
    
    def get_publishable_products(self, batch_size=500):
        """Extrae productos de Odoo que cumplen criterios para Google Merchant en lotes"""
        print("📦 Extrayendo productos publicables de Odoo en lotes...")
        
        try:
            # Dominio de búsqueda: productos que cumplen todos los criterios
            domain = [
                ['website_published', '=', True],
                ['image_1920', '!=', False],
                ['website_description', '!=', False],
                ['list_price', '>', 0]
            ]
            
            # Campos necesarios para Google Merchant (según Excel modificado)
            fields = [
                'id', 'name', 'website_description', 'image_1920', 
                'compare_list_price', 'list_price', 'default_code', 'active',
                'barcode', 'website_url', 'weight', 'public_categ_ids'
                # Nota: No necesitamos product_tmpl_id porque estamos consultando product.template directamente
            ]
            
            # Primero, obtener solo los IDs para contar total
            print("🔍 Contando productos que cumplen criterios...")
            product_ids = self.odoo_models.execute_kw(
                self.odoo_db, self.odoo_uid, self.odoo_password,
                'product.template', 'search',
                [domain]
            )
            
            total_products = len(product_ids)
            print(f"✅ Encontrados {total_products} productos publicables")
            
            if total_products == 0:
                return []
            
            # Extraer productos en lotes
            all_products = []
            num_batches = (total_products + batch_size - 1) // batch_size
            print(f"📊 Procesando en {num_batches} lotes de máximo {batch_size} productos...")
            
            for batch_num in range(num_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total_products)
                batch_ids = product_ids[start_idx:end_idx]
                
                print(f"📦 Lote {batch_num + 1}/{num_batches}: extrayendo productos {start_idx + 1}-{end_idx}")
                
                # Extraer datos del lote actual
                batch_products = self.odoo_models.execute_kw(
                    self.odoo_db, self.odoo_uid, self.odoo_password,
                    'product.template', 'read',
                    [batch_ids],
                    {'fields': fields}
                )
                
                all_products.extend(batch_products)
                print(f"   ✅ Lote {batch_num + 1} completado: {len(batch_products)} productos extraídos")
                
                # Pausa entre lotes para no sobrecargar el servidor
                if batch_num < num_batches - 1:  # No pausar después del último lote
                    time.sleep(1)
            
            print(f"🎉 Extracción completada: {len(all_products)} productos obtenidos")
            
            # Mostrar estadísticas
            if all_products:
                with_default_code = sum(1 for p in all_products if p.get('default_code'))
                print(f"   - {with_default_code}/{len(all_products)} productos con código de referencia")
                
                # Mostrar algunos ejemplos
                print("📋 Ejemplos de productos encontrados:")
                for i, product in enumerate(all_products[:3]):
                    print(f"   {i+1}. {product['name']} (ID: {product['id']}, Precio: €{product['list_price']})")
            
            return all_products
            
        except Exception as e:
            print(f"❌ Error extrayendo productos de Odoo: {e}")
            return []
    
    def transform_product_data(self, odoo_product):
        """Transforma datos de producto Odoo a formato Merchant API según mapeos del Excel"""
        try:
            # ID único para Google Merchant (offerId)
            offer_id = f"odoo_{odoo_product['id']}"
            
            # URL del producto - siempre usar BASE_URL para asegurar URL completa
            website_url = odoo_product.get('website_url', '').strip()
            if website_url and website_url.startswith('http'):
                # Si ya es una URL completa, usarla tal como está
                product_link = website_url
            elif website_url and website_url.startswith('/'):
                # Si es una URL relativa, añadir el BASE_URL
                product_link = f"{WEBSITE_BASE_URL.rstrip('/')}{website_url}"
            else:
                # Construir URL por defecto
                product_link = f"{WEBSITE_BASE_URL}/shop/product/{odoo_product['id']}"
            
            print(f"    🔗 URL del producto: {product_link}")
            
            # Generar URL directa de imagen desde Odoo usando product.template
            image_url = None
            if odoo_product.get('image_1920'):
                # Usar product.template para la URL de imagen (el id ya es el template_id)
                template_id = odoo_product['id']  # Estamos consultando product.template directamente
                image_url = f"{WEBSITE_BASE_URL}/web/image/product.template/{template_id}/image_1920"
                print(f"    🖼️ URL de imagen: {image_url} (product.template)")
            
            if not image_url:
                raise Exception(f"No se pudo generar URL de imagen para producto {offer_id}")
            
            # Precio principal - usar compare_list_price según Excel
            main_price = odoo_product.get('compare_list_price') or odoo_product.get('list_price', 0)
            price_micros = int(float(main_price) * 1_000_000)
            
            # Sale price - usar list_price según Excel  
            sale_price_micros = None
            if odoo_product.get('list_price') and float(odoo_product['list_price']) > 0:
                sale_price_micros = int(float(odoo_product['list_price']) * 1_000_000)
            
            # Brand - obtener desde atributos de marca de Odoo
            brand_name = self.get_brand_from_attributes(odoo_product)
            if not brand_name:
                brand_name = "Klavier"  # Valor por defecto
            
            # GTIN desde barcode según Excel - con validación de formato
            gtin_value = self.validate_and_format_gtin(odoo_product.get('barcode'))
            
            # Google Product Category desde public_categ_ids
            google_category = self.get_google_category_from_public_categ(odoo_product)
            
            # Crear ProductInput con la estructura oficial correcta
            # Basado en la documentación oficial de Google Merchant API v1
            
            # Crear atributos del producto usando la estructura correcta
            product_attributes = {
                'title': odoo_product['name'][:150],  # Límite de Google
                'description': odoo_product['website_description'][:5000],  # Límite de Google
                'link': product_link,
                'image_link': image_url,
                'availability': Availability.IN_STOCK,  # Usar enum oficial en lugar de string
                'condition': Condition.NEW,  # Usar enum oficial en lugar de string
                'brand': brand_name
            }
            
            # Precio usando la clase Price oficial
            product_attributes['price'] = Price(
                amount_micros=price_micros,
                currency_code=DEFAULT_CURRENCY
            )
            
            # Agregar GTIN si existe y es válido (como array)
            if gtin_value:
                product_attributes['gtins'] = [gtin_value]
                print(f"    📦 GTIN válido añadido: {gtin_value}")
            else:
                barcode_raw = odoo_product.get('barcode', '')
                if barcode_raw:
                    print(f"    ⚠️ Barcode inválido ignorado: '{barcode_raw}' (debe ser GTIN de 8, 12, 13 o 14 dígitos)")
                else:
                    print(f"    ℹ️ Sin código de barras en Odoo")
            
            # Agregar MPN si existe
            if odoo_product.get('default_code'):
                product_attributes['mpn'] = odoo_product['default_code']
                print(f"    🔢 MPN añadido: {odoo_product['default_code']}")
            
            # Agregar peso si existe (usando ShippingWeight)
            if odoo_product.get('weight') and float(odoo_product['weight']) > 0:
                # El peso en Odoo está en kg
                weight_kg = float(odoo_product['weight'])
                
                product_attributes['shipping_weight'] = ShippingWeight(
                    value=weight_kg,
                    unit='kg'  # Unidad en kilogramos
                )
                print(f"    ⚖️ Peso añadido: {weight_kg}kg")
            
            # Agregar sale_price si es diferente al precio principal
            if sale_price_micros and sale_price_micros != price_micros:
                product_attributes['sale_price'] = Price(
                    amount_micros=sale_price_micros,
                    currency_code=DEFAULT_CURRENCY
                )
                print(f"    💰 Sale price añadido: €{sale_price_micros / 1_000_000}")
            
            # Agregar categoría de Google si se pudo mapear
            if google_category:
                product_attributes['google_product_category'] = google_category
                print(f"    🏷️ Categoría Google añadida: {google_category}")
            
            # Crear ProductInput con los campos correctos según la documentación oficial
            try:
                # Crear ProductAttributes primero
                attributes = ProductAttributes(**product_attributes)
                
                product_input = ProductInput(
                    content_language=DEFAULT_LANGUAGE,
                    feed_label=DEFAULT_COUNTRY,
                    offer_id=offer_id,
                    product_attributes=attributes  # Campo correcto: product_attributes
                )
                
                print(f"    ✅ ProductInput creado correctamente para {offer_id}")
                return product_input
                
            except Exception as creation_error:
                print(f"    ❌ Error específico creando ProductInput: {type(creation_error).__name__}: {creation_error}")
                print(f"    📋 Datos problemáticos:")
                print(f"       - offer_id: {offer_id}")
                print(f"       - content_language: {DEFAULT_LANGUAGE}")
                print(f"       - feed_label: {DEFAULT_COUNTRY}")
                print(f"       - product_attributes keys: {list(product_attributes.keys())}")
                
                # Mostrar algunos valores de attributes para debug
                for key in ['title', 'availability', 'condition', 'price']:
                    if key in product_attributes:
                        value = product_attributes[key]
                        print(f"       - {key}: {type(value).__name__} = {value}")
                
                import traceback
                traceback.print_exc()
                return None
            
        except Exception as e:
            print(f"❌ Error general transformando producto {odoo_product.get('name', 'desconocido')}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def insert_product_to_merchant(self, product_input):
        """Inserta un producto en Google Merchant usando la nueva API"""
        try:
            # Crear el request object usando InsertProductInputRequest
            request = InsertProductInputRequest(
                parent=f"accounts/{self.merchant_id}",
                product_input=product_input,
                data_source=f"accounts/{self.merchant_id}/dataSources/{self.data_source_id}"
            )
            
            # Hacer la llamada a la API con request object
            result = self.merchant_client.insert_product_input(request=request)
            
            return {
                'success': True, 
                'result': result,
                'action': 'created',
                'product_name': result.name if hasattr(result, 'name') else 'unknown'
            }
            
        except api_exceptions.AlreadyExists:
            # El producto ya existe, esto es normal en muchos casos
            return {
                'success': True,
                'action': 'already_exists',
                'product_name': product_input.offer_id
            }
            
        except api_exceptions.InvalidArgument as e:
            return {
                'success': False,
                'error': f"Argumentos inválidos: {e}",
                'details': str(e)
            }
            
        except api_exceptions.PermissionDenied as e:
            return {
                'success': False,
                'error': f"Permisos denegados: {e}",
                'details': "Verificar que el Merchant Center esté vinculado al proyecto GCP"
            }
            
        except Exception as e:
            return {
                'success': False, 
                'error': f"Error inesperado: {e}",
                'details': str(e)
            }
    
    def get_existing_product(self, offer_id):
        """Busca un producto existente en Google Merchant por offer_id"""
        try:
            # El formato correcto para productos usa el channel y contentLanguage  
            # accounts/{account}/products/{offerId}~{contentLanguage}~{targetCountry}~{channel}
            product_name = f"accounts/{self.merchant_id}/products/{offer_id}~{DEFAULT_LANGUAGE}~{DEFAULT_COUNTRY}~online"
            
            # Intentar obtener el producto existente
            existing_product = self.products_client.get_product(name=product_name)
            
            print(f"    🔍 Producto existente encontrado: {offer_id}")
            return existing_product
            
        except api_exceptions.NotFound:
            # El producto no existe, esto es normal para productos nuevos
            print(f"    ➕ Producto nuevo: {offer_id}")
            return None
            
        except Exception as e:
            print(f"    ⚠️ Error buscando producto {offer_id}: {e}")
            return None
    
    def needs_update(self, existing_product, new_product_input):
        """Compara un producto existente con los nuevos datos para determinar si necesita actualización"""
        try:
            # Extraer atributos del producto existente
            existing_attrs = existing_product.attributes if hasattr(existing_product, 'attributes') else {}
            new_attrs = new_product_input.product_attributes
            
            changes_detected = []
            
            # Comparar título
            if existing_attrs.get('title') != new_attrs.get('title'):
                changes_detected.append(f"title: '{existing_attrs.get('title')}' → '{new_attrs.get('title')}'")
            
            # Comparar descripción
            if existing_attrs.get('description') != new_attrs.get('description'):
                changes_detected.append(f"description: [CAMBIO EN DESCRIPCIÓN]")
            
            # Comparar precio
            existing_price = existing_attrs.get('price')
            new_price = new_attrs.get('price')
            if existing_price and new_price:
                existing_amount = getattr(existing_price, 'amount_micros', 0)
                new_amount = getattr(new_price, 'amount_micros', 0)
                if existing_amount != new_amount:
                    changes_detected.append(f"price: {existing_amount/1000000} → {new_amount/1000000}")
            
            # Comparar imagen
            if existing_attrs.get('image_link') != new_attrs.get('image_link'):
                changes_detected.append(f"image_link: [CAMBIO EN IMAGEN]")
            
            # Comparar disponibilidad
            if existing_attrs.get('availability') != new_attrs.get('availability'):
                changes_detected.append(f"availability: {existing_attrs.get('availability')} → {new_attrs.get('availability')}")
            
            if changes_detected:
                print(f"    🔄 Cambios detectados en {len(changes_detected)} campos:")
                for change in changes_detected[:3]:  # Mostrar solo los primeros 3 cambios
                    print(f"       - {change}")
                if len(changes_detected) > 3:
                    print(f"       - ... y {len(changes_detected) - 3} cambios más")
                return True
            else:
                print(f"    ✅ Sin cambios detectados")
                return False
                
        except Exception as e:
            print(f"    ⚠️ Error comparando productos: {e}")
            # En caso de error, asumir que necesita actualización
            return True
    
    def update_existing_product(self, product_input):
        """Actualiza un producto existente en Google Merchant"""
        try:
            # Construir el nombre del producto
            product_name = f"accounts/{self.merchant_id}/products/{product_input.offer_id}"
            
            # Nota: La nueva Merchant API usa insert para tanto crear como actualizar
            # Si el producto existe, insert lo reemplazará automáticamente
            request = InsertProductInputRequest(
                parent=f"accounts/{self.merchant_id}",
                product_input=product_input,
                data_source=f"accounts/{self.merchant_id}/dataSources/{self.data_source_id}"
            )
            
            result = self.merchant_client.insert_product_input(request=request)
            
            return {
                'success': True,
                'result': result,
                'action': 'updated',
                'product_name': result.name if hasattr(result, 'name') else product_input.offer_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error actualizando producto: {e}",
                'details': str(e),
                'action': 'update_failed'
            }
    
    def sync_product_to_merchant(self, product_input, dry_run=False):
        """Sincroniza un solo producto (crear o actualizar) con Google Merchant"""
        if dry_run:
            # En modo dry run, solo mostrar información
            print(f"  🔍 [DRY RUN] ProductInput preparado exitosamente:")
            print(f"     - Offer ID: {product_input.offer_id}")
            print(f"     - Idioma: {product_input.content_language}")
            print(f"     - País: {product_input.feed_label}")
            
            # Intentar acceder a algunos atributos de manera segura para el dry run
            try:
                if hasattr(product_input, 'product_attributes'):
                    attrs = product_input.product_attributes
                    title = attrs.get('title', 'N/A')
                    if hasattr(attrs.get('price'), 'amount_micros'):
                        price_amount = attrs.get('price').amount_micros / 1_000_000
                        currency = attrs.get('price').currency_code
                        print(f"     - Producto: {title[:50]}...")
                        print(f"     - Precio Odoo: {currency}{price_amount}")
                    else:
                        print(f"     - Producto: {title[:50]}...")
                        print(f"     - Precio: [CONFIGURADO]")
            except:
                print(f"     - Producto: [DATOS CONFIGURADOS]")
            
            print(f"     ✅ Listo para envío a Google Merchant")
            return {'success': True, 'action': 'dry_run', 'product_id': product_input.offer_id}
        
        try:
            # Usar insert_product_to_merchant directamente
            # La nueva Merchant API maneja automáticamente crear/actualizar:
            # - Si el producto no existe: lo crea
            # - Si el producto existe: lo reemplaza (actualiza)
            print(f"    🔄 Sincronizando producto (crear/actualizar automático)")
            return self.insert_product_to_merchant(product_input)
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Error en sincronización: {e}",
                'product_id': product_input.offer_id,
                'action': 'sync_failed'
            }
    
    def sync_products(self, dry_run=False):
        """Sincroniza productos de Odoo con Google Merchant API"""
        print("🚀 Iniciando sincronización con Google Merchant API...")
        
        if dry_run:
            print("🔍 MODO DRY RUN - No se realizarán cambios en Google Merchant")
        
        try:
            # Obtener productos de Odoo
            products = self.get_publishable_products()
            
            if not products:
                print("ℹ️ No hay productos para sincronizar")
                return True
            
            # Ya no necesitamos servidor de imágenes - usando URLs directas de Odoo
            print("🖼️ Usando URLs directas de Odoo para imágenes")
            
            # Contadores
            stats = {
                'total': len(products),
                'successful': 0,
                'created': 0,
                'updated': 0,
                'no_changes': 0,
                'already_exists': 0,
                'failed': 0,
                'skipped': 0
            }
            
            # Limitar productos solo en modo de testing (comentar para producción)
            # if not dry_run:
            #     products = products[:5]
            #     stats['total'] = len(products)
            #     print(f"\n🧪 MODO TEST: Procesando solo {stats['total']} productos")
            
            print(f"\n📊 Procesando {stats['total']} productos...")
            
            # Procesar cada producto
            for i, odoo_product in enumerate(products, 1):
                product_name = odoo_product.get('name', 'Sin nombre')
                print(f"\n[{i}/{stats['total']}] Procesando: {product_name}")
                
                try:
                    # Transformar datos
                    product_input = self.transform_product_data(odoo_product)
                    
                    if not product_input:
                        print(f"  ⚠️ No se pudo transformar producto, saltando...")
                        stats['skipped'] += 1
                        continue
                    
                    # Usar la nueva función de sincronización que maneja creación y actualización
                    result = self.sync_product_to_merchant(product_input, dry_run)
                    
                    if result['success']:
                        action = result.get('action', 'processed')
                        if action == 'dry_run':
                            stats['successful'] += 1
                        elif action == 'created':
                            print(f"  ✅ Producto sincronizado exitosamente (nuevo)")
                            stats['created'] += 1
                            stats['successful'] += 1
                        elif action == 'updated':
                            print(f"  🔄 Producto sincronizado exitosamente (actualizado)")
                            stats['updated'] += 1
                            stats['successful'] += 1
                        elif action == 'no_changes':
                            print(f"  ✅ Producto sincronizado exitosamente")
                            stats['no_changes'] += 1
                            stats['successful'] += 1
                        elif action == 'already_exists':
                            print(f"  ℹ️ Producto ya existe en Google Merchant")
                            stats['already_exists'] += 1
                            stats['successful'] += 1
                        else:
                            print(f"  ✅ Producto procesado exitosamente")
                            stats['successful'] += 1
                    else:
                        print(f"  ❌ Error: {result['error']}")
                        if 'details' in result:
                            print(f"     Detalles: {result['details']}")
                        stats['failed'] += 1
                    
                    # Pausa entre productos para respetar rate limits
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"  ❌ Error inesperado: {e}")
                    stats['failed'] += 1
            
            # Resumen final
            print(f"\n📋 Resumen de sincronización:")
            print(f"  - Total procesados: {stats['total']}")
            print(f"  - Exitosos: {stats['successful']}")
            print(f"    • Productos creados: {stats['created']}")
            print(f"    • Productos actualizados: {stats['updated']}")
            print(f"    • Sin cambios: {stats['no_changes']}")
            print(f"    • Ya existían: {stats['already_exists']}")
            print(f"  - Fallidos: {stats['failed']}")
            print(f"  - Saltados: {stats['skipped']}")
            
            return stats['failed'] == 0
            
        except Exception as e:
            print(f"❌ Error durante la sincronización: {e}")
            return False
        
        finally:
            # Ya no necesitamos limpiar imágenes temporales - usando URLs directas
            print("✅ Sincronización finalizada (usando URLs directas de Odoo)")
    
    def cleanup_temp_images(self):
        """Limpia las imágenes temporales generadas"""
        try:
            if os.path.exists(IMAGES_DIR):
                import shutil
                shutil.rmtree(IMAGES_DIR)
                print("🧹 Imágenes temporales eliminadas")
        except Exception as e:
            print(f"⚠️ Error limpiando imágenes temporales: {e}")

def parse_arguments():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Sincroniza productos de Odoo con Google Merchant API (nueva versión)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python google_merchant_sync.py --dry-run    # Modo prueba sin cambios
  python google_merchant_sync.py              # Sincronización completa

NOTA: Esta versión usa la nueva Merchant API que reemplaza Content API for Shopping.
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Modo de prueba - no realiza cambios en Google Merchant'
    )
    
    return parser.parse_args()

def main():
    """Función principal"""
    print("🚀 Google Merchant API Sync (Nueva API v1)")
    print("=" * 50)
    
    # Parsear argumentos
    args = parse_arguments()
    
    # Validar configuración
    missing_vars = []
    required_vars = [
        'ODOO_URL', 'ODOO_DB', 
        'GOOGLE_MERCHANT_ID', 'GOOGLE_CREDENTIALS_FILE', 'GOOGLE_DATA_SOURCE_ID'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    # Validar autenticación de Odoo
    if not (os.getenv('ODOO_API_KEY') or (os.getenv('ODOO_USER') and os.getenv('ODOO_PASSWORD'))):
        missing_vars.append('ODOO_API_KEY o (ODOO_USER + ODOO_PASSWORD)')
    
    if missing_vars:
        print("❌ Error: Faltan las siguientes variables en el archivo .env:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\n💡 Ejemplo de configuración completa:")
        print("GOOGLE_MERCHANT_ID=123456789")
        print("GOOGLE_DATA_SOURCE_ID=987654321")  
        print("GOOGLE_CREDENTIALS_FILE=/path/to/service-account.json")
        sys.exit(1)
    
    # Crear directorio Workflow si no existe
    os.makedirs("Workflow", exist_ok=True)
    
    # Ejecutar sincronización
    sync = OdooMerchantAPISync()
    
    try:
        # Conectar a Odoo
        if not sync.connect_odoo():
            sys.exit(1)
        
        # Autenticar con Google Merchant (solo si no es dry run)
        if not args.dry_run:
            if not sync.authenticate_merchant_api():
                sys.exit(1)
            
            # Verificar registro de desarrollador
            if not sync.register_developer_if_needed():
                sys.exit(1)
        
        # Sincronizar productos
        success = sync.sync_products(dry_run=args.dry_run)
        
        if success:
            print("\n🎉 Sincronización completada exitosamente")
        else:
            print("\n⚠️ Sincronización completada con errores")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🚨 Sincronización interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()