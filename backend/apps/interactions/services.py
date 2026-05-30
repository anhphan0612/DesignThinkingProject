from .models import Favorite, SearchLog, UserEvent


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

