from django.db import models

# Create your models here.
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Transaction(models.Model):
    INCOME = "Income"
    EXPENSE = "Expense"
    TYPE_CHOICES = [(INCOME, "Income"), (EXPENSE, "Expense")]

    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    type = models.CharField(max_length=7, choices=TYPE_CHOICES)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )

    class Meta:
        ordering = ["-date", "-pk"]

    def __str__(self):
        return f"{self.type}: {self.description[:50]} ({self.amount})"


class Gst(models.Model):
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="gst_records"
    )
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.gst_percentage}% GST for transaction #{self.transaction_id}"


class Ledger(models.Model):
    date = models.DateField()
    transaction = models.OneToOneField(
        Transaction, on_delete=models.CASCADE, related_name="ledger_entry"
    )
    current_balance = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["date", "transaction_id"]

    def __str__(self):
        return f"Ledger entry for transaction #{self.transaction_id}"
