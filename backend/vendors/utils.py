from .models import Vendor


def get_vendor_for_user(user):
    if not user or not user.is_authenticated or not user.email:
        return None
    return Vendor.objects.filter(
        contact_email__iexact=user.email
    ).first()
