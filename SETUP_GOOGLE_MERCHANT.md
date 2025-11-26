# Google Merchant API Setup Instructions

Esta guía te ayudará a configurar la nueva Google Merchant API para la sincronización con Odoo.

## 🚨 Importante

Esta integración usa la **nueva Merchant API** que reemplaza la Content API for Shopping. La Content API será descontinuada en agosto 2026.

## Paso 1: Configurar Google Cloud Project

### 1.1 Crear/Seleccionar Proyecto
1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Anota el ID del proyecto

### 1.2 Habilitar Merchant API
1. En Cloud Console, ve a **APIs & Services > Library**
2. Busca "Merchant API"
3. Habilita la **Merchant API** (NO Content API for Shopping)

### 1.3 Crear Service Account
1. Ve a **APIs & Services > Credentials**
2. Clic en **Create Credentials > Service Account**
3. Llena los datos:
   - **Name**: `merchant-api-sync`
   - **Description**: `Service account for Odoo-Merchant sync`
4. Clic en **Create and Continue**
5. En **Grant access**, añade el rol: **Editor** (o permisos más específicos)
6. Clic en **Done**

### 1.4 Descargar Credenciales JSON
1. En la lista de Service Accounts, clic en el recién creado
2. Ve a la pestaña **Keys**
3. Clic en **Add Key > Create new key**
4. Selecciona **JSON** y descarga el archivo
5. Guarda el archivo en un lugar seguro (ej: `/path/to/merchant-credentials.json`)

## Paso 2: Configurar Google Merchant Center

### 2.1 Verificar Merchant Center
1. Ve a [Google Merchant Center](https://merchants.google.com/)
2. Asegúrate de que tu cuenta esté verificada y activa
3. Anota tu **Merchant ID** (número visible en la URL)

### 2.2 Vincular con Google Cloud Project
1. En Merchant Center, ve a **Settings > Developer Registration**
2. Clic en **Register for API access**
3. Selecciona tu Google Cloud Project
4. Confirma el registro

### 2.3 Crear Data Source
1. En Merchant Center, ve a **Products > Feeds**
2. Clic en **Create feed** (si no tienes uno)
3. Selecciona:
   - **Primary feeds**
   - **Shopping ads**
   - **Country**: Spain
   - **Language**: Spanish
4. Anota el **Data Source ID** (se muestra en la URL del feed)

## Paso 3: Configurar Variables de Entorno

Edita el archivo `.env` con los valores obtenidos:

```bash
# Google Merchant API configuration (New API v1)
GOOGLE_MERCHANT_ID=123456789  # Tu Merchant ID
GOOGLE_DATA_SOURCE_ID=987654321  # Tu Data Source ID  
GOOGLE_CREDENTIALS_FILE=/path/to/merchant-credentials.json  # Ruta al JSON
WEBSITE_BASE_URL=https://www.klavier.es
DEFAULT_CURRENCY=EUR
DEFAULT_COUNTRY=ES
DEFAULT_LANGUAGE=es
```

## Paso 4: Instalar Dependencias

```bash
pip install google-shopping-merchant-products
```

## Paso 5: Probar la Configuración

```bash
# Prueba sin hacer cambios
python google_merchant_sync.py --dry-run
```

Si todo está configurado correctamente, deberías ver:
- ✅ Conectado exitosamente a Odoo
- ✅ Autenticado con Google Merchant API
- 📦 Lista de productos encontrados

## Troubleshooting

### Error: "Merchant API no disponible"
- Instala: `pip install google-shopping-merchant-products`

### Error: "Permisos denegados"
- Verifica que el Merchant Center esté vinculado al proyecto GCP
- Revisa que el Service Account tenga permisos suficientes

### Error: "Data Source no encontrado"
- Verifica el `GOOGLE_DATA_SOURCE_ID` en Merchant Center > Products > Feeds
- Asegúrate de que el feed esté activo

### Error de autenticación
- Verifica que el archivo JSON de credenciales sea válido
- Comprueba que la ruta en `GOOGLE_CREDENTIALS_FILE` sea correcta

## Estructura de Datos

La nueva Merchant API usa esta estructura para productos:

```json
{
  "offerId": "odoo_123",
  "contentLanguage": "es",
  "feedLabel": "ES", 
  "channel": "ONLINE",
  "attributes": {
    "title": "Producto de prueba",
    "description": "Descripción del producto",
    "link": "https://www.klavier.es/shop/product/123",
    "imageLink": "http://localhost:8081/product_123.jpg",
    "price": {
      "amountMicros": "29990000",  // 29.99 EUR
      "currencyCode": "EUR"
    },
    "availability": "in stock",
    "condition": "new"
  }
}
```

## Recursos Adicionales

- [Merchant API Documentation](https://developers.google.com/merchant/api)
- [Migration Guide](https://developers.google.com/merchant/api/guides/compatibility/overview)
- [Python Client Library](https://googleapis.dev/python/google-shopping-merchant-products/latest/)

## Soporte

Si encuentras problemas:
1. Revisa los logs del script para errores específicos
2. Verifica la configuración paso a paso
3. Consulta la documentación oficial de Google Merchant API