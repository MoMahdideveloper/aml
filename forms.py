from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SelectField
from wtforms.validators import DataRequired, Email, Optional, NumberRange, Length


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
    description = TextAreaField("Description", validators=[DataRequired()])
    agent_id = IntegerField("Agent", validators=[DataRequired(), NumberRange(min=1)])
    priority = StringField("Priority", validators=[Optional(), Length(max=20)])
    due_date = StringField("Due Date", validators=[Optional(), Length(max=20)])  # YYYY-MM-DD
