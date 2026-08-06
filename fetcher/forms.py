from django import forms


class ConnectForm(forms.Form):
    """The one form that both authenticates to Gmail and defines the search."""

    gmail_address = forms.EmailField(
        label="Gmail address",
        widget=forms.EmailInput(
            attrs={"placeholder": "you@gmail.com", "autocomplete": "username"}
        ),
    )
    app_password = forms.CharField(
        label="App Password",
        widget=forms.PasswordInput(
            attrs={"placeholder": "16-character App Password", "autocomplete": "current-password"},
            render_value=False,
        ),
        help_text=(
            "Not your normal Gmail password. Generate one at "
            "myaccount.google.com/apppasswords (requires 2-Step Verification)."
        ),
    )
    sender_email = forms.CharField(
        label="Fetch mail from",
        widget=forms.TextInput(attrs={"placeholder": "someone@example.com"}),
        help_text="The address (or name) that appears in the 'From' field.",
    )
    mailbox = forms.CharField(
        label="Mailbox / label",
        initial="INBOX",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "INBOX"}),
    )
    limit = forms.IntegerField(
        label="Max results",
        initial=25,
        min_value=1,
        max_value=200,
        widget=forms.NumberInput(attrs={"placeholder": "25"}),
    )

    def clean_mailbox(self):
        return self.cleaned_data.get("mailbox") or "INBOX"

    def clean_sender_email(self):
        return self.cleaned_data["sender_email"].strip()
