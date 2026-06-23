from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, NumberRange


class CompanySettingsForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired()])
    address = TextAreaField('Address', validators=[Optional()])
    phone = StringField('Phone', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email()])
    tax_rate = DecimalField('Tax Rate', validators=[DataRequired(), NumberRange(min=0, max=1)],
                            places=4, description='Enter as decimal e.g. 0.1000 for 10%')
    base_currency = StringField('Base Currency', validators=[DataRequired()])
    submit = SubmitField('Save Settings')


class CurrencyForm(FlaskForm):
    code = StringField('Currency Code', validators=[DataRequired()])
    name = StringField('Currency Name', validators=[DataRequired()])
    symbol = StringField('Symbol', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')


class UnitForm(FlaskForm):
    name = StringField('Unit Name', validators=[DataRequired()])
    abbreviation = StringField('Abbreviation', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')


class UserForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = StringField('Password', validators=[Optional()])
    submit = SubmitField('Save')


class AssignRoleForm(FlaskForm):
    submit = SubmitField('Assign Role')