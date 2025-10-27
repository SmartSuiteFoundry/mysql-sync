# SmartSuite Field Types Reference

This document describes all supported SmartSuite field types and how to configure them in your sync mappings.

## Quick Reference

| Field Type | MySQL Example | SmartSuite Format | Config Type |
|------------|---------------|-------------------|-------------|
| Text | `VARCHAR` | `"string"` | `text` |
| Textarea | `TEXT` | `"string"` | `textarea` |
| Number | `INT`, `DECIMAL` | `"123.45"` (string) | `number` |
| Currency | `DECIMAL` | `"99.99"` (string) | `currency` |
| Date | `DATE`, `DATETIME` | `{"date": "ISO", "include_time": bool}` | `date` |
| Single Select | `ENUM` | `"choice_id"` (string) | `singleselect` |
| Yes/No | `BOOLEAN` | `true/false` | `yesno` |
| Email | `VARCHAR` | `["email@example.com"]` (array) | `emailfield` |
| Phone | `VARCHAR` | `[{"number": "555-1234"}]` (array) | `phonefield` |

## Configuration Format

### New Format (Recommended)

```yaml
destination:
  field_types:
    field_name:
      type: "field_type"
      # Additional options...
```

### Legacy Format (Still Supported)

```yaml
destination:
  transformations:
    field_name:
      type: "transformation_type"
      # Options...
```

## Field Type Details

### Text Fields

#### text
Basic text field.

```yaml
field_types:
  customer_name:
    type: "text"
```

**MySQL types**: `VARCHAR`, `CHAR`, `TEXT`
**SmartSuite format**: `"string value"`
**Example**: `"John Doe"`

#### textarea
Long text field with line breaks.

```yaml
field_types:
  description:
    type: "textarea"
```

**MySQL types**: `TEXT`, `MEDIUMTEXT`, `LONGTEXT`
**SmartSuite format**: `"multi\nline\ntext"`
**Example**: `"Line 1\nLine 2\nLine 3"`

#### title
Record title field (same as text).

```yaml
field_types:
  order_number:
    type: "title"
```

**MySQL types**: `VARCHAR`
**SmartSuite format**: `"string"`
**Example**: `"ORD-2024-001"`

---

### Number Fields

#### number
Numeric field (stored as string in SmartSuite).

```yaml
field_types:
  quantity:
    type: "number"
```

**MySQL types**: `INT`, `BIGINT`, `DECIMAL`, `FLOAT`, `DOUBLE`
**SmartSuite format**: `"123.45"` (string)
**Example**: MySQL `123.45` → SmartSuite `"123.45"`

**Note**: Automatically converts `Decimal` objects to strings.

#### currency
Currency/money field (stored as string).

```yaml
field_types:
  price:
    type: "currency"
```

**MySQL types**: `DECIMAL(10,2)`
**SmartSuite format**: `"99.99"` (string)
**Example**: MySQL `Decimal('99.99')` → SmartSuite `"99.99"`

#### percent
Percentage field (stored as string).

```yaml
field_types:
  discount:
    type: "percent"
```

**MySQL types**: `DECIMAL`, `FLOAT`
**SmartSuite format**: `"15.5"` (string)
**Example**: MySQL `15.5` → SmartSuite `"15.5"`

---

### Date Fields

#### date
Date and/or datetime field.

```yaml
field_types:
  # Date only (no time)
  order_date:
    type: "date"
    include_time: false

  # Date and time
  created_at:
    type: "date"
    include_time: true
```

**MySQL types**: `DATE`, `DATETIME`, `TIMESTAMP`
**SmartSuite format**:
```json
{
  "date": "2024-01-15T10:30:00",
  "include_time": true
}
```

**Options**:
- `include_time`: `true` to include time, `false` for date only (default: `false`)

**Examples**:

| MySQL Value | include_time | SmartSuite Format |
|-------------|--------------|-------------------|
| `date(2024-01-15)` | `false` | `{"date": "2024-01-15T00:00:00", "include_time": false}` |
| `datetime(2024-01-15 14:30:00)` | `true` | `{"date": "2024-01-15T14:30:00", "include_time": true}` |

---

### Choice Fields

#### singleselect
Single selection dropdown field.

```yaml
field_types:
  status:
    type: "singleselect"
    value_map:
      "active": "Active"
      "inactive": "Inactive"
      "pending": "Pending"
```

**MySQL types**: `ENUM`, `VARCHAR`
**SmartSuite format**: `"choice_id"` or `"choice_value"`

**value_map**: Maps MySQL values to SmartSuite choice IDs/values.

**Example**:
- MySQL: `"active"`
- Config maps to: `"Active"`
- SmartSuite receives: `"Active"`

**Without value_map**: Value is passed as-is (must match SmartSuite choice exactly).

#### multipleselectfield
Multiple selection field (tags, multi-select dropdown).

```yaml
field_types:
  tags:
    type: "multipleselectfield"
    value_map:
      "urgent": "Urgent"
      "important": "Important"
```

**MySQL types**: `SET`, comma-separated `VARCHAR`
**SmartSuite format**: `["choice_id1", "choice_id2"]` (array)

**Example**:
- MySQL: `"urgent,important"` or `["urgent", "important"]`
- SmartSuite: `["Urgent", "Important"]`

---

### Boolean Fields

#### yesno
Yes/No checkbox field.

```yaml
field_types:
  is_active:
    type: "yesno"
```

**MySQL types**: `BOOLEAN`, `TINYINT(1)`, `ENUM('yes','no')`
**SmartSuite format**: `true` or `false`

**Conversion**:
- MySQL `true`, `1`, `"yes"`, `"y"`, `"t"`, `"on"` → SmartSuite `true`
- Everything else → SmartSuite `false`

---

### Contact Fields

#### emailfield
Email address field.

```yaml
field_types:
  email:
    type: "emailfield"
```

**MySQL types**: `VARCHAR`
**SmartSuite format**: `["email@example.com"]` (array of strings)

**Examples**:
- MySQL: `"john@example.com"` → SmartSuite: `["john@example.com"]`
- MySQL: `["john@ex.com", "jane@ex.com"]` → SmartSuite: `["john@ex.com", "jane@ex.com"]`

#### phonefield
Phone number field.

```yaml
field_types:
  phone:
    type: "phonefield"
    default_country: "US"  # Optional: default country code
    default_type: 2  # Optional: 1=office, 2=mobile, 4=home, 5=fax, 8=other
```

**MySQL types**: `VARCHAR`
**SmartSuite format**: Array of phone objects (only 4 required fields)
```json
[
  {
    "phone_country": "US",
    "phone_number": "555-1234",
    "phone_extension": "",
    "phone_type": 2
  }
]
```

**Note**: `sys_root` and `sys_title` are NOT required (they are system-generated by SmartSuite)

**Phone type values**:
- `1` = Office
- `2` = Mobile (default)
- `4` = Home
- `5` = Fax
- `8` = Other

**Simple example** (just phone number string):
- MySQL: `"555-0101"`
- SmartSuite receives:
```json
[{
  "phone_country": "US",
  "phone_number": "555-0101",
  "phone_extension": "",
  "phone_type": 2
}]
```

**Complex example** (custom phone object from MySQL):
- MySQL: `{"number": "555-1234", "country": "CA", "extension": "123", "type": 1}`
- SmartSuite receives:
```json
[{
  "phone_country": "CA",
  "phone_number": "555-1234",
  "phone_extension": "123",
  "phone_type": 1
}]
```

**Real example** (from SmartSuite):
- Matches the format: `"913 553 7700"` with type `1` (office) becomes:
```json
[{
  "phone_country": "US",
  "phone_number": "913 553 7700",
  "phone_extension": "",
  "phone_type": 1
}]
```

**Options**:
- `default_country`: Country code to use (default: "US")
- `default_type`: Phone type number (default: 2 for mobile)

---

### Link Fields

#### linkfield
URL/link field.

```yaml
field_types:
  website:
    type: "linkfield"
```

**MySQL types**: `VARCHAR`
**SmartSuite format**: `["https://example.com"]` (array of strings)

**Example**:
- MySQL: `"https://example.com"` → SmartSuite: `["https://example.com"]`

---

### Relationship Fields

#### linkedrecordfield
Linked record field (relationship to another table).

```yaml
field_types:
  customer_id:
    type: "linkedrecordfield"
```

**MySQL types**: Foreign key `INT`, `VARCHAR`
**SmartSuite format**: `["record_id_1", "record_id_2"]` (array of record IDs)

**Example**:
- MySQL: `123` → SmartSuite: `["123"]`
- MySQL: `[123, 456]` → SmartSuite: `["123", "456"]`

**Note**: You need to provide the SmartSuite record IDs, not the MySQL IDs. Use a lookup or separate sync to get these.

#### memberfield
Assigned to / member field.

```yaml
field_types:
  assigned_to:
    type: "memberfield"
```

**MySQL types**: `VARCHAR` (user ID), `INT`
**SmartSuite format**: `["member_id_1"]` (array of member IDs)

**Example**:
- MySQL: `"user_123"` → SmartSuite: `["user_123"]`

**Note**: You need SmartSuite member IDs from your workspace.

---

## Auto-Conversion

If you don't specify a field type, the system automatically converts common Python/MySQL types:

| Python Type | Auto-Converted To |
|-------------|-------------------|
| `Decimal` | String number `"123.45"` |
| `datetime` | Date object `{"date": "ISO", "include_time": true}` |
| `date` | Date object `{"date": "ISO", "include_time": false}` |
| `bool` | Boolean `true`/`false` |
| `int`/`float` | String `"123"` |
| `str` | String (unchanged) |
| `bytes` | UTF-8 string |

## Complete Example

```yaml
syncs:
  - name: "orders_sync"
    enabled: true

    source:
      query: "SELECT * FROM orders"
      primary_key: "id"

    destination:
      table_id: "table_abc123"

      field_mappings:
        id: "order_id"
        order_number: "title"
        customer_name: "customer"
        total: "total_amount"
        status: "order_status"
        order_date: "order_date"
        notes: "notes"
        is_paid: "is_paid"
        email: "customer_email"
        phone: "customer_phone"

      external_id_field: "order_id"

      field_types:
        # Number fields
        id:
          type: "number"
        total:
          type: "currency"

        # Date fields
        order_date:
          type: "date"
          include_time: false

        # Choice fields
        status:
          type: "singleselect"
          value_map:
            "pending": "Pending"
            "shipped": "Shipped"

        # Text fields
        notes:
          type: "textarea"

        # Boolean
        is_paid:
          type: "yesno"

        # Contact fields
        email:
          type: "emailfield"
        phone:
          type: "phonefield"
```

## Common Issues

### Issue: "Object of type Decimal is not JSON serializable"

**Solution**: Add field type definition:
```yaml
field_types:
  amount:
    type: "currency"  # or "number"
```

### Issue: "Object of type datetime is not JSON serializable"

**Solution**: Add field type definition:
```yaml
field_types:
  created_at:
    type: "date"
    include_time: true
```

### Issue: Choice values not matching

**Problem**: MySQL has `"active"` but SmartSuite expects `"Active"` (capital A).

**Solution**: Use `value_map`:
```yaml
field_types:
  status:
    type: "singleselect"
    value_map:
      "active": "Active"
      "inactive": "Inactive"
```

### Issue: Date showing wrong time

**Problem**: Date-only fields showing times.

**Solution**: Set `include_time: false`:
```yaml
field_types:
  birth_date:
    type: "date"
    include_time: false
```

## Migration from Legacy Format

### Before (Legacy)
```yaml
transformations:
  price:
    type: "number"
    format: "float"
  status:
    type: "choice"
    value_map:
      "active": "Active"
  order_date:
    type: "date"
    format: "%Y-%m-%d"
```

### After (New Format)
```yaml
field_types:
  price:
    type: "currency"  # or "number"
  status:
    type: "singleselect"
    value_map:
      "active": "Active"
  order_date:
    type: "date"
    include_time: false
```

**Note**: Legacy format still works! No need to migrate immediately.

## Summary of SmartSuite Field Types

### Supported Types

| Config Value | SmartSuite Field | Format |
|--------------|------------------|--------|
| `text` | Text | String |
| `textarea` | Text Area | String |
| `title` | Title | String |
| `number` | Number | String |
| `currency` | Currency | String |
| `percent` | Percent | String |
| `date` | Date | Object `{date, include_time}` |
| `singleselect` | Single Select | String (choice ID) |
| `multipleselectfield` | Multiple Select | Array of strings |
| `yesno` | Yes/No | Boolean |
| `emailfield` | Email | Array of strings |
| `phonefield` | Phone | Array of phone objects |
| `linkfield` | Link | Array of strings |
| `linkedrecordfield` | Linked Record | Array of record IDs |
| `memberfield` | Member | Array of member IDs |

### Not Yet Implemented

These SmartSuite field types are not yet supported but could be added:

- Address
- Checklist
- Color Picker
- Full Name
- IP Address
- SmartDoc
- Social Network
- Date Range
- Due Date
- Duration
- Time
- Rating
- Vote
- Files and Images
- Signature

If you need any of these, please add custom handling in `config_loader.py`.
