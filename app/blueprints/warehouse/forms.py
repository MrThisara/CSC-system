from flask_wtf import FlaskForm
from wtforms import DecimalField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class WriteOffForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = DecimalField('Quantity', validators=[DataRequired(),
                            NumberRange(min=0)], places=4)
    reason = TextAreaField('Reason', validators=[Optional()])
    submit = SubmitField('Write Off Stock')


class TransferReviewForm(FlaskForm):
    rejection_reason = TextAreaField('Rejection Reason', validators=[Optional()])
    submit = SubmitField('Submit')