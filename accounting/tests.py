from django.test import TestCase

# Create your tests here.
from io import BytesIO
from urllib.error import HTTPError
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import CategoryForm, TransactionForm
from .models import Category, Gst, Ledger, Transaction


class AccountingViewsTests(TestCase):
    fixtures = ["sample_transactions.json"]

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Office")

    def create_transaction(self, *, amount="100.00", entry_date=None, entry_type="Income"):
        entry = Transaction.objects.create(
            date=entry_date or date.today(),
            description="Test transaction",
            amount=Decimal(amount),
            type=entry_type,
            category=self.category,
        )
        Gst.objects.create(
            transaction=entry,
            gst_percentage=Decimal("18.00"),
            gst_amount=(Decimal(amount) * Decimal("0.18")).quantize(Decimal("0.01")),
        )
        return entry

    def test_dashboard_renders_and_links_transactions(self):
        entry = self.create_transaction()
        response = self.client.get(reverse("accounting:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, entry.description)
        self.assertContains(response, "100.00")

    def test_add_transaction_creates_gst_and_running_ledger(self):
        response = self.client.post(
            reverse("accounting:add_transaction"),
            {
                "date": "2026-01-02",
                "description": "Consulting work",
                "amount": "100.00",
                "type": "Income",
                "category": self.category.pk,
            },
        )
        self.assertRedirects(response, reverse("accounting:dashboard"))
        entry = Transaction.objects.get(description="Consulting work")
        self.assertEqual(entry.gst_records.get().gst_amount, Decimal("18.00"))
        fixture_balance = sum(
            (
                item.amount if item.type == Transaction.INCOME else -item.amount
                for item in Transaction.objects.filter(date__lt=entry.date)
            ),
            Decimal("0.00"),
        )
        self.assertEqual(
            entry.ledger_entry.current_balance, fixture_balance + Decimal("100.00")
        )

    def test_backdated_transaction_recalculates_later_balances(self):
        later = self.create_transaction(entry_date=date(2026, 1, 10))
        response = self.client.post(
            reverse("accounting:add_transaction"),
            {
                "date": "2026-01-01",
                "description": "Earlier expense",
                "amount": "40.00",
                "type": "Expense",
                "category": self.category.pk,
            },
        )
        self.assertRedirects(response, reverse("accounting:dashboard"))
        fixture_balance = sum(
            (
                item.amount if item.type == Transaction.INCOME else -item.amount
                for item in Transaction.objects.filter(date__lt=date(2026, 1, 1))
            ),
            Decimal("0.00"),
        )
        self.assertEqual(
            later.ledger_entry.current_balance, fixture_balance + Decimal("60.00")
        )

    def test_invalid_transaction_is_not_saved(self):
        response = self.client.post(
            reverse("accounting:add_transaction"),
            {
                "date": "2026-01-02",
                "description": "",
                "amount": "-1",
                "type": "other",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(description="").exists())

    def test_add_and_assign_category(self):
        response = self.client.post(
            reverse("accounting:add_category"), {"name": "Travel"}
        )
        self.assertRedirects(response, reverse("accounting:dashboard"))
        entry = self.create_transaction()
        travel = Category.objects.get(name="Travel")
        response = self.client.post(
            reverse("accounting:categorize"),
            {"transaction_id": entry.pk, "category": travel.pk},
        )
        self.assertRedirects(response, reverse("accounting:categorize"))
        entry.refresh_from_db()
        self.assertEqual(entry.category, travel)

    def test_gst_report_page_and_pdf_download(self):
        entry_date = date.today()
        self.create_transaction(entry_date=entry_date)
        self.create_transaction(entry_date=entry_date - timedelta(days=30))
        response = self.client.get(reverse("accounting:gst_report"))
        self.assertContains(response, "GST report")

        response = self.client.get(
            reverse("accounting:gst_report"),
            {"start_date": entry_date.isoformat(), "category": self.category.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF"))

    def test_gst_report_rejects_invalid_date_range(self):
        response = self.client.get(
            reverse("accounting:gst_report"),
            {"start_date": "2026-02-02", "end_date": "2026-01-01"},
        )
        self.assertEqual(response.status_code, 400)

    def test_gst_bill_download(self):
        entry = self.create_transaction()
        response = self.client.get(
            reverse("accounting:gst_bill", args=[entry.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF"))

    def test_analytics_shows_configuration_error_without_key(self):
        with override_settings(GEMINI_API_KEY=""):
            response = self.client.get(reverse("accounting:analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GEMINI_API_KEY")

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("accounting.views._request_financial_predictions")
    def test_analytics_renders_predictions(self, mock_predictions):
        mock_predictions.return_value = {
            "predictions": [{"month": "2026-12", "income": 120.0, "expense": 80.0}],
            "insights": ["Spending is stable."],
            "recommendations": ["Save more."],
        }
        response = self.client.get(reverse("accounting:analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spending is stable.")
        self.assertContains(response, "2026-12")

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("accounting.views._request_financial_predictions")
    def test_analytics_shows_actionable_gemini_error(self, mock_predictions):
        mock_predictions.side_effect = HTTPError(
            "https://example.test",
            404,
            "Not Found",
            None,
            BytesIO(
                b'{"error":{"message":"This model is no longer available. Try another model."}}'
            ),
        )
        response = self.client.get(reverse("accounting:analytics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This model is no longer available.")


class AccountingFormsTests(TestCase):
    def test_transaction_form_validates_amount_and_type(self):
        valid = TransactionForm(
            data={
                "date": "2026-01-02",
                "description": "Sale",
                "amount": "10.50",
                "type": "Income",
            }
        )
        invalid = TransactionForm(
            data={
                "date": "2026-01-02",
                "description": "Sale",
                "amount": "0",
                "type": "Unknown",
            }
        )
        self.assertTrue(valid.is_valid(), valid.errors)
        self.assertFalse(invalid.is_valid())

    def test_category_form_rejects_duplicate_name(self):
        Category.objects.create(name="Office")
        form = CategoryForm(data={"name": "Office"})
        self.assertFalse(form.is_valid())


class LedgerModelTests(TestCase):
    def test_ledger_is_one_to_one_with_transaction(self):
        entry = Transaction.objects.create(
            date=date.today(), description="Entry", amount="5.00", type="Income"
        )
        Ledger.objects.create(
            date=entry.date, transaction=entry, current_balance="5.00"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Ledger.objects.create(
                date=entry.date, transaction=entry, current_balance="10.00"
            )
