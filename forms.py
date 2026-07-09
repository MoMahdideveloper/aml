from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import FloatField, IntegerField, SelectField, StringField, TextAreaField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, Regexp, ValidationError


class BaseNoCSRFForm(FlaskForm):
    class Meta:
        csrf = False  # CSRF is opt-in via app config; forms validate without it


class AgentForm(BaseNoCSRFForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=255)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[DataRequired(), Length(max=50)])
    specialization = StringField("Specialization", validators=[Optional(), Length(max=255)])
    bio = TextAreaField("Bio", validators=[Optional()])


class CustomerForm(BaseNoCSRFForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=255)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[DataRequired(), Length(max=50)])
    budget_min = FloatField("Budget Min", validators=[Optional(), NumberRange(min=0)])
    budget_max = FloatField("Budget Max", validators=[Optional(), NumberRange(min=0)])
    preferred_bedrooms = IntegerField("Bedrooms", validators=[Optional(), NumberRange(min=0)])
    preferred_bathrooms = IntegerField("Bathrooms", validators=[Optional(), NumberRange(min=0)])
    preferred_type = StringField("Property Type", validators=[Optional(), Length(max=50)])
    location_preference = StringField("Location", validators=[Optional(), Length(max=255)])


class PropertyForm(BaseNoCSRFForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    address = TextAreaField("Address", validators=[DataRequired()])
    property_type = StringField("Type", validators=[DataRequired(), Length(max=50)])
    bedrooms = IntegerField("Bedrooms", validators=[Optional(), NumberRange(min=0)])
    bathrooms = IntegerField("Bathrooms", validators=[Optional(), NumberRange(min=0)])
    square_feet = IntegerField("Square Feet", validators=[Optional(), NumberRange(min=0)])
    description = TextAreaField("Description", validators=[Optional()])
    agent_id = IntegerField("Agent", validators=[Optional(), NumberRange(min=1)])
    year_built = IntegerField(
        "Year Built", validators=[Optional(), NumberRange(min=1800, max=3000)]
    )
    parking_spaces = IntegerField("Parking", validators=[Optional(), NumberRange(min=0)])
    floors = IntegerField("Floors", validators=[Optional(), NumberRange(min=1)])
    units = IntegerField("Units", validators=[Optional(), NumberRange(min=1)])
    property_condition = StringField("Condition", validators=[Optional(), Length(max=50)])
    property_features = TextAreaField("Features", validators=[Optional()])
    neighborhood = StringField("Neighborhood", validators=[Optional(), Length(max=100)])
    property_category = StringField("Category", validators=[Optional(), Length(max=50)])
    listing_type = SelectField(
        "Listing Type", choices=[("sale", "sale"), ("rental", "rental")], validators=[Optional()]
    )
    sale_price = FloatField("Sale Price", validators=[Optional(), NumberRange(min=0)])
    rahn = FloatField("Rahn", validators=[Optional(), NumberRange(min=0)])
    ejare = FloatField("Ejare", validators=[Optional(), NumberRange(min=0)])


class DealForm(BaseNoCSRFForm):
    property_id = IntegerField("Property", validators=[DataRequired(), NumberRange(min=1)])
    customer_id = IntegerField("Customer", validators=[DataRequired(), NumberRange(min=1)])
    agent_id = IntegerField("Agent", validators=[DataRequired(), NumberRange(min=1)])
    status = StringField("Status", validators=[Optional(), Length(max=50)])
    offer_amount = FloatField("Offer", validators=[Optional(), NumberRange(min=0)])


class TaskForm(BaseNoCSRFForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description", validators=[Optional()])
    # Task.agent_id is NOT NULL in the ORM
    agent_id = IntegerField("Agent", validators=[DataRequired(), NumberRange(min=1)])
    priority = StringField("Priority", validators=[Optional(), Length(max=20)])
    due_date = StringField("Due Date", validators=[Optional(), Length(max=20)])  # YYYY-MM-DD


class EnvironmentVariableForm(FlaskForm):
    """Form for creating and editing environment variables with enhanced validation"""
    key = StringField(
        "Variable Key", 
        validators=[
            DataRequired(message="Variable key is required"), 
            Length(max=255, message="Key cannot exceed 255 characters"),
            Regexp(
                r'^[A-Za-z_][A-Za-z0-9_]*$', 
                message="Key must start with letter or underscore and contain only alphanumeric characters and underscores"
            )
        ],
        render_kw={
            "placeholder": "e.g., DATABASE_URL, API_KEY, DEBUG_MODE",
            "class": "form-control",
            "pattern": "^[A-Za-z_][A-Za-z0-9_]*$",
            "title": "Must start with letter or underscore, followed by letters, numbers, or underscores"
        }
    )
    value = StringField(
        "Value", 
        validators=[
            DataRequired(message="Variable value is required"),
            Length(max=10000, message="Value cannot exceed 10,000 characters")
        ],
        render_kw={
            "placeholder": "Enter the environment variable value",
            "class": "form-control"
        }
    )
    description = TextAreaField(
        "Description", 
        validators=[Optional(), Length(max=500, message="Description cannot exceed 500 characters")],
        render_kw={
            "placeholder": "Optional description of what this variable controls",
            "class": "form-control",
            "rows": "3"
        }
    )
    is_required = BooleanField(
        "Required Variable", 
        default=False,
        render_kw={
            "class": "form-check-input"
        }
    )
    
    def validate_key(self, field):
        """Custom validation for environment variable key"""
        key = field.data.upper() if field.data else ""
        
        # Check for reserved prefixes
        reserved_prefixes = ['SYSTEM_', 'FLASK_', 'PYTHON_', 'PATH', 'HOME', 'USER']
        if any(key.startswith(prefix) for prefix in reserved_prefixes):
            raise ValidationError(f"Key cannot start with reserved prefix: {', '.join(reserved_prefixes)}")
        
        # Check for common typos or problematic names
        problematic_names = ['PASSWORD', 'PASS', 'PWD', 'SECRET', 'KEY']
        if key in problematic_names:
            raise ValidationError(f"Use more specific names like 'DATABASE_PASSWORD' instead of '{key}'")
    
    def validate_value(self, field):
        """Custom validation for environment variable value"""
        if not field.data:
            return
        
        value = field.data
        key = self.key.data.upper() if self.key.data else ""
        
        # Validate URL format for URL variables
        if key.endswith('_URL') and value:
            import re
            url_pattern = r'^https?://|^postgresql://|^sqlite://'
            if not re.match(url_pattern, value):
                raise ValidationError("URL values should start with a valid protocol (http://, https://, postgresql://, sqlite://)")
        
        # Validate port numbers
        if key.endswith('_PORT') and value:
            try:
                port = int(value)
                if not (1 <= port <= 65535):
                    raise ValidationError("Port values must be between 1 and 65535")
            except ValueError:
                raise ValidationError("Port values must be numeric")
        
        # Validate email format
        if key.endswith('_EMAIL') and value:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                raise ValidationError("Email values must be in valid email format")
        
        # Check for weak values
        weak_values = ['password', '123456', 'admin', 'secret', 'test', 'default']
        if value.lower() in weak_values:
            raise ValidationError("Value appears to be a common weak password or default value")


class PropertyEditForm(BaseNoCSRFForm):
    """Enhanced form for editing property records with validation"""
    property_id = IntegerField("Property ID", validators=[DataRequired()])
    is_ai_extracted = HiddenField("AI Extracted", default="false")
    ai_raw_data = HiddenField("AI Raw Data", default="")
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    address = TextAreaField("Address", validators=[DataRequired()])
    image = FileField("Property Image", validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    property_type = SelectField(
        "Property Type",
        choices=[("house", "House"), ("condo", "Condo"), ("loft", "Loft"), ("townhouse", "Townhouse"), ("commercial", "Commercial")],
        validators=[DataRequired()]
    )
    bedrooms = IntegerField("Bedrooms", validators=[Optional(), NumberRange(min=0, max=20)])
    bathrooms = IntegerField("Bathrooms", validators=[Optional(), NumberRange(min=0, max=20)])
    square_feet = IntegerField("Square Feet", validators=[Optional(), NumberRange(min=0)])
    description = TextAreaField("Description", validators=[Optional()])
    agent_id = IntegerField("Agent", validators=[Optional(), NumberRange(min=1)])
    year_built = IntegerField(
        "Year Built", validators=[Optional(), NumberRange(min=1800, max=3000)]
    )
    parking_spaces = IntegerField("Parking", validators=[Optional(), NumberRange(min=0, max=10)])
    floors = IntegerField("Floors", validators=[Optional(), NumberRange(min=1, max=50)])
    units = IntegerField("Units", validators=[Optional(), NumberRange(min=1, max=100)])
    property_condition = SelectField(
        "Condition",
        choices=[("excellent", "Excellent"), ("good", "Good"), ("fair", "Fair"), ("needs_renovation", "Needs Renovation")],
        validators=[Optional()]
    )
    property_features = TextAreaField("Features", validators=[Optional()])
    neighborhood = StringField("Neighborhood", validators=[Optional(), Length(max=100)])
    property_category = SelectField(
        "Category",
        choices=[("residential", "Residential"), ("commercial", "Commercial"), ("industrial", "Industrial")],
        validators=[Optional()]
    )
    heating_type = StringField("Heating Type", validators=[Optional(), Length(max=50)])
    cooling_type = StringField("Cooling Type", validators=[Optional(), Length(max=50)])
    listing_type = SelectField(
        "Listing Type", 
        choices=[("sale", "Sale"), ("rental", "Rental")], 
        validators=[DataRequired()]
    )
    sale_price = IntegerField("Sale Price", validators=[Optional(), NumberRange(min=0)])
    rahn = IntegerField("Rahn (Deposit)", validators=[Optional(), NumberRange(min=0)])
    ejare = IntegerField("Ejare (Monthly Rent)", validators=[Optional(), NumberRange(min=0)])
    latitude = FloatField("Latitude", validators=[Optional()])
    longitude = FloatField("Longitude", validators=[Optional()])
    document_type = StringField("Document Type", validators=[Optional(), Length(max=50)])
    floor_number = IntegerField("Floor Number", validators=[Optional()])
    built_area = IntegerField("Built Area", validators=[Optional(), NumberRange(min=0)])
    land_area = IntegerField("Land Area", validators=[Optional(), NumberRange(min=0)])
    floor_covering = StringField("Floor Covering", validators=[Optional(), Length(max=50)])
    facade_type = StringField("Facade Type", validators=[Optional(), Length(max=50)])
    wall_covering = StringField("Wall Covering", validators=[Optional(), Length(max=50)])
    cabinet_type = StringField("Cabinet Type", validators=[Optional(), Length(max=50)])
    property_direction = StringField("Direction", validators=[Optional(), Length(max=30)])
    is_exchangeable = BooleanField("Exchangeable", default=False)
    boundary_width = FloatField("Boundary Width", validators=[Optional(), NumberRange(min=0)])
    density = StringField("Density", validators=[Optional(), Length(max=100)])
    commercial_status = StringField("Commercial Status", validators=[Optional(), Length(max=50)])
    usage_type = StringField("Usage Type", validators=[Optional(), Length(max=50)])
    ceiling_count = IntegerField("Ceiling Count", validators=[Optional(), NumberRange(min=0)])
    permit_ceiling = StringField("Permit Ceiling", validators=[Optional(), Length(max=50)])
    property_length = FloatField("Property Length", validators=[Optional(), NumberRange(min=0)])
    property_height = FloatField("Property Height", validators=[Optional(), NumberRange(min=0)])
    price_per_meter = IntegerField("Price Per Meter", validators=[Optional(), NumberRange(min=0)])
    custom_fields = TextAreaField("Custom Fields (JSON/Text)", validators=[Optional()])
    
    def validate(self, extra_validators=None):
        """Override validate method to include custom property validation"""
        from datetime import datetime
        # First run the standard validation
        if not super().validate(extra_validators):
            return False
        
        # Validate pricing based on listing type
        if self.listing_type.data == 'sale':
            if not self.sale_price.data or self.sale_price.data <= 0:
                self.sale_price.errors.append("Sale price is required for sale listings.")
                return False
        elif self.listing_type.data == 'rental':
            if not self.rahn.data and not self.ejare.data:
                self.rahn.errors.append("Either Rahn or Ejare (or both) must be specified for rental listings.")
                self.ejare.errors.append("Either Rahn or Ejare (or both) must be specified for rental listings.")
                return False
        
        # Validate year built is not in the future
        if self.year_built.data and self.year_built.data > datetime.now().year:
            self.year_built.errors.append("Year built cannot be in the future.")
            return False
        
        return True

