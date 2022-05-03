from django.contrib import admin
from .models import User
from .models import Warehouse
from .models import Truck
from .models import Package

# Register your models here.
admin.site.register(Warehouse)
admin.site.register(Truck)
admin.site.register(Package)