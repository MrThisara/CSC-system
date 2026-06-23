from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DecimalField, IntegerField,
                     SelectField, SubmitField)
from wtforms.validators import DataRequired, Optional, NumberRange, Email


class BulkBuyerForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email()])
    delivery_address = TextAreaField('Delivery Address', validators=[Optional()])
    submit = SubmitField('Save')


class SaleItemForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = DecimalField('Quantity', validators=[DataRequired(),
                            NumberRange(min=0)], places=4)
    submit = SubmitField('Add Item')


class WalkInSaleForm(FlaskForm):
    submit = SubmitField('Complete Sale')


class BulkOrderForm(FlaskForm):
    bulk_buyer_id = SelectField('Bulk Buyer', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Place Bulk Order')


class TransferRequestForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = DecimalField('Quantity', validators=[DataRequired(),
                            NumberRange(min=0)], places=4)
    submit = SubmitField('Request Transfer')


class CustomerReturnForm(FlaskForm):
    sale_id = SelectField('Sale', coerce=int, validators=[DataRequired()])
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = DecimalField('Quantity', validators=[DataRequired(),
                            NumberRange(min=0)], places=4)
    reason = TextAreaField('Reason', validators=[Optional()])
    submit = SubmitField('Create Return')


class DeliveryStatusForm(FlaskForm):
    delivery_status = SelectField('Delivery Status',
                                  choices=[('Pending', 'Pending'),
                                           ('Dispatched', 'Dispatched'),
                                           ('Delivered', 'Delivered')],
                                  validators=[DataRequired()])
    estimated_days = IntegerField('Estimated Days', validators=[Optional()])
    submit = SubmitField('Update')