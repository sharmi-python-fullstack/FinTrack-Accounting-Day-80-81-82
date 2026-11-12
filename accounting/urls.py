from django.urls import path

from . import views

app_name = "accounting"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("transactions/add/", views.add_transaction, name="add_transaction"),
    path("categories/add/", views.add_category, name="add_category"),
    path("transactions/categorize/", views.categorize_transactions, name="categorize"),
    path("reports/gst/", views.generate_gst_report, name="gst_report"),
    path(
        "transactions/<int:transaction_id>/gst-bill/",
        views.generate_gst_bill,
        name="gst_bill",
    ),
    path("analytics/", views.predictive_analytics, name="analytics"),
]
