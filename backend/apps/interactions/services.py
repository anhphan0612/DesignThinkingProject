from django.utils import timezone

from .models import ChatMessage, ChatThread, ContactRequest, Favorite, SearchLog, UserEvent


def get_session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key or ""


def event_user(request):
    return request.user if request.user.is_authenticated else None


def log_event(*, request, type, room=None, metadata=None):
    return UserEvent.objects.create(
        user=event_user(request),
        session_key=get_session_key(request),
        type=type,
        room=room,
        metadata=metadata or {},
    )


def add_favorite(*, user, room, request=None):
    favorite, created = Favorite.objects.get_or_create(user=user, room=room)
    if request and created:
        log_event(request=request, type=UserEvent.Type.FAVORITE_ADD, room=room)
    return favorite, created


def remove_favorite(*, user, room, request=None):
    deleted, _ = Favorite.objects.filter(user=user, room=room).delete()
    if request and deleted:
        log_event(request=request, type=UserEvent.Type.FAVORITE_REMOVE, room=room)
    return deleted > 0


def log_search(*, request, query_text="", filters=None, result_ids=None):
    result_ids = result_ids or []
    log_event(request=request, type=UserEvent.Type.SEARCH, metadata={"filters": filters or {}})
    return SearchLog.objects.create(
        user=event_user(request),
        session_key=get_session_key(request),
        query_text=query_text,
        filters=filters or {},
        result_ids=result_ids,
        result_count=len(result_ids),
    )


def start_contact_thread(*, requester, recipient, message="", room=None, roommate_post=None):
    contact_request = ContactRequest.objects.create(
        requester=requester,
        recipient=recipient,
        room=room,
        roommate_post=roommate_post,
        message=message,
    )
    thread, _ = ChatThread.objects.get_or_create(
        requester=requester,
        recipient=recipient,
        room=room,
        roommate_post=roommate_post,
        defaults={"contact_request": contact_request},
    )
    if not thread.contact_request_id:
        thread.contact_request = contact_request
    thread.updated_at = timezone.now()
    thread.save(update_fields=("contact_request", "updated_at"))
    if message.strip():
        ChatMessage.objects.create(thread=thread, sender=requester, body=message.strip())
    return contact_request, thread

