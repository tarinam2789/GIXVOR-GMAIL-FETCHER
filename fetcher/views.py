from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ConnectForm
from .gmail_client import (
    GmailAuthError,
    GmailConnectionError,
    GmailSearchError,
    fetch_from_sender,
)
from .models import CachedEmail, SearchQuery

SESSION_ADDRESS_KEY = "gmail_address"
SESSION_PASSWORD_KEY = "gmail_app_password"
SESSION_SERVER_KEY = "gmail_imap_server"


def _ensure_session(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def landing(request):
    """The pretty marketing/portfolio landing page."""
    stats = {
        "queries": SearchQuery.objects.count(),
        "emails": CachedEmail.objects.count(),
    }
    return render(request, "fetcher/landing.html", {"stats": stats})


def connect(request):
    """Collect Gmail credentials + search target, run the fetch, cache the results."""
    if request.method == "POST":
        form = ConnectForm(request.POST)
        if form.is_valid():
            session_key = _ensure_session(request)
            gmail_address = form.cleaned_data["gmail_address"]
            app_password = form.cleaned_data["app_password"]
            sender_email = form.cleaned_data["sender_email"]
            mailbox = form.cleaned_data["mailbox"]
            limit = form.cleaned_data["limit"]

            query = SearchQuery.objects.create(
                session_key=session_key,
                gmail_address=gmail_address,
                sender_email=sender_email,
                mailbox=mailbox,
            )

            try:
                fetched = fetch_from_sender(
                    gmail_address=gmail_address,
                    app_password=app_password,
                    sender_email=sender_email,
                    mailbox=mailbox,
                    limit=limit,
                )
            except GmailAuthError as exc:
                query.succeeded = False
                query.error_message = str(exc)
                query.save(update_fields=["succeeded", "error_message"])
                messages.error(request, str(exc))
                return render(request, "fetcher/connect.html", {"form": form})
            except (GmailConnectionError, GmailSearchError) as exc:
                query.succeeded = False
                query.error_message = str(exc)
                query.save(update_fields=["succeeded", "error_message"])
                messages.error(request, str(exc))
                return render(request, "fetcher/connect.html", {"form": form})

            CachedEmail.objects.bulk_create(
                [
                    CachedEmail(
                        query=query,
                        message_id=e.message_id,
                        subject=e.subject,
                        from_address=e.from_address,
                        to_address=e.to_address,
                        date_header=e.date_header,
                        received_at=e.received_at,
                        snippet=e.snippet,
                        body_text=e.body_text,
                        body_html=e.body_html,
                        has_attachments=bool(e.attachment_names),
                        attachment_names="|".join(e.attachment_names),
                    )
                    for e in fetched
                ]
            )
            query.result_count = len(fetched)
            query.save(update_fields=["result_count"])

            # Keep credentials only in the session, only for a "refresh" convenience.
            request.session[SESSION_ADDRESS_KEY] = gmail_address
            request.session[SESSION_PASSWORD_KEY] = app_password

            if fetched:
                messages.success(
                    request, f"Pulled {len(fetched)} message(s) from {sender_email}."
                )
            else:
                messages.info(
                    request, f"Connected fine, but no messages from {sender_email} were found."
                )
            return redirect("fetcher:results", pk=query.pk)
    else:
        form = ConnectForm(initial={"mailbox": "INBOX", "limit": 25})

    return render(request, "fetcher/connect.html", {"form": form})


def results(request, pk):
    query = get_object_or_404(SearchQuery, pk=pk)
    emails = query.emails.all()
    can_refresh = (
        request.session.get(SESSION_ADDRESS_KEY) == query.gmail_address
        and SESSION_PASSWORD_KEY in request.session
    )
    return render(
        request,
        "fetcher/results.html",
        {"query": query, "emails": emails, "can_refresh": can_refresh},
    )


def email_detail(request, pk, email_pk):
    query = get_object_or_404(SearchQuery, pk=pk)
    msg = get_object_or_404(CachedEmail, pk=email_pk, query=query)
    return render(request, "fetcher/email_detail.html", {"query": query, "msg": msg})


def refresh(request, pk):
    query = get_object_or_404(SearchQuery, pk=pk)
    gmail_address = request.session.get(SESSION_ADDRESS_KEY)
    app_password = request.session.get(SESSION_PASSWORD_KEY)

    if gmail_address != query.gmail_address or not app_password:
        messages.warning(request, "Reconnect with your App Password to refresh this search.")
        return redirect("fetcher:connect")

    try:
        fetched = fetch_from_sender(
            gmail_address=gmail_address,
            app_password=app_password,
            sender_email=query.sender_email,
            mailbox=query.mailbox,
            limit=max(query.result_count, 25),
        )
    except (GmailAuthError, GmailConnectionError, GmailSearchError) as exc:
        messages.error(request, str(exc))
        return redirect("fetcher:results", pk=query.pk)

    query.emails.all().delete()
    CachedEmail.objects.bulk_create(
        [
            CachedEmail(
                query=query,
                message_id=e.message_id,
                subject=e.subject,
                from_address=e.from_address,
                to_address=e.to_address,
                date_header=e.date_header,
                received_at=e.received_at,
                snippet=e.snippet,
                body_text=e.body_text,
                body_html=e.body_html,
                has_attachments=bool(e.attachment_names),
                attachment_names="|".join(e.attachment_names),
            )
            for e in fetched
        ]
    )
    query.result_count = len(fetched)
    query.succeeded = True
    query.error_message = ""
    query.save(update_fields=["result_count", "succeeded", "error_message"])
    messages.success(request, f"Refreshed — {len(fetched)} message(s) now cached.")
    return redirect("fetcher:results", pk=query.pk)


def history(request):
    session_key = _ensure_session(request)
    queries = SearchQuery.objects.filter(session_key=session_key)
    return render(request, "fetcher/history.html", {"queries": queries})


def disconnect(request):
    request.session.pop(SESSION_ADDRESS_KEY, None)
    request.session.pop(SESSION_PASSWORD_KEY, None)
    messages.info(request, "Disconnected. Your App Password has been cleared from this session.")
    return redirect("fetcher:landing")
