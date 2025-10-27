"""
Configuration Loader
-------------------
Loads and validates sync configuration from YAML files.
Handles SmartSuite field type conversions.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class SmartSuiteFieldConverter:
    """Converts values to SmartSuite field type formats."""

    @staticmethod
    def convert(value: Any, field_type: str, **options) -> Any:
        """
        Convert a value to the appropriate SmartSuite field format.

        Args:
            value: The value to convert
            field_type: SmartSuite field type (text, number, date, etc.)
            **options: Additional options like value_map, include_time, etc.

        Returns:
            Converted value in SmartSuite format
        """
        if value is None:
            return SmartSuiteFieldConverter._null_value_for_type(field_type)

        # Map field types to conversion methods
        converters = {
            'text': SmartSuiteFieldConverter.to_text,
            'textarea': SmartSuiteFieldConverter.to_textarea,
            'title': SmartSuiteFieldConverter.to_text,
            'number': SmartSuiteFieldConverter.to_number,
            'currency': SmartSuiteFieldConverter.to_currency,
            'percent': SmartSuiteFieldConverter.to_percent,
            'date': SmartSuiteFieldConverter.to_date,
            'singleselect': SmartSuiteFieldConverter.to_single_select,
            'multipleselectfield': SmartSuiteFieldConverter.to_multiple_select,
            'yesno': SmartSuiteFieldConverter.to_yesno,
            'emailfield': SmartSuiteFieldConverter.to_email,
            'phonefield': SmartSuiteFieldConverter.to_phone,
            'linkfield': SmartSuiteFieldConverter.to_link,
            'linkedrecordfield': SmartSuiteFieldConverter.to_linked_record,
            'memberfield': SmartSuiteFieldConverter.to_assigned_to,
        }

        converter = converters.get(field_type.lower())
        if converter:
            return converter(value, **options)

        # Default: convert to string
        return SmartSuiteFieldConverter.to_text(value)

    @staticmethod
    def _null_value_for_type(field_type: str) -> Any:
        """Return appropriate null value for field type."""
        array_types = ['multipleselectfield', 'emailfield', 'phonefield',
                      'linkfield', 'linkedrecordfield', 'memberfield']
        if field_type.lower() in array_types:
            return []
        if field_type.lower() == 'yesno':
            return False
        if field_type.lower() in ['number', 'currency', 'percent']:
            return "0"
        if field_type.lower() == 'date':
            return {"date": None, "include_time": False}
        return ""

    @staticmethod
    def to_text(value: Any, **options) -> str:
        """Convert to text/title field."""
        return str(value) if value is not None else ""

    @staticmethod
    def to_textarea(value: Any, **options) -> str:
        """Convert to textarea field."""
        return str(value) if value is not None else ""

    @staticmethod
    def to_number(value: Any, **options) -> str:
        """Convert to number field (string format required by SmartSuite)."""
        if isinstance(value, Decimal):
            return str(float(value))
        return str(float(value)) if value is not None else "0"

    @staticmethod
    def to_currency(value: Any, **options) -> str:
        """Convert to currency field (string format)."""
        if isinstance(value, Decimal):
            return str(float(value))
        return str(float(value)) if value is not None else "0"

    @staticmethod
    def to_percent(value: Any, **options) -> str:
        """Convert to percent field (string format)."""
        if isinstance(value, Decimal):
            return str(float(value))
        return str(float(value)) if value is not None else "0"

    @staticmethod
    def to_date(value: Any, **options) -> Dict[str, Any]:
        """
        Convert to date field object.

        SmartSuite format: {"date": "ISO8601", "include_time": boolean}
        """
        include_time = options.get('include_time', False)

        if value is None:
            return {"date": None, "include_time": include_time}

        # Handle different date/time types
        if isinstance(value, datetime):
            return {
                "date": value.isoformat(),
                "include_time": True  # datetime always includes time
            }
        elif isinstance(value, date):
            # Date only - convert to datetime at midnight
            dt = datetime.combine(value, datetime.min.time())
            return {
                "date": dt.isoformat(),
                "include_time": include_time
            }
        elif isinstance(value, str):
            # Try to parse ISO format
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return {
                    "date": dt.isoformat(),
                    "include_time": include_time
                }
            except:
                # Return as-is if can't parse
                return {
                    "date": value,
                    "include_time": include_time
                }

        return {
            "date": str(value),
            "include_time": include_time
        }

    @staticmethod
    def to_single_select(value: Any, **options) -> str:
        """
        Convert to single select field.

        Use value_map to convert database values to SmartSuite choice IDs.
        """
        value_map = options.get('value_map', {})
        str_value = str(value) if value is not None else ""

        # Map value if mapping provided
        if value_map and str_value in value_map:
            return value_map[str_value]

        return str_value

    @staticmethod
    def to_multiple_select(value: Any, **options) -> List[str]:
        """Convert to multiple select field (array of choice IDs)."""
        value_map = options.get('value_map', {})

        if value is None:
            return []

        if isinstance(value, (list, tuple)):
            values = [str(v) for v in value if v is not None]
        else:
            values = [str(value)]

        # Apply value mapping if provided
        if value_map:
            return [value_map.get(v, v) for v in values]

        return values

    @staticmethod
    def to_yesno(value: Any, **options) -> bool:
        """Convert to yes/no field (boolean)."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 't', 'y', 'on')
        return bool(value)

    @staticmethod
    def to_email(value: Any, **options) -> List[str]:
        """Convert to email field (array of strings)."""
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value if v]
        return [str(value)] if value else []

    @staticmethod
    def to_phone(value: Any, **options) -> List[Dict[str, Any]]:
        """
        Convert to phone field (array of phone objects).

        SmartSuite phone format (only these 4 fields required):
        [
            {
                "phone_country": "US",
                "phone_number": "555-1234",
                "phone_extension": "",
                "phone_type": 2  # 1=office, 2=mobile, 4=home, 5=fax, 8=other
            }
        ]

        Note: sys_root and sys_title are NOT required (system-generated)
        """
        if value is None:
            return []

        default_country = options.get('default_country', 'US')
        default_type = options.get('default_type', 2)  # 2 = mobile

        phones = []

        # Handle array of phone values
        if isinstance(value, (list, tuple)):
            for v in value:
                if isinstance(v, dict):
                    # Already a dict, ensure SmartSuite format
                    phones.append(SmartSuiteFieldConverter._format_phone_object(v, default_country, default_type))
                elif v:
                    # Simple value, convert to phone object
                    phones.append(SmartSuiteFieldConverter._create_phone_object(str(v), default_country, default_type))
        elif value:
            # Single value
            if isinstance(value, dict):
                phones.append(SmartSuiteFieldConverter._format_phone_object(value, default_country, default_type))
            else:
                phones.append(SmartSuiteFieldConverter._create_phone_object(str(value), default_country, default_type))

        return phones

    @staticmethod
    def _create_phone_object(phone_number: str, country: str = 'US', phone_type: int = 2) -> Dict[str, Any]:
        """
        Create a SmartSuite phone object from a phone number string.

        Args:
            phone_number: Phone number string (e.g., "555-1234" or "(555) 123-4567")
            country: Country code (default: 'US')
            phone_type: Phone type (1=office, 2=mobile, 4=home, 5=fax, 8=other)

        Returns:
            SmartSuite phone object (only required fields)
        """
        return {
            "phone_country": country,
            "phone_number": phone_number,
            "phone_extension": "",
            "phone_type": phone_type
        }

    @staticmethod
    def _format_phone_object(phone_dict: Dict[str, Any], default_country: str = 'US', default_type: int = 2) -> Dict[str, Any]:
        """
        Ensure phone dict has all required SmartSuite fields.

        Args:
            phone_dict: Partial or complete phone object
            default_country: Default country if not specified
            default_type: Default phone type if not specified

        Returns:
            Complete SmartSuite phone object (only required fields)
        """
        # Extract phone number from various possible field names
        phone_number = (
            phone_dict.get('phone_number') or
            phone_dict.get('number') or
            phone_dict.get('phone') or
            str(phone_dict.get('value', ''))
        )

        # Extract other fields with fallbacks
        country = phone_dict.get('phone_country') or phone_dict.get('country') or default_country
        extension = phone_dict.get('phone_extension') or phone_dict.get('extension') or ""
        phone_type = phone_dict.get('phone_type') or phone_dict.get('type') or default_type

        # Convert phone_type to int if it's a string number
        if isinstance(phone_type, str) and phone_type.isdigit():
            phone_type = int(phone_type)
        elif not isinstance(phone_type, int):
            phone_type = default_type

        return {
            "phone_country": country,
            "phone_number": phone_number,
            "phone_extension": str(extension) if extension else "",
            "phone_type": phone_type
        }

    @staticmethod
    def to_link(value: Any, **options) -> List[str]:
        """Convert to link field (array of URLs)."""
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value if v]
        return [str(value)] if value else []

    @staticmethod
    def to_linked_record(value: Any, **options) -> List[str]:
        """Convert to linked record field (array of record IDs)."""
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value if v]
        return [str(value)] if value else []

    @staticmethod
    def to_assigned_to(value: Any, **options) -> List[str]:
        """Convert to assigned to/member field (array of member IDs)."""
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value if v]
        return [str(value)] if value else []


class SyncConfig:
    """Represents a single sync configuration."""

    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize sync configuration.

        Args:
            config_dict: Dictionary containing sync configuration
        """
        self.name = config_dict['name']
        self.enabled = config_dict.get('enabled', True)
        self.description = config_dict.get('description', '')

        # Source configuration
        source = config_dict['source']
        self.query = source['query']
        self.primary_key = source['primary_key']
        self.updated_at_field = source.get('updated_at_field')

        # Destination configuration
        destination = config_dict['destination']
        self.table_id = destination['table_id']
        self.field_mappings = destination['field_mappings']
        self.external_id_field = destination['external_id_field']
        self.field_types = destination.get('field_types', {})  # NEW: field type definitions
        self.transformations = destination.get('transformations', {})  # DEPRECATED: use field_types instead

    def transform_value(self, field_name: str, value: Any) -> Any:
        """
        Transform a field value to SmartSuite format.

        Args:
            field_name: Source field name
            value: Original value

        Returns:
            Transformed value in SmartSuite format
        """
        # Check if field has type definition
        if field_name in self.field_types:
            field_config = self.field_types[field_name]
            field_type = field_config.get('type', 'text')

            # Extract options from config
            options = {}
            if 'value_map' in field_config:
                options['value_map'] = field_config['value_map']
            if 'include_time' in field_config:
                options['include_time'] = field_config['include_time']

            # Convert using field type
            return SmartSuiteFieldConverter.convert(value, field_type, **options)

        # Legacy: check old transformations format
        if field_name in self.transformations:
            return self._legacy_transform(field_name, value)

        # No transformation defined - apply automatic conversion
        return self._auto_convert(value)

    def _legacy_transform(self, field_name: str, value: Any) -> Any:
        """Handle legacy transformation format (for backwards compatibility)."""
        transform = self.transformations[field_name]
        transform_type = transform.get('type')

        try:
            if transform_type == 'number':
                return SmartSuiteFieldConverter.to_number(value)
            elif transform_type == 'choice':
                value_map = transform.get('value_map', {})
                return SmartSuiteFieldConverter.to_single_select(value, value_map=value_map)
            elif transform_type == 'date':
                include_time = transform.get('include_time', False)
                return SmartSuiteFieldConverter.to_date(value, include_time=include_time)
        except Exception as e:
            logger.warning(f"Failed to transform {field_name}={value}: {e}")

        return self._auto_convert(value)

    def _auto_convert(self, value: Any) -> Any:
        """Automatic type conversion for common Python types."""
        if value is None:
            return None

        if isinstance(value, Decimal):
            return str(float(value))
        elif isinstance(value, datetime):
            # Auto-convert datetime to date field format
            return {
                "date": value.isoformat(),
                "include_time": True
            }
        elif isinstance(value, date):
            # Auto-convert date to date field format
            dt = datetime.combine(value, datetime.min.time())
            return {
                "date": dt.isoformat(),
                "include_time": False
            }
        elif isinstance(value, bytes):
            return value.decode('utf-8')
        elif isinstance(value, bool):
            return value
        elif isinstance(value, (int, float)):
            return str(value)

        return str(value)

    def map_record(self, source_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map a source record to SmartSuite format.

        Args:
            source_record: Source database record

        Returns:
            Mapped record for SmartSuite with correct field type formats
        """
        mapped = {}

        for source_field, smartsuite_field in self.field_mappings.items():
            if source_field in source_record:
                value = source_record[source_field]
                transformed_value = self.transform_value(source_field, value)
                mapped[smartsuite_field] = transformed_value

        return mapped

    def __repr__(self):
        return f"<SyncConfig name={self.name} enabled={self.enabled}>"


class ConfigLoader:
    """Loads sync configurations from YAML files."""

    def __init__(self, config_path: str = "config/sync_mappings.yml"):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)

    def load(self) -> List[SyncConfig]:
        """
        Load all sync configurations from YAML file.

        Returns:
            List of SyncConfig objects

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        logger.info(f"Loading configuration from {self.config_path}")

        with open(self.config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        syncs = []
        for sync_dict in config_data.get('syncs', []):
            try:
                sync_config = SyncConfig(sync_dict)
                syncs.append(sync_config)
                logger.info(f"Loaded sync config: {sync_config.name}")
            except Exception as e:
                logger.error(f"Failed to load sync config: {e}")
                logger.error(f"Config data: {sync_dict}")
                raise

        return syncs

    def get_enabled_syncs(self) -> List[SyncConfig]:
        """
        Get only enabled sync configurations.

        Returns:
            List of enabled SyncConfig objects
        """
        all_syncs = self.load()
        return [sync for sync in all_syncs if sync.enabled]

    def validate_config(self) -> bool:
        """
        Validate configuration file.

        Returns:
            True if valid, raises exception otherwise
        """
        try:
            syncs = self.load()

            for sync in syncs:
                # Check required fields
                assert sync.name, "Sync name is required"
                assert sync.query, "Source query is required"
                assert sync.primary_key, "Primary key is required"
                assert sync.table_id, "Table ID is required"
                assert sync.field_mappings, "Field mappings are required"
                assert sync.external_id_field, "External ID field is required"

                logger.info(f"✓ Config '{sync.name}' is valid")

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
