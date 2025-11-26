# Google Merchant Center - Requisitos Completos para Indexar Productos

## 📋 Campos Obligatorios (CRÍTICOS)

Estos campos son **OBLIGATORIOS** para todos los productos. Sin ellos, Google no indexará el producto.

| Campo | Descripción | Formato | Ejemplo | Estado en Odoo |
|-------|-------------|---------|---------|----------------|
| `id` | Identificador único del producto | String (máx 50 chars) | `odoo_12345` | ✅ Implementado |
| `title` | Nombre del producto | String (máx 150 chars) | `Camiseta Azul Algodón` | ✅ Implementado (`name`) |
| `description` | Descripción detallada | String (500+ chars) | `Camiseta 100% algodón...` | ✅ Implementado (`website_description`) |
| `link` | URL de la página del producto | URL válida | `https://klavier.es/product/123` | ✅ Implementado |
| `image_link` | URL de imagen principal | URL válida | `http://localhost:8081/img.jpg` | ✅ Implementado |
| `availability` | Estado de disponibilidad | `in stock` \| `out of stock` \| `preorder` | `in stock` | ✅ Implementado (fijo) |
| `price` | Precio del producto | `{amount_micros, currency_code}` | `{29990000, "EUR"}` | ✅ Implementado |
| `condition` | Estado del producto | `new` \| `used` \| `refurbished` | `new` | ✅ Implementado (fijo) |
| `brand` | Marca del producto | String | `Klavier` | ✅ Implementado (fijo) |

## ⚠️ Campos Condicionales (IMPORTANTES)

Obligatorios según el tipo de producto o circunstancias específicas.

### Para Productos con Código de Barras
| Campo | Descripción | Cuándo es Obligatorio | Estado en Odoo |
|-------|-------------|-----------------------|----------------|
| `gtin` | Código de barras global | Productos nuevos con GTIN del fabricante | ❌ **FALTA** |
| `mpn` | Número de parte del fabricante | Si no hay GTIN disponible | ✅ Implementado (`default_code`) |
| `identifier_exists` | Indica si existen identificadores | Productos sin GTIN/MPN | ❌ **FALTA** |

### Para Ropa y Accesorios
| Campo | Descripción | Ejemplo | Estado en Odoo |
|-------|-------------|---------|----------------|
| `gender` | Género objetivo | `male` \| `female` \| `unisex` | ❌ **FALTA** |
| `age_group` | Grupo de edad | `newborn` \| `infant` \| `toddler` \| `kids` \| `adult` | ❌ **FALTA** |
| `color` | Color del producto | `Azul`, `Rojo` | ❌ **FALTA** |
| `size` | Talla del producto | `M`, `L`, `42` | ❌ **FALTA** |
| `material` | Material principal | `Algodón`, `Cuero` | ❌ **FALTA** |

## 🚀 Campos Opcionales Altamente Recomendados

Mejoran significativamente la indexación y visibilidad.

### Información Adicional del Producto
| Campo | Descripción | Beneficio | Estado en Odoo |
|-------|-------------|-----------|----------------|
| `google_product_category` | Categoría de Google | Mejor clasificación | ❌ **FALTA** |
| `product_type` | Categoría personalizada | Organización interna | ✅ Disponible (`categ_id`) |
| `sale_price` | Precio de oferta | Promociones | ❌ **FALTA** |
| `sale_price_effective_date` | Fechas de la oferta | Promociones temporales | ❌ **FALTA** |
| `item_group_id` | Agrupación de variantes | Productos relacionados | ❌ **FALTA** |

### Información de Envío
| Campo | Descripción | Ejemplo | Estado en Odoo |
|-------|-------------|---------|----------------|
| `shipping` | Configuración de envío | `{price: 5.99, country: "ES"}` | ❌ **FALTA** |
| `shipping_weight` | Peso del producto | `0.5 kg` | ✅ Disponible (`weight`) |
| `shipping_length` | Largo del paquete | `30 cm` | ❌ **FALTA** |
| `shipping_width` | Ancho del paquete | `20 cm` | ❌ **FALTA** |
| `shipping_height` | Alto del paquete | `10 cm` | ❌ **FALTA** |

### Información Adicional
| Campo | Descripción | Estado en Odoo |
|-------|-------------|----------------|
| `custom_label_0` | Etiqueta personalizada 1 | ❌ **FALTA** |
| `custom_label_1` | Etiqueta personalizada 2 | ❌ **FALTA** |
| `custom_label_2` | Etiqueta personalizada 3 | ❌ **FALTA** |
| `ads_redirect` | URL alternativa para anuncios | ❌ **FALTA** |

## 🆕 Novedades 2024-2025

### Implementadas en 2024
| Campo | Descripción | Obligatorio | Estado |
|-------|-------------|-------------|--------|
| `structured_title` | Título generado por IA | Si se usa IA | ❌ **FALTA** |
| `structured_description` | Descripción generada por IA | Si se usa IA | ❌ **FALTA** |
| `loyalty_program` | Programa de fidelización | Para precios de miembro | ❌ **FALTA** |

### Cambios en 2025
| Campo | Cambio | Fecha | Impacto |
|-------|--------|-------|---------|
| `member_price` | Ya no en `price` principal | Julio 2025 | Debe usar `loyalty_program` |
| `tax` | Ya no requerido (US) | Julio 2025 | Simplificación para US |
| `certification` | Reemplaza `energy_efficiency_class` | Abril 2025 | Solo productos EU |

## 📊 Estado Actual de la Integración

### ✅ Implementados (9/10 Críticos)
- `id`, `title`, `description`, `link`, `image_link`
- `availability`, `price`, `condition`, `brand`

### ❌ Campos Críticos Faltantes (1/10)
- `gtin` o `identifier_exists` - **CRÍTICO**

### ❌ Campos Importantes Faltantes
- **Identificadores**: `gtin`, `identifier_exists`
- **Ropa**: `gender`, `age_group`, `color`, `size`, `material`
- **Categorización**: `google_product_category`
- **Promociones**: `sale_price`, `sale_price_effective_date`
- **Envío**: `shipping`, dimensiones del paquete

## 🔧 Recomendaciones de Implementación

### Prioridad 1 - CRÍTICO
1. **Implementar `identifier_exists`** para productos sin GTIN
2. **Mapear `gtin`** desde campo personalizado de Odoo si existe

### Prioridad 2 - ALTO
1. **Mapear `google_product_category`** desde categorías de Odoo
2. **Implementar `sale_price`** desde listas de precios de Odoo
3. **Extraer atributos de ropa** (`color`, `size`, etc.) desde variantes

### Prioridad 3 - MEDIO
1. **Configurar información de envío** básica
2. **Implementar etiquetas personalizadas**
3. **Añadir dimensiones del paquete**

## 📝 Mapeo Odoo → Google Merchant

### Campos ya Mapeados
```python
# Mapeo actual en el script
"name" → "attributes.title"
"website_description" → "attributes.description" 
"list_price" → "attributes.price"
"image_1920" → "attributes.image_link"
"default_code" → "attributes.mpn" (si existe)
```

### Campos Disponibles en Odoo para Mapear
```python
# Disponibles pero no implementados
"weight" → "shipping_weight"
"categ_id" → "product_type" / "google_product_category"
"public_categ_ids" → categorización adicional
```

### Campos que Necesitan Configuración Manual
```python
# Requieren configuración en Odoo
- GTIN (campo personalizado x_studio_gtin)
- Gender (atributo de producto)
- Age Group (atributo de producto) 
- Color (variante de producto)
- Size (variante de producto)
- Material (atributo de producto)
```

## 🎯 Plan de Mejora

1. **Implementar `identifier_exists`** inmediatamente
2. **Añadir campos opcionales importantes** progresivamente
3. **Configurar atributos en Odoo** para ropa y accesorios
4. **Validar cumplimiento** antes de envío a Google Merchant
5. **Monitorear cambios 2025** y implementar cuando sea necesario

Este documento asegura que los productos cumplan con todos los requisitos de Google Merchant Center para una indexación exitosa.