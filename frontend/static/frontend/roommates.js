const roommateState = {
    universities: [],
    districts: [],
    wards: [],
    tags: [],
    posts: [],
    isAuthenticated: document.querySelector("meta[name='is-authenticated']").content === "true",
    isStudent: document.querySelector("meta[name='is-student']").content === "true",
};

const roommateEls = {
    query: document.querySelector("#roommateQuery"),
    type: document.querySelector("#roommateType"),
    university: document.querySelector("#roommateUniversity"),
    district: document.querySelector("#roommateDistrict"),
    minBudget: document.querySelector("#roommateMinBudget"),
    maxBudget: document.querySelector("#roommateMaxBudget"),
    tags: document.querySelector("#roommateTags"),
    apply: document.querySelector("#applyRoommateFilters"),
    reset: document.querySelector("#resetRoommateFilters"),
    list: document.querySelector("#roommateList"),
    resultCount: document.querySelector("#roommateResultCount"),
    status: document.querySelector("#roommateStatus"),
    matchBox: document.querySelector("#roommateMatchBox"),
    matchList: document.querySelector("#roommateMatchList"),
    matchCount: document.querySelector("#roommateMatchCount"),
    heroPostCount: document.querySelector("#heroPostCount"),
    heroMatchCount: document.querySelector("#heroMatchCount"),
    form: document.querySelector("#roommateForm"),
    formTags: document.querySelector("#roommateFormTags"),
};

function roommateEndpoint(path, params = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
        if (Array.isArray(value)) {
            value.filter(Boolean).forEach((item) => url.searchParams.append(key, item));
        } else if (value !== undefined && value !== null && value !== "") {
            url.searchParams.set(key, value);
        }
    });
    return url;
}

async function roommateFetchJson(path, params) {
    const response = await fetch(roommateEndpoint(path, params));
    if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
    }
    return response.json();
}

function csrfToken() {
    return document.querySelector("meta[name='csrf-token']").content;
}

function textNode(tagName, text, className) {
    const element = document.createElement(tagName);
    if (className) {
        element.className = className;
    }
    element.textContent = text;
    return element;
}

function money(value) {
    if (!value) {
        return "Chưa cập nhật";
    }
    return new Intl.NumberFormat("vi-VN", {
        style: "currency",
        currency: "VND",
        maximumFractionDigits: 0,
    }).format(Number(value));
}

function showRoommateStatus(message, isError = false) {
    roommateEls.status.hidden = !message;
    roommateEls.status.textContent = message || "";
    roommateEls.status.style.background = isError ? "#fef2f2" : "#fff7ed";
    roommateEls.status.style.color = isError ? "#991b1b" : "#9a3412";
}

function selectedTagIds() {
    return Array.from(document.querySelectorAll("input[name='roommate_lifestyle_tag']:checked")).map(
        (input) => input.value,
    );
}

function currentRoommateFilters() {
    return {
        q: roommateEls.query.value.trim(),
        type: roommateEls.type.value,
        university: roommateEls.university.value,
        district: roommateEls.district.value,
        min_budget: roommateEls.minBudget.value,
        max_budget: roommateEls.maxBudget.value,
        lifestyle_tag: selectedTagIds(),
    };
}

function fillSelect(select, items, labelFn) {
    items.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent = labelFn(item);
        select.append(option);
    });
}

function renderReferenceData() {
    fillSelect(roommateEls.university, roommateState.universities, (item) => `${item.short_name || "UNI"} - ${item.name}`);
    fillSelect(roommateEls.district, roommateState.districts, (item) => item.name);

    if (roommateEls.form) {
        fillSelect(roommateEls.form.elements.university, roommateState.universities, (item) => item.name);
        fillSelect(roommateEls.form.elements.ward, roommateState.wards, (item) => `${item.name}, ${item.district_name}`);
    }

    roommateEls.tags.replaceChildren();
    if (roommateEls.formTags) {
        roommateEls.formTags.replaceChildren();
    }
    roommateState.tags.forEach((tag) => {
        const filterLabel = document.createElement("label");
        filterLabel.className = "check";
        const filterInput = document.createElement("input");
        filterInput.type = "checkbox";
        filterInput.name = "roommate_lifestyle_tag";
        filterInput.value = tag.id;
        filterLabel.append(filterInput, textNode("span", tag.name));
        roommateEls.tags.append(filterLabel);

        if (roommateEls.formTags) {
            const formLabel = document.createElement("label");
            formLabel.className = "check";
            const formInput = document.createElement("input");
            formInput.type = "checkbox";
            formInput.name = "lifestyle_tags";
            formInput.value = tag.id;
            formLabel.append(formInput, textNode("span", tag.name));
            roommateEls.formTags.append(formLabel);
        }
    });
}

function renderEmptyRoommates() {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.append(
        textNode("p", "Không có kết quả", "eyebrow"),
        textNode("h2", "Chưa có bài ghép trọ phù hợp"),
        textNode("p", "Thử giảm điều kiện lọc hoặc tạo bài nhu cầu mới nếu bạn là sinh viên.", "muted"),
    );
    roommateEls.list.replaceChildren(empty);
}

function roommateCard(post) {
    const card = document.createElement("article");
    card.className = "room-card roommate-card";

    const badge = document.createElement("div");
    badge.className = "thumb roommate-badge";
    badge.append(textNode("span", post.type === "has_room" ? "CÓ PHÒNG" : "TÌM CÙNG"));

    const content = document.createElement("div");
    const budget = `${money(post.budget_min)} - ${money(post.budget_max)}`;
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.append(
        textNode("span", post.university_name || "Chưa chọn trường"),
        textNode("span", post.district_name || post.preferred_districts.map((item) => item.name).join(", ") || "Chưa chọn khu vực"),
        textNode("span", `${post.available_slots} chỗ trống`),
    );

    const tags = document.createElement("div");
    tags.className = "tags";
    post.lifestyle_tags.slice(0, 4).forEach((tag) => tags.append(textNode("span", tag.name, "tag")));

    content.append(
        textNode("h3", post.title),
        textNode("div", budget, "price"),
        meta,
        textNode("p", post.description || post.address || "Người đăng chưa bổ sung mô tả.", "muted"),
        tags,
        textNode("span", post.contact_phone ? `Liên hệ: ${post.contact_phone}` : "Liên hệ sau khi trao đổi", "card-link"),
    );

    card.append(badge, content);
    return card;
}

function renderRoommatePosts() {
    roommateEls.resultCount.textContent = `${roommateState.posts.length} bài`;
    if (roommateEls.heroPostCount) {
        roommateEls.heroPostCount.textContent = roommateState.posts.length;
    }
    if (!roommateState.posts.length) {
        renderEmptyRoommates();
        return;
    }
    roommateEls.list.replaceChildren();
    roommateState.posts.forEach((post) => roommateEls.list.append(roommateCard(post)));
}

function renderMatches(items) {
    if (!items.length) {
        roommateEls.matchBox.hidden = true;
        if (roommateEls.heroMatchCount) {
            roommateEls.heroMatchCount.textContent = "0";
        }
        return;
    }
    roommateEls.matchBox.hidden = false;
    roommateEls.matchCount.textContent = `${items.length} gợi ý`;
    if (roommateEls.heroMatchCount) {
        roommateEls.heroMatchCount.textContent = items.length;
    }
    roommateEls.matchList.replaceChildren();
    items.slice(0, 4).forEach((post) => {
        const element = document.createElement("div");
        element.className = "recommendation-item";
        const copy = document.createElement("div");
        copy.append(
            textNode("strong", post.title),
            textNode("span", post.match.reasons.join(" · ")),
        );
        element.append(copy, textNode("span", `${post.match.score}%`));
        roommateEls.matchList.append(element);
    });
}

async function loadRoommates() {
    showRoommateStatus("Đang tải bài ghép trọ...");
    try {
        const data = await roommateFetchJson("/api/roommate-posts/", currentRoommateFilters());
        roommateState.posts = data.results || [];
        showRoommateStatus("");
        renderRoommatePosts();
    } catch (error) {
        showRoommateStatus("Không tải được danh sách ghép trọ. Hãy kiểm tra server Django và API.", true);
        console.error(error);
    }
}

async function loadMatches() {
    if (!roommateState.isStudent) {
        return;
    }
    try {
        const data = await roommateFetchJson("/api/roommate-posts/matches/");
        renderMatches(data);
    } catch (error) {
        console.error(error);
    }
}

function formPayload(form) {
    const data = new FormData(form);
    const payload = {};
    for (const [key, value] of data.entries()) {
        if (key !== "lifestyle_tags" && value !== "") {
            payload[key] = value;
        }
    }
    payload.lifestyle_tags = data.getAll("lifestyle_tags");
    return payload;
}

async function submitRoommatePost(event) {
    event.preventDefault();
    const response = await fetch("/api/roommate-posts/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken(),
        },
        body: JSON.stringify(formPayload(event.currentTarget)),
    });
    if (!response.ok) {
        const error = await response.json();
        showRoommateStatus(JSON.stringify(error), true);
        return;
    }
    event.currentTarget.reset();
    showRoommateStatus("Đã đăng bài ghép trọ.");
    await loadRoommates();
    await loadMatches();
}

async function bootstrapRoommates() {
    try {
        const [universities, districts, wards, tags] = await Promise.all([
            roommateFetchJson("/api/universities/"),
            roommateFetchJson("/api/districts/"),
            roommateFetchJson("/api/wards/"),
            roommateFetchJson("/api/lifestyle-tags/"),
        ]);
        roommateState.universities = universities.results || [];
        roommateState.districts = districts.results || [];
        roommateState.wards = wards.results || [];
        roommateState.tags = tags.results || [];
        renderReferenceData();
        await loadRoommates();
        await loadMatches();
    } catch (error) {
        showRoommateStatus("Không tải được dữ liệu cần thiết. Hãy thử tải lại trang sau ít phút.", true);
        console.error(error);
    }
}

roommateEls.apply.addEventListener("click", loadRoommates);
roommateEls.reset.addEventListener("click", () => {
    roommateEls.query.value = "";
    roommateEls.type.value = "";
    roommateEls.university.value = "";
    roommateEls.district.value = "";
    roommateEls.minBudget.value = "";
    roommateEls.maxBudget.value = "";
    document.querySelectorAll("input[name='roommate_lifestyle_tag']").forEach((input) => {
        input.checked = false;
    });
    loadRoommates();
});
roommateEls.query.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        loadRoommates();
    }
});
if (roommateEls.form) {
    roommateEls.form.addEventListener("submit", submitRoommatePost);
}

bootstrapRoommates();
