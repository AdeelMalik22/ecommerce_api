from django.contrib import admin

from rest.models import Product, OrderItem


# Register your models here.

@admin.register(Product)
class ModelNameAdmin(admin.ModelAdmin):
    list_display = ['id','name','category','price','created_at']


