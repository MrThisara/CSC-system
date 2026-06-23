from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DecimalField, IntegerField,
                     SelectField, BooleanField, SubmitField, DateField)
from wtforms.validators import DataRequired, Optional, NumberRange, Email


class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[DataRequired()])
    contact_name = StringField('Contact Name', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone', validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    country = StringField('Country', validators=[Optional()])
    lead_time_days = IntegerField('Lead Time (days)', validators=[Optional()])
    currency_id = SelectField('Currency', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save')


class ProductForm(FlaskForm):
    sku = StringField('SKU', validators=[DataRequired()])
    name = StringField('Product Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    unit_id = SelectField('Unit', coerce=int, validators=[DataRequired()])
    selling_price = DecimalField('Selling Price (JPY)', validators=[DataRequired(),
                                 NumberRange(min=0)], places=2)
    warehouse_reorder_threshold = DecimalField('Warehouse Reorder Threshold',
                                               validators=[Optional()], places=2, default=0)
    shelf_reorder_threshold = DecimalField('Shelf Reorder Threshold',
                                           validators=[Optional()], places=2, default=0)
    bulk_limit = DecimalField('Bulk Limit', validators=[Optional()], places=2, default=0)
    submit = SubmitField('Save')


class PurchaseOrderForm(FlaskForm):
    supplier_id = SelectField('Supplier', coerce=int, validators=[DataRequired()])
    currency_id = SelectField('Currency', coerce=int, validators=[DataRequired()])
    exchange_rate = DecimalField('Exchange Rate to JPY', validators=[DataRequired(),
                                 NumberRange(min=0)], places=6)
    expected_delivery = DateField('Expected Delivery', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save')


class POItemForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = DecimalField('Quantity', validators=[DataRequired(), NumberRange(min=0)], places=4)
    unit_price = DecimalField('Unit Price', validators=[DataRequired(), NumberRange(min=0)], places=4)
    submit = SubmitField('Add Item')


class GoodsReceivedForm(FlaskForm):
    submit = SubmitField('Confirm Goods Received')


class ShipmentForm(FlaskForm):
    tracking_number = StringField('Tracking Number', validators=[Optional()])
    carrier = StringField('Carrier', validators=[Optional()])
    shipped_date = DateField('Shipped Date', validators=[Optional()])
    estimated_arrival = DateField('Estimated Arrival', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save')


class LandedCostForm(FlaskForm):
    freight = DecimalField('Freight', validators=[Optional()], places=2, default=0)
    import_duty = DecimalField('Import Duty', validators=[Optional()], places=2, default=0)
    insurance = DecimalField('Insurance', validators=[Optional()], places=2, default=0)
    other = DecimalField('Other', validators=[Optional()], places=2, default=0)
    currency_id = SelectField('Currency', coerce=int, validators=[DataRequired()])
    exchange_rate = DecimalField('Exchange Rate to JPY', validators=[DataRequired(),
                                 NumberRange(min=0)], places=6)
    submit = SubmitField('Save Landed Cost')


class SupplierReturnForm(FlaskForm):
    supplier_id = SelectField('Supplier', coerce=int, validators=[DataRequired()])
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = DecimalField('Quantity', validators=[DataRequired(), NumberRange(min=0)], places=4)
    reason = TextAreaField('Reason', validators=[Optional()])
    submit = SubmitField('Create Return')