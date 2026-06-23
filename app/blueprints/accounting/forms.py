from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DecimalField,
                     SelectField, SubmitField, DateField, BooleanField)
from wtforms.validators import DataRequired, Optional, NumberRange


class LedgerEntryForm(FlaskForm):
    entry_type = SelectField('Entry Type', choices=[
        ('payable', 'Payable'),
        ('receivable', 'Receivable'),
        ('tax_collected', 'Tax Collected'),
        ('tax_paid', 'Tax Paid'),
        ('payment', 'Payment'),
        ('adjustment', 'Adjustment'),
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(),
                          NumberRange(min=0)], places=2)
    currency_id = SelectField('Currency', coerce=int, validators=[DataRequired()])
    exchange_rate = DecimalField('Exchange Rate', validators=[Optional()],
                                 places=6, default=1)
    is_manual = BooleanField('Manual Entry')
    submit = SubmitField('Save Entry')


class AccountsPayableForm(FlaskForm):
    supplier_id = SelectField('Supplier', coerce=int, validators=[DataRequired()])
    po_id = SelectField('Purchase Order', coerce=int, validators=[Optional()])
    amount_due = DecimalField('Amount Due', validators=[DataRequired(),
                              NumberRange(min=0)], places=2)
    currency_id = SelectField('Currency', coerce=int, validators=[DataRequired()])
    exchange_rate = DecimalField('Exchange Rate', validators=[Optional()],
                                 places=6, default=1)
    due_date = DateField('Due Date', validators=[Optional()])
    submit = SubmitField('Save')


class AccountsReceivableForm(FlaskForm):
    bulk_buyer_id = SelectField('Bulk Buyer', coerce=int, validators=[DataRequired()])
    sale_id = SelectField('Sale', coerce=int, validators=[Optional()])
    amount_due = DecimalField('Amount Due', validators=[DataRequired(),
                              NumberRange(min=0)], places=2)
    due_date = DateField('Due Date', validators=[Optional()])
    submit = SubmitField('Save')


class PaymentForm(FlaskForm):
    payment_type = SelectField('Payment Type', choices=[
        ('outgoing', 'Outgoing — To Supplier'),
        ('incoming', 'Incoming — From Bulk Buyer'),
    ], validators=[DataRequired()])
    payable_id = SelectField('Accounts Payable', coerce=int, validators=[Optional()])
    receivable_id = SelectField('Accounts Receivable', coerce=int,
                                validators=[Optional()])
    amount = DecimalField('Amount', validators=[DataRequired(),
                          NumberRange(min=0)], places=2)
    currency_id = SelectField('Currency', coerce=int, validators=[DataRequired()])
    exchange_rate = DecimalField('Exchange Rate', validators=[Optional()],
                                 places=6, default=1)
    payment_date = DateField('Payment Date', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Record Payment')


class TaxEntryForm(FlaskForm):
    tax_type = SelectField('Tax Type', choices=[
        ('collected', 'Collected — From Customers'),
        ('paid', 'Paid — On Imports'),
    ], validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(),
                          NumberRange(min=0)], places=2)
    tax_rate = DecimalField('Tax Rate', validators=[DataRequired()],
                            places=4, default=0.10)
    reference_type = StringField('Reference Type', validators=[Optional()])
    reference_id = StringField('Reference ID', validators=[Optional()])
    submit = SubmitField('Save')