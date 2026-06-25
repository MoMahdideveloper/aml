# Data Model: Template Replacement Feature

## Entities

This feature focuses on UI/template replacement and does not introduce new database entities. Instead, it involves several conceptual entities that guide the implementation:

### Template Mapping
- **Purpose**: Maps existing Flask template files to their Stitch KPI dashboard equivalents
- **Attributes**:
  - flask_template: String (path to existing template in templates/ directory)
  - stitch_template: String (path to equivalent Stitch design)
  - route_association: String (Flask route that uses this template)
  - variables_required: List[String] (template variables expected by Flask route)
  - variables_available: List[String] (template variables provided in Stitch design)

### Dynamic Data Context
- **Purpose**: Defines the data variables passed from Flask routes to templates
- **Attributes**:
  - template_name: String (name of the template)
  - route_function: String (Flask view function name)
  - context_variables: Dictionary[String, Any] (variables passed to template)
  - variable_types: Dictionary[String, String] (data types of each variable)
  - source: String (service or model providing the data)

### Asset Pipeline
- **Purpose**: Manages integration of Stitch design assets (CSS, JS, images) into Flask application
- **Attributes**:
  - asset_type: Enum [css, js, image, font, other]
  - source_path: String (original path in Stitch design)
  - destination_path: String (path in Flask static/ directory)
  - minify: Boolean (whether asset should be minified in production)
  - cache_duration: String (HTTP cache control directive)
  - dependencies: List[String] (other assets this asset depends on)

### Template Structure
- **Purpose**: Defines how Stitch templates are adapted for Flask template inheritance
- **Attributes**:
  - template_name: String (name of the template)
  - extends_base: String (base template this extends, if any)
  - blocks: List[String] (template blocks defined/overridden)
  - includes: List[String] (other templates included)
  - variable_usage: Dictionary[String, String] (how template variables are used)
  - form_integration: Boolean (whether template contains Flask-WTF forms)

## Relationships

- **Template Mapping** references **Dynamic Data Context** via route_association/route_function
- **Template Mapping** references **Asset Pipeline** to determine required assets for each template
- **Template Structure** references **Dynamic Data Context** for variable usage
- **Asset Pipeline** is independent but used by all templates

## Validation Rules

1. **Template Mapping Completeness**: Every Flask template in templates/ directory must have a corresponding entry in Template Mapping
2. **Variable Consistency**: Variables required by Flask routes must be available in the corresponding Stitch template
3. **Asset Integrity**: All referenced assets in Stitch designs must have valid mappings in Asset Pipeline
4. **Template Validity**: Adapted Stitch templates must be valid Jinja2 syntax
5. **Form Compatibility**: Templates containing forms must maintain field names and IDs expected by Flask-WTF

## Implementation Notes

- No new database tables or models are required for this feature
- All entities are conceptual and implemented through file structure and template adaptations
- The existing data models (Property, Customer, Deal, Agent, Task, etc.) remain unchanged
- Dynamic data flow from existing routes to templates is preserved