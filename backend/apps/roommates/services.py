from datetime import timedelta

from apps.recommendations.text import normalize_text


def ranges_overlap(left_min, left_max, right_min, right_max):
    if left_min is None or left_max is None or right_min is None or right_max is None:
        return False
    return left_min <= right_max and right_min <= left_max


def _text_similarity(profile, post):
    profile_terms = []
    if profile.university:
        profile_terms.extend([profile.university.name, profile.university.short_name])
    profile_terms.extend(profile.preferred_districts.values_list("name", flat=True))
    profile_terms.extend(profile.lifestyle_tags.values_list("name", flat=True))
    if not profile_terms:
        return 0
    text = normalize_text(" ".join([post.title, post.description, post.address or ""]))
    matched = [term for term in profile_terms if normalize_text(term) and normalize_text(term) in text]
    return min(10, len(matched) * 3)


def score_roommate_post(profile, post):
    score = 0
    reasons = []
    detail = {}

    if profile.university_id and post.university_id == profile.university_id:
        score += 22
        detail["university"] = 1
        reasons.append("Cùng trường")
    else:
        detail["university"] = 0

    if ranges_overlap(profile.budget_min, profile.budget_max, post.budget_min, post.budget_max):
        score += 24
        detail["budget"] = 1
        reasons.append("Ngân sách khớp")
    else:
        detail["budget"] = 0

    preferred_district_ids = set(profile.preferred_districts.values_list("id", flat=True))
    post_district_ids = set(post.preferred_districts.values_list("id", flat=True))
    if post.ward_id:
        post_district_ids.add(post.ward.district_id)
    if preferred_district_ids and preferred_district_ids.intersection(post_district_ids):
        score += 18
        detail["district"] = 1
        reasons.append("Khu vực phù hợp")
    else:
        detail["district"] = 0

    profile_tag_ids = set(profile.lifestyle_tags.values_list("id", flat=True))
    post_tag_ids = set(post.lifestyle_tags.values_list("id", flat=True))
    overlap = profile_tag_ids.intersection(post_tag_ids)
    if overlap:
        tag_score = min(18, len(overlap) * 6)
        score += tag_score
        detail["lifestyle"] = round(tag_score / 18, 2)
        reasons.append("Thói quen sống tương đồng")
    else:
        detail["lifestyle"] = 0

    if profile.move_in_date and post.move_in_date:
        days = abs(profile.move_in_date - post.move_in_date)
        if days <= timedelta(days=14):
            score += 10
            detail["move_in_date"] = 1
            reasons.append("Ngày chuyển vào gần nhau")
        else:
            detail["move_in_date"] = 0

    text_points = _text_similarity(profile, post)
    if text_points:
        score += text_points
        detail["text"] = round(text_points / 10, 2)
        reasons.append("Nội dung bài đăng gần với hồ sơ")
    else:
        detail["text"] = 0

    if not reasons:
        reasons.append("Có thể cân nhắc trao đổi thêm")

    return {
        "score": min(score, 100),
        "reasons": reasons[:4],
        "score_detail": detail,
    }
