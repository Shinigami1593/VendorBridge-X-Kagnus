import re

from rest_framework import serializers

from .models import Vendor


class VendorSerializer(serializers.ModelSerializer):
    gst_number = serializers.CharField(validators=[])

    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'category', 'gst_number', 'contact_person',
            'contact_email', 'contact_phone', 'address', 'status',
            'rating', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
        extra_kwargs = {
            'name': {'required': True},
            'category': {'required': True},
            'contact_phone': {'required': True},
        }

    def validate_gst_number(self, value):
        if not re.fullmatch(r'[A-Za-z0-9]{15}', value):
            raise serializers.ValidationError(
                'GST number must be exactly 15 letters or digits.'
            )
        value = value.upper()
        matches = Vendor.objects.filter(gst_number__iexact=value)
        if self.instance:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise serializers.ValidationError(
                'A vendor with this GST number already exists.'
            )
        return value

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            fields['rating'].read_only = True
        elif request.user.role not in ('admin', 'officer'):
            fields['rating'].read_only = True
        return fields
