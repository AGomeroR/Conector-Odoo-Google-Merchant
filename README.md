# Odoo to Google Merchant Center Integration

This project provides automated synchronization of product data from Odoo ERP to Google Merchant Center, enabling seamless e-commerce product visibility across Google Shopping and other Google services.

## Overview

The integration extracts products from Odoo that meet specific criteria and uploads them to Google Merchant Center using the new Merchant API (v1). This ensures your product catalog is always up-to-date across platforms.

## Features

- **Automated Product Extraction**: Pulls products from Odoo based on configurable criteria
- **Google Merchant API Integration**: Uses the latest Merchant API (v1) for reliable product uploads
- **Flexible Authentication**: Supports both API key and username/password authentication for Odoo
- **Image Handling**: Converts Odoo's base64-encoded images to accessible URLs
- **Progress Tracking**: Comprehensive logging and error handling
- **Dry Run Mode**: Test synchronization without making actual changes
- **Image Management**: Optional image cleanup to save disk space

## Prerequisites

- Python 3.7+
- Odoo instance with API access
- Google Merchant Center account
- Google Cloud Project with Merchant API enabled
- Service Account credentials for Google API authentication

## Installation

1. Clone the repository:
```bash
cd Conexion-Odoo-con-Google-Merchant
```

2. Install required dependencies:
```bash
pip install pandas xmlrpc openpyxl python-dotenv google-auth google-auth-oauthlib google-auth-httplib2 google-shopping-merchant-products
```

3. Set up Google Cloud credentials (see Google API Setup section)

4. Create a `.env` file in the project root (see Configuration section)

## Google API Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your Project ID

### 2. Enable the Merchant API

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Merchant API" (NOT "Content API for Shopping")
3. Click **Enable**

### 3. Create a Service Account

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **Service Account**
3. Fill in the service account details:
   - Name: `merchant-sync-service`
   - Description: `Service account for Odoo to Google Merchant synchronization`
4. Click **Create and Continue**
5. Grant the service account the role: **Merchant API Editor**
6. Click **Done**

### 4. Generate Service Account Key (JSON)

1. In **Credentials**, click on the service account you just created
2. Go to the **Keys** tab
3. Click **Add Key** > **Create new key**
4. Select **JSON** format
5. Click **Create**
6. A JSON file will be downloaded to your computer

**Important**: This JSON file contains sensitive credentials. Store it securely!

### 5. Save the Credentials File

1. Rename the downloaded file to something memorable (e.g., `google-merchant-credentials.json`)
2. Move it to your project directory or a secure location
3. Update the `GOOGLE_CREDENTIALS_FILE` path in your `.env` file

**Example structure of the JSON file:**
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "merchant-sync-service@your-project-id.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

### 6. Link to Google Merchant Center

1. Go to [Google Merchant Center](https://merchants.google.com/)
2. Navigate to **Settings** > **Account access** > **Developer**
3. Add your Google Cloud Project ID
4. Note your Merchant Center ID (visible in the URL or Settings)

### 7. Configure Data Source

1. In Merchant Center, go to **Products** > **Feeds**
2. Create a new data source or note your existing data source ID
3. Add the data source ID to your `.env` file

## Configuration

Create a `.env` file in the project root with the following variables:

```bash
# Odoo Configuration
ODOO_URL=https://your-odoo-instance.com
ODOO_DB=your_database_name
ODOO_API_KEY=your_api_key_here
# OR use username/password (API key is preferred)
ODOO_USER=your_username
ODOO_PASSWORD=your_password

# Google Merchant API Configuration
GOOGLE_MERCHANT_ID=1234567890
GOOGLE_DATA_SOURCE_ID=1234567890
GOOGLE_CREDENTIALS_FILE=./google-merchant-credentials.json
WEBSITE_BASE_URL=https://your-website.com
DEFAULT_CURRENCY=EUR
DEFAULT_COUNTRY=ES
DEFAULT_LANGUAGE=es
```

### Product Criteria

Products are automatically filtered and only synced if they meet ALL of these criteria:
- `website_published = True` (published on website)
- Has an image (`image_1920` field is not empty)
- Has `website_description` (not empty)
- Has `list_price` greater than 0

## Usage

### Google Merchant Sync

Synchronize products to Google Merchant Center:

```bash
# Test run without making actual changes
python google_merchant_sync.py --dry-run

# Full synchronization to Google Merchant
python google_merchant_sync.py
```

## Project Structure

```
├── .env                                    # Environment configuration (DO NOT COMMIT)
├── .gitignore                              # Git ignore file
├── README.md                               # This file
├── CLAUDE.md                               # Development guidelines
├── google-merchant-credentials.json        # Google service account (DO NOT COMMIT)
├── 27.Importador_directo_odoo.py           # Odoo product importer
├── google_merchant_sync.py                 # Google Merchant sync script
└── Workflow/
    ├── Articulos_a_subir.xlsx             # Product data export
    ├── images/                            # Downloaded product images
    ├── merchant_sync_progress.json        # Sync progress tracking
    └── merchant_sync_errors.json          # Error logs
```

## Field Mapping

| Odoo Field | Google Merchant Field | Notes |
|------------|----------------------|-------|
| `name` | `attributes.title` | Max 150 characters |
| `website_description` | `attributes.description` | Max 5000 characters |
| `image_1920` | `attributes.image_link` | Base64 converted to URL |
| `list_price` | `attributes.price` | Converted to micros format |
| `id` | `offer_id` | Prefixed with "odoo_" |

Additional required fields automatically set:
- `attributes.link`: Product page URL
- `attributes.availability`: "in stock"
- `attributes.condition`: "new"
- `content_language`: Language code (e.g., "es")
- `feed_label`: Target country (e.g., "ES")
- `channel`: "ONLINE"

## Google Merchant API

This project uses the **new Merchant API (v1)** which replaces the Content API for Shopping (being discontinued in August 2026).

### Key Differences
- Uses `productInputs` instead of direct `products` endpoint
- Requires data source configuration in Merchant Center
- Different authentication and project setup requirements

### API Endpoints
- **Base URL**: `https://merchantapi.googleapis.com`
- **Insert Product**: `POST /products/v1/accounts/{merchantId}/productInputs:insert`

## Error Handling

The system includes comprehensive error handling:
- Tracks successful uploads and failures
- Logs all API responses and errors
- Implements retry logic for transient failures
- Respects Google API rate limits with exponential backoff

Progress and errors are logged to:
- `Workflow/merchant_sync_progress.json`
- `Workflow/merchant_sync_errors.json`

## Security Considerations

### Critical Security Rules

1. **Never commit sensitive files to version control**:
   - `.env` file
   - `google-merchant-credentials.json`
   - Any files containing API keys or passwords

2. **Use `.gitignore`** to exclude sensitive files

3. **Store credentials securely**:
   - Keep service account JSON in a secure location
   - Use environment variables for all sensitive data
   - Limit file permissions on credential files

4. **API Security**:
   - Use HTTPS for all API communications
   - Keep service account permissions minimal (principle of least privilege)
   - Rotate credentials periodically
   - Monitor API usage for suspicious activity

5. **Validate all data** before sending to external APIs

### Recommended File Permissions

```bash
chmod 600 .env
chmod 600 google-merchant-credentials.json
```

## Troubleshooting

### Common Issues

**Authentication Errors**
- Verify your Odoo API key or credentials in `.env`
- Check that the service account JSON file path is correct
- Ensure the service account has proper permissions in Google Cloud

**Google API Errors**
- Verify Merchant API is enabled in Google Cloud Console
- Check that your project is linked to Merchant Center
- Ensure data source ID is correct

**Missing Products**
- Check that products meet all required criteria:
  - `website_published = True`
  - Has image
  - Has description
  - Price > 0

**Image Upload Failures**
- Verify images are accessible via URL
- Check image format and size meet Google's requirements
- Ensure proper base64 to URL conversion

**Rate Limiting**
- The script implements automatic retry with exponential backoff
- Check Google API quotas in Cloud Console
- Consider batching requests for large catalogs

## Development

For detailed development guidelines and technical documentation, see [CLAUDE.md](CLAUDE.md).

### Testing

Always test changes with `--dry-run` mode first:
```bash
python google_merchant_sync.py --dry-run
```

## License

[Add your license information here]

## Support

For issues and questions, please open an issue in the repository or contact the development team.

## Additional Resources

- [Google Merchant API Documentation](https://developers.google.com/merchant/api)
- [Odoo XML-RPC API Documentation](https://www.odoo.com/documentation/16.0/developer/api/external_api.html)
- [Google Cloud Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [Google Merchant Center Help](https://support.google.com/merchants/)

---

## Author

**Alvaro Gómez**
Email: gomex1994@gmail.com
Year: 2025
