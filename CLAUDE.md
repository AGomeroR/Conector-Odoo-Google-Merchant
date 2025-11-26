# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project integrates Odoo ERP with Google Merchant Center API to synchronize product data. The system extracts products from Odoo that meet specific criteria and uploads them to Google Merchant Center for e-commerce visibility.

## Development Commands

### Environment Setup
```bash
pip install pandas xmlrpc openpyxl python-dotenv google-auth google-auth-oauthlib google-auth-httplib2 google-shopping-merchant-products
```

### Running the Scripts
```bash
# Odoo Importer
python 27.Importador_directo_odoo.py                # Run with image cleanup
python 27.Importador_directo_odoo.py --keep-images  # Run keeping images

# Google Merchant Sync (New Merchant API)
python google_merchant_sync.py --dry-run            # Test run without changes
python google_merchant_sync.py                      # Full sync to Google Merchant
```

## Odoo Connection Architecture

### Authentication Methods
The project supports two Odoo authentication methods (configured in `.env`):
1. **API Key authentication** (preferred): `ODOO_API_KEY`
2. **Username/password authentication**: `ODOO_USER` + `ODOO_PASSWORD`

### Connection Pattern
```python
# XML-RPC connection setup
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
uid = common.authenticate(db, username, password, {})
```

### Product Extraction for Google Merchant

#### Required Product Criteria
Products must meet ALL of the following criteria to be exported to Google Merchant:
- `website_published = True` (product is published on website)
- Must have an image (`image_1920` field not empty)
- Must have `website_description` (not empty)
- Must have `list_price` > 0

#### Odoo Query Pattern
```python
# Search products that meet Google Merchant criteria
domain = [
    ['website_published', '=', True],
    ['image_1920', '!=', False],
    ['website_description', '!=', False],
    ['list_price', '>', 0]
]

products = models.execute_kw(
    db, uid, password,
    'product.template', 'search_read',
    [domain],
    {'fields': ['id', 'name', 'website_description', 'image_1920', 'list_price', 'default_code']}
)
```

## Google Merchant API Integration (New API v1)

⚠️ **IMPORTANTE**: Esta integración usa la nueva **Merchant API** que reemplaza la Content API for Shopping. La Content API será descontinuada en agosto 2026.

### Required Field Mapping (Odoo → Google Merchant API)

| Odoo Field | Google Merchant Field | Required | Notes |
|------------|----------------------|----------|--------|
| `name` | `attributes.title` | Yes | Product title (max 150 chars) |
| `website_description` | `attributes.description` | Yes | Product description (max 5000 chars) |
| `image_1920` | `attributes.image_link` | Yes | Convert base64 to accessible URL |
| `list_price` | `attributes.price` | Yes | Format: `{amount_micros: int, currency_code: string}` |
| `id` | `offer_id` | Yes | Unique product identifier (prefixed with "odoo_") |
| | `attributes.link` | Yes | Product page URL on website |
| | `attributes.availability` | Yes | "in stock" / "out of stock" |
| | `attributes.condition` | Yes | "new" (default) |
| | `content_language` | Yes | Language code (e.g., "es") |
| | `feed_label` | Yes | Target country (e.g., "ES") |
| | `channel` | Yes | "ONLINE" for web products |

### Google Merchant API Setup
1. **Google Cloud Project**: Enable **Merchant API** (not Content API)
2. **Authentication**: Service Account credentials (JSON file)
3. **Merchant Center Account**: Must be linked to Google Cloud project via Developer Registration
4. **Data Source**: Must have at least one data source configured in Merchant Center

### API Endpoints (New Merchant API)
- **Base URL**: `https://merchantapi.googleapis.com`
- **Insert Product**: `POST /products/v1/accounts/{merchantId}/productInputs:insert`
- **Product Management**: Uses `productInputs` instead of direct `products`

## Data Processing Pipeline

### 1. Extract Products from Odoo
```python
def get_publishable_products():
    """Extract products that meet Google Merchant criteria"""
    domain = [
        ['website_published', '=', True],
        ['image_1920', '!=', False],
        ['website_description', '!=', False],
        ['list_price', '>', 0]
    ]
    return odoo_models.execute_kw(db, uid, password, 'product.template', 'search_read', [domain])
```

### 2. Transform to Google Merchant API Format
```python
def transform_product_data(odoo_product):
    """Transform Odoo product to new Merchant API format"""
    from google.shopping.merchant_products_v1.types import ProductInput, Attributes, Price
    
    # Convert price to micros (price * 1,000,000)
    price_micros = int(float(odoo_product['list_price']) * 1_000_000)
    
    attributes = Attributes(
        title=odoo_product['name'][:150],
        description=odoo_product['website_description'][:5000],
        link=f"{WEBSITE_BASE_URL}/shop/product/{odoo_product['id']}",
        image_link=convert_base64_to_url(odoo_product['image_1920']),
        price=Price(
            amount_micros=price_micros,
            currency_code='EUR'
        ),
        availability="in stock",
        condition="new"
    )
    
    return ProductInput(
        offer_id=f"odoo_{odoo_product['id']}",
        content_language="es",
        feed_label="ES",
        channel="ONLINE",
        attributes=attributes
    )
```

### 3. Upload to Google Merchant API
```python
def upload_to_merchant_api(product_input):
    """Upload product using new Merchant API"""
    from google.shopping.merchant_products_v1 import ProductInputsServiceClient
    
    client = ProductInputsServiceClient(credentials=credentials)
    parent = f"accounts/{MERCHANT_ID}"
    data_source = f"accounts/{MERCHANT_ID}/dataSources/{DATA_SOURCE_ID}"
    
    request = {
        "parent": parent,
        "product_input": product_input,
        "data_source": data_source
    }
    
    return client.insert_product_input(**request)
```

## Image Handling

### Base64 to URL Conversion
Odoo stores images as base64 data in `image_1920` field. Google Merchant requires accessible URLs:

1. **Option 1**: Convert base64 to temporary files and serve via HTTP server
2. **Option 2**: Upload images to cloud storage (AWS S3, Google Cloud Storage)
3. **Option 3**: Use Odoo's built-in image URLs if available

## Error Handling and Logging

### Progress Tracking
- Track successful uploads, failures, and API rate limits
- Log Google Merchant API responses and errors
- Implement retry logic for failed uploads

### Rate Limiting
- Google Merchant API has quotas (check current limits)
- Implement exponential backoff for rate limit errors
- Batch requests when possible

## File Structure

```
├── .env                              # Environment configuration
├── 27.Importador_directo_odoo.py     # Existing Odoo importer
├── google_merchant_sync.py           # Main Google Merchant sync script (to be created)
├── Workflow/
│   ├── Articulos_a_subir.xlsx       # Product data source
│   ├── images/                      # Product images directory
│   ├── merchant_sync_progress.json  # Sync progress tracking
│   └── merchant_sync_errors.json    # Error log file
```

## Environment Variables

Add to `.env` file:
```bash
# Existing Odoo configuration
ODOO_URL=https://www.klavier.es
ODOO_DB=onmi-engineering-gestion-klavier-main-20096465
ODOO_API_KEY=35d79c7ee1adcf887d9d34478e532995420fbe37
ODOO_USER=admin@klavier.es
ODOO_PASSWORD=admin2021.klavier

# Google Merchant API configuration (New API)
GOOGLE_MERCHANT_ID=your_merchant_id
GOOGLE_DATA_SOURCE_ID=your_data_source_id
GOOGLE_CREDENTIALS_FILE=path/to/service-account.json
WEBSITE_BASE_URL=https://www.klavier.es
DEFAULT_CURRENCY=EUR
DEFAULT_COUNTRY=ES
DEFAULT_LANGUAGE=es
```

## Security Considerations

- Store Google API credentials securely (service account JSON file)
- Use HTTPS for all API communications
- Implement proper error handling to avoid exposing sensitive data
- Validate all product data before sending to Google Merchant

## Dependencies

### Existing Dependencies
- `pandas`: Data processing
- `xmlrpc.client`: Odoo API communication
- `python-dotenv`: Environment variables
- `openpyxl`: Excel file reading

### Dependencies for New Google Merchant API
- `google-auth`: Google authentication
- `google-auth-oauthlib`: OAuth flow  
- `google-auth-httplib2`: HTTP transport
- `google-shopping-merchant-products`: New Merchant API client (replaces google-api-python-client)

## Implementation Notes

### Product ID Strategy
- Use Odoo product template ID as Google Merchant product ID
- Ensure IDs are unique and consistent across syncs
- Handle product updates vs. new insertions

### Sync Strategy
- Full sync: Extract all qualifying products and sync to Google Merchant
- Incremental sync: Track changes and sync only modified products
- Implement conflict resolution for concurrent updates

### Testing
- Start with test Merchant Center account
- Validate product data format before API calls
- Test with small batches before full sync