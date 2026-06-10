from datetime import timedelta


def ranges_overlap(left_min, left_max, right_min, right_max):
    if left_min is None or left_max is None or right_min is None or right_max is None:
        return False
    return left_min <= right_max and right_min <= left_max


def score_roommate_post(profile, post):
    score = 0
    reasons = []

    if profile.university_id and post.university_id == profile.university_id:
        score += 25
        reasons.append("Cùng trường")

    if ranges_overlap(profile.budget_min, profile.budget_max, post.budget_min, post.budget_max):
        score += 25
        reasons.append("Ngân sách khớp")

    preferred_district_ids = set(profile.preferred_districts.values_list("id", flat=True))
    post_district_ids = set(post.preferred_districts.values_list("id", flat=True))
    if post.ward_id:
        post_district_ids.add(post.ward.district_id)
    if preferred_district_ids and preferred_district_ids.intersection(post_district_ids):
        score += 20
        reasons.append("Khu vực phù hợp")

    profile_tag_ids = set(profile.lifestyle_tags.values_list("id", flat=True))
    post_tag_ids = set(post.lifestyle_tags.values_list("id", flat=True))
    overlap = profile_tag_ids.intersection(post_tag_ids)
    if overlap:
        score += min(20, len(overlap) * 7)
        reasons.append("Thói quen sống tương đồng")

    if profile.move_in_date and post.move_in_date:
        if abs(profile.move_in_date - post.move_in_date) <= timedelta(days=14):
            score += 10
            reasons.append("Ngày chuyển vào gần nhau")

    if not reasons:
        reasons.append("Có thể cân nhắc trao đổi thêm")

    return {
        "score": min(score, 100),
        "reasons": reasons,
    }
