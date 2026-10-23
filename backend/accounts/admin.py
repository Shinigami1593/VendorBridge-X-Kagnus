from django.contrib import admin

from .models import User

admin.site.register(User)


# pip install pillow
# pip freeze > requirements.txt
# python manage.py makemigrations
# python manage.py migrate
# python manage.py createsuperuser