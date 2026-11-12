from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Category, Gst, Ledger, Transaction

admin.site.register(Transaction)
admin.site.register(Gst)
admin.site.register(Ledger)
admin.site.register(Category)
