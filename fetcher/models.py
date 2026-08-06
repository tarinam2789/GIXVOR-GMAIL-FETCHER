from django.db import models


class SearchQuery(models.Model):
    """
    One "fetch this sender's mail" run.

    We deliberately never store the Gmail App Password here (or anywhere
    else in the database) -- it only ever lives in the server-side
    session for the duration of the browser session. This table just
    remembers *what* was searched for, so a user can revisit results.
    """

    session_key = models.CharField(max_length=40, db_index=True)
    gmail_address = models.EmailField(help_text="The mailbox that was searched.")
    sender_email = models.CharField(
        max_length=255, help_text="The 'From' address (or name) that was searched for."
    )
    mailbox = models.CharField(max_length=120, default="INBOX")
    result_count = models.PositiveIntegerField(default=0)
    succeeded = models.BooleanField(default=True)
    error_message = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Search queries"

    def __str__(self):
        return f"{self.sender_email} -> {self.gmail_address} ({self.created_at:%Y-%m-%d %H:%M})"


class CachedEmail(models.Model):
    """A single fetched message, cached so results can be re-browsed without hitting Gmail again."""

    query = models.ForeignKey(SearchQuery, related_name="emails", on_delete=models.CASCADE)
    message_id = models.CharField(max_length=998, blank=True, default="")
    subject = models.CharField(max_length=998, blank=True, default="(no subject)")
    from_address = models.CharField(max_length=998, blank=True, default="")
    to_address = models.CharField(max_length=998, blank=True, default="")
    date_header = models.CharField(max_length=255, blank=True, default="")
    received_at = models.DateTimeField(null=True, blank=True)
    snippet = models.CharField(max_length=280, blank=True, default="")
    body_text = models.TextField(blank=True, default="")
    body_html = models.TextField(blank=True, default="")
    has_attachments = models.BooleanField(default=False)
    attachment_names = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-received_at", "-id"]

    def __str__(self):
        return self.subject or "(no subject)"

    @property
    def attachment_list(self):
        return [name for name in self.attachment_names.split("|") if name]
