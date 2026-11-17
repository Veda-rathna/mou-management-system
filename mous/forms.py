from django import forms
from mous.models import MOU, PartnerSubmission, ShareLink


class BaseStyledForm(forms.ModelForm):
    """Adds Bootstrap 5 form classes and styling consistently."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.setdefault('class', 'form-control')
            else:
                field.widget.attrs.setdefault('class', 'form-control')


class MOUForm(BaseStyledForm):
    """Internal college form to create or update an MOU."""
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    expiry_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = MOU
        fields = [
            'title',
            'partner_name',
            'partner_organization',
            'partner_email',
            'partner_phone',
            'department',
            'description',
            'start_date',
            'expiry_date',
            'document',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Scope, key milestones, objectives...'}),
        }


class PartnerInviteForm(forms.ModelForm):
    """Quick form to initiate an MOU invitation for an external partner."""
    class Meta:
        model = MOU
        fields = [
            'title',
            'partner_name',
            'partner_organization',
            'partner_email',
            'department',
            'description',
            'document',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Industry Collaboration & Training MOU'}),
            'partner_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Signatory / Point of Contact'}),
            'partner_organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Acme Technologies Inc.'}),
            'partner_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@acme.org'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dept of Computer Science & Engineering'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief description of proposed cooperation...'}),
            'document': forms.FileInput(attrs={'class': 'form-control'}),
        }


class PartnerPortalSubmissionForm(forms.ModelForm):
    """Public submission form for external partner via UUID share link."""
    signature_data = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'id_signature_data'}),
        required=False
    )

    class Meta:
        model = PartnerSubmission
        fields = [
            'partner_name',
            'partner_organization',
            'partner_email',
            'partner_phone',
            'partner_designation',
            'updated_document',
            'notes',
        ]
        widgets = {
            'partner_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Legal Name'}),
            'partner_organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company / Organization'}),
            'partner_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'official@company.com'}),
            'partner_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 555 123 4567'}),
            'partner_designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Managing Director / VP Partnerships'}),
            'updated_document': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Review comments, proofreading notes, or clarification on terms...'}),
        }


class CollegeSignForm(forms.Form):
    """Internal college approval and digital countersign form."""
    signatory_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dr. Jane Smith'})
    )
    signatory_title = forms.CharField(
        max_length=255,
        initial='Principal & Dean of Institutional Partnerships',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    signature_data = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'id_college_signature_data'}),
        required=True
    )
