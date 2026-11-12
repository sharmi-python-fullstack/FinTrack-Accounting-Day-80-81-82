from django import forms

from .models import Category, Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["date", "description", "amount", "type", "category"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]


class TransactionCategoryForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["category"]


class GstReportFilterForm(forms.Form):
    start_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(), required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date must be on or before end date.")
        return cleaned_data
