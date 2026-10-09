from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FloatField, MultipleFileField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Email, Regexp
from app.models import Complaint

class ComplaintForm(FlaskForm):
    complainant_name = StringField('Your Name (Optional)', validators=[Optional(), Length(max=100)])
    complainant_phone = StringField('Mobile Number (Optional)', validators=[
        Optional(),
        Length(min=7, max=20),
        Regexp(r'^[+0-9\s\-()]+$', message="Please enter a valid phone number.")
    ])
    complainant_email = StringField('Email Address (Optional)', validators=[Optional(), Email(), Length(max=120)])
    
    category = SelectField('Waste / Dirt Category', choices=[(c, c) for c in Complaint.CATEGORIES], validators=[DataRequired()])
    description = TextAreaField('Detailed Description of the Issue', validators=[
        DataRequired(message="Please provide details about the waste or dirtiness."),
        Length(min=10, max=2000, message="Description must be between 10 and 2000 characters.")
    ])
    
    address = StringField('Street Address / Specific Location', validators=[
        DataRequired(message="Street address or specific spot is required."),
        Length(max=255)
    ])
    locality = StringField('Locality / Neighborhood / Ward', validators=[
        DataRequired(message="Locality or ward name is required."),
        Length(max=100)
    ])
    landmark = StringField('Nearest Landmark', validators=[Optional(), Length(max=150)])
    
    latitude = FloatField('Latitude (Optional)', validators=[Optional()])
    longitude = FloatField('Longitude (Optional)', validators=[Optional()])
    
    images = MultipleFileField('Photographs of the Dirty Area', validators=[Optional()])
    submit = SubmitField('Submit Cleanliness Report')


class TrackForm(FlaskForm):
    tracking_id = StringField('Complaint Tracking ID', validators=[
        DataRequired(message="Please enter your tracking ID."),
        Length(min=6, max=40)
    ])
    submit = SubmitField('Track Status')
