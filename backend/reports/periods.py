from calendar import monthrange
from datetime import date
import re

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError


def report_period(params):
    month = params.get('month')
    date_from = params.get('date_from')
    date_to = params.get('date_to')
    if date_from or date_to:
        if not date_from or not date_to:
            raise ValidationError({'date': 'Provide both date_from and date_to.'})
        try:
            start, end = parse_date(date_from), parse_date(date_to)
        except ValueError:
            start = end = None
        if not start or not end:
            raise ValidationError({'date': 'Enter valid dates in YYYY-MM-DD format.'})
        if start > end:
            raise ValidationError({'date': 'date_from must not be after date_to.'})
        label = start.strftime('%b %d, %Y') if start == end else (
            f'{start.strftime("%b %d, %Y")} - {end.strftime("%b %d, %Y")}'
        )
        return start, end, label
    if month:
        try:
            if not re.fullmatch(r'\d{4}-\d{2}', month):
                raise ValueError
            year, month_number = (int(part) for part in month.split('-'))
            start = date(year, month_number, 1)
            end = date(year, month_number, monthrange(year, month_number)[1])
        except (ValueError, TypeError):
            raise ValidationError({'month': 'Enter a valid month in YYYY-MM format.'})
    else:
        today = timezone.localdate()
        start = today.replace(day=1)
        end = date(start.year, start.month, monthrange(start.year, start.month)[1])
    return start, end, start.strftime('%B %Y')
