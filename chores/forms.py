# chores/forms.py

from django import forms
from .models import Chore, Category


class ChoreForm(forms.ModelForm):
    """Form for creating and editing chores."""

    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=True,
        label="Category",
    )
    interval_override_days = forms.IntegerField(
        required=False,
        label="Interval Override (days)",
        min_value=1,
        help_text="Leave blank to use household default",
    )
    is_one_time = forms.BooleanField(
        required=False,
        label="One-time chore",
    )

    class Meta:
        model = Chore
        fields = ['name', 'category', 'difficulty', 'interval_override_days', 'is_one_time']

    def __init__(self, *args, categories=None, household=None, **kwargs):
        super().__init__(*args, **kwargs)
        if categories is not None:
            self.fields['category'].queryset = categories
        if self.instance and self.instance.pk:
            self.fields['name'].initial = self.instance.name
            self.fields['difficulty'].initial = self.instance.difficulty
            if self.instance.category:
                self.fields['category'].initial = self.instance.category.id
            if self.instance.interval_override_days is not None:
                self.fields['interval_override_days'].initial = self.instance.interval_override_days
            self.fields['is_one_time'].initial = self.instance.is_one_time
        else:
            self.fields['difficulty'].initial = 'medium'
            self.fields['is_one_time'].initial = False
