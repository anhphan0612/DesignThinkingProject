const roommateState = {
    universities: [],
    districts: [],
    wards: [],
    tags: [],
    posts: [],
    viewMode: "open",
    editingPostId: null,
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
    sort: document.querySelector("#roommateSort"),
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
    formTitle: document.querySelector("#roommateFormTitle"),
    formTags: document.querySelector("#roommateFormTags"),
    cancelEdit: document.querySelector("#cancelRoommateEdit"),
    showOpen: document.querySelector("#showOpenPosts"),
    showMine: document.querySelector("#showMyPosts"),
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

async function roommateSendJson(path, method = "POST", body = {}) {
    const response = await fetch(path, {
        method,
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken(),
        },
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const error = new Error(`Request failed with status ${response.status}`);
        error.payload = payload;
        throw error;
    }
    if (response.status === 204) {
        return {};
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
    if (value === null || value === undefined || value === "") {
        return "Chưa cập nhật";
    }
    const amount = Number(value);
    if (!Number.isFinite(amount)) {
        return "Chưa cập nhật";
    }
    return new Intl.NumberFormat("vi-VN", {
        style: "currency",
        currency: "VND",
        maximumFractionDigits: 0,
    }).format(amount);
}

function postPriceLabel(post) {
    if (post.budget_min && post.budget_max && post.budget_min !== post.budget_max) {
        return `${money(post.budget_min)} - ${money(post.budget_max)}`;
    }
    return money(post.budget_max || post.budget_min);
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
        sort: roommateEls.sort.value,
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
    const title = roommateState.viewMode === "mine" ? "Bạn chưa có bài ghép trọ nào" : "Chưa có bài ghép trọ phù hợp";
    const copy = roommateState.viewMode === "mine"
        ? "Tạo bài mới để tìm người ở ghép hoặc tìm bạn cùng thuê phòng."
        : "Thử giảm điều kiện lọc hoặc tạo bài nhu cầu mới nếu bạn là sinh viên.";
    empty.append(
        textNode("p", "Không có kết quả", "eyebrow"),
        textNode("h2", title),
        textNode("p", copy, "muted"),
    );
    roommateEls.list.replaceChildren(empty);
}

async function contactRoommatePost(post, button) {
    if (!roommateState.isAuthenticated) {
        window.location.href = `/auth/login/?next=/roommates/`;
        return;
    }
    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = "Đang mở chat...";
    try {
        const data = await roommateSendJson(`/api/roommate-posts/${post.id}/contact/`, "POST");
        showRoommateStatus(data.message || "Đã mở cuộc trò chuyện trong app.");
        if (data.thread_id && window.RentifyChat) {
            await window.RentifyChat.open(data.thread_id, `Chat với ${data.recipient_name || post.posted_by_name}`);
        }
    } catch (error) {
        showRoommateStatus("Không mở được chat. Hãy thử lại.", true);
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}

function roommateCard(post) {
    const card = document.createElement("article");
    card.className = "room-card roommate-card";
    card.tabIndex = 0;
    const roomUrl = post.room?.id ? `/rooms/${post.room.id}/` : "";
    card.setAttribute("role", roomUrl ? "link" : "button");
    card.setAttribute("aria-label", roomUrl ? `Xem phòng của bài ${post.title}` : `Xem thông tin bài ${post.title}`);

    const badge = document.createElement("div");
    badge.className = "thumb roommate-badge";
    badge.append(textNode("span", post.type === "has_room" ? "CÓ PHÒNG" : "TÌM CÙNG"));

    const content = document.createElement("div");
    const budget = postPriceLabel(post);
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.append(
        textNode("span", post.university_name || "Chưa chọn trường"),
        textNode("span", post.district_name || (post.preferred_districts || []).map((item) => item.name).join(", ") || "Chưa chọn khu vực"),
        textNode("span", `${post.available_slots} chỗ trống`),
        textNode("span", post.status_label),
    );

    const tags = document.createElement("div");
    tags.className = "tags";
    (post.lifestyle_tags || []).slice(0, 4).forEach((tag) => tags.append(textNode("span", tag.name, "tag")));

    const details = document.createElement("div");
    details.className = "roommate-inline-detail";
    details.hidden = Boolean(roomUrl);
    const externalRoomSummary = [
        post.external_room_name,
        post.external_room_area ? `${Number(post.external_room_area).toLocaleString("vi-VN")} m²` : "",
        post.external_room_total_rent ? `Tổng thuê ${money(post.external_room_total_rent)}` : "",
    ].filter(Boolean).join(" · ");
    details.append(
        textNode("strong", post.posted_by_name || "Người đăng"),
        textNode("span", post.room ? "Phòng đã có trên nền tảng." : "Phòng do người đang thuê tự khai báo, chưa phải listing chính thức."),
        textNode("span", post.room_verification_level_label || "Chưa xác minh"),
        textNode("span", externalRoomSummary || post.address || post.ward_name || "Chưa cập nhật địa chỉ cụ thể."),
    );

    const cardActions = document.createElement("div");
    cardActions.className = "card-actions-row";
    if (roomUrl) {
        const roomLink = document.createElement("a");
        roomLink.className = "card-link";
        roomLink.href = roomUrl;
        roomLink.textContent = "Xem phòng";
        roomLink.addEventListener("click", (event) => event.stopPropagation());
        cardActions.append(roomLink);
    } else {
        const searchLink = document.createElement("a");
        searchLink.className = "card-link";
        searchLink.href = `/rooms/?q=${encodeURIComponent(post.address || post.ward_name || post.title)}`;
        searchLink.textContent = post.type === "has_room" ? "Tìm phòng liên quan" : "Tìm phòng phù hợp";
        searchLink.addEventListener("click", (event) => event.stopPropagation());
        const detailButton = document.createElement("button");
        detailButton.type = "button";
        detailButton.className = "secondary";
        detailButton.textContent = "Ẩn/hiện liên hệ";
        detailButton.addEventListener("click", (event) => {
            event.stopPropagation();
            details.hidden = !details.hidden;
        });
        cardActions.append(searchLink, detailButton);
    }
    if (roommateState.viewMode !== "mine") {
        const contact = document.createElement("button");
        contact.type = "button";
        contact.className = "secondary";
        contact.textContent = "Nhắn qua app";
        contact.addEventListener("click", (event) => {
            event.stopPropagation();
            contactRoommatePost(post, contact);
        });
        cardActions.append(contact);
    }

    content.append(
        textNode("h3", post.title),
        textNode("div", budget, "price"),
        meta,
        textNode("p", post.description || post.address || "Người đăng chưa bổ sung mô tả.", "muted"),
        tags,
        details,
        cardActions,
    );

    if (roommateState.viewMode === "mine") {
        content.append(ownerActions(post));
    } else {
        content.append(reportAction(post));
    }

    card.append(badge, content);
    card.addEventListener("click", () => {
        if (roomUrl) {
            window.location.href = roomUrl;
            return;
        }
        details.hidden = false;
    });
    card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            if (roomUrl) {
                window.location.href = roomUrl;
                return;
            }
            details.hidden = false;
        }
    });
    return card;
}

function reportAction(post) {
    const actions = document.createElement("div");
    actions.className = "card-actions-row";
    const report = document.createElement("button");
    report.type = "button";
    report.className = "secondary";
    report.textContent = "Báo cáo";
    report.addEventListener("click", async (event) => {
        event.stopPropagation();
        report.disabled = true;
        try {
            await roommateSendJson("/api/reports/", "POST", {
                target_type: "roommate_post",
                roommate_post: post.id,
                reason: "Bài ghép trọ cần kiểm tra",
                details: post.title,
            });
            showRoommateStatus("Đã gửi báo cáo. Admin sẽ kiểm tra bài này.");
        } catch (error) {
            showRoommateStatus("Không gửi được báo cáo. Hãy thử lại.", true);
        } finally {
            report.disabled = false;
        }
    });
    actions.append(report);
    return actions;
}

function ownerActions(post) {
    const actions = document.createElement("div");
    actions.className = "card-actions-row";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "secondary";
    edit.textContent = "Sửa";
    edit.addEventListener("click", (event) => {
        event.stopPropagation();
        startEdit(post);
    });
    actions.append(edit);

    if (post.status === "active") {
        const close = document.createElement("button");
        close.type = "button";
        close.className = "secondary";
        close.textContent = "Đóng bài";
        close.addEventListener("click", (event) => {
            event.stopPropagation();
            closePost(post);
        });
        actions.append(close);
    }

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "danger-inline";
    remove.textContent = "Xóa";
    remove.addEventListener("click", (event) => {
        event.stopPropagation();
        deletePost(post);
    });
    actions.append(remove);
    return actions;
}

function renderRoommatePosts() {
    roommateEls.resultCount.textContent = `${roommateState.posts.length} bài`;
    if (roommateEls.heroPostCount && roommateState.viewMode === "open") {
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
    if (!items.length || roommateState.viewMode === "mine") {
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
    const mine = roommateState.viewMode === "mine";
    showRoommateStatus(mine ? "Đang tải bài của bạn..." : "Đang tải bài ghép trọ...");
    try {
        const path = mine ? "/api/roommate-posts/mine/" : "/api/roommate-posts/";
        const data = await roommateFetchJson(path, mine ? {} : currentRoommateFilters());
        roommateState.posts = data.results || [];
        if (!mine && data.search_intelligence?.fallback_used) {
            showRoommateStatus("Không tìm thấy kết quả khớp chính xác với từ khóa, đang hiển thị các bài gần với nhu cầu hơn.");
        } else {
            showRoommateStatus("");
        }
        renderRoommatePosts();
    } catch (error) {
        showRoommateStatus("Không tải được danh sách ghép trọ. Hãy kiểm tra server Django và API.", true);
        console.error(error);
    }
}

async function loadMatches() {
    if (!roommateState.isStudent || roommateState.viewMode === "mine") {
        renderMatches([]);
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
        if (!["lifestyle_tags", "post_id", "rent_price"].includes(key) && value !== "") {
            payload[key] = value;
        }
    }
    const rentPrice = data.get("rent_price");
    if (rentPrice !== "") {
        payload.budget_min = rentPrice;
        payload.budget_max = rentPrice;
    }
    payload.lifestyle_tags = data.getAll("lifestyle_tags");
    return payload;
}

function readableErrors(errorPayload) {
    if (!errorPayload || typeof errorPayload !== "object") {
        return "Không gửi được bài. Hãy kiểm tra lại thông tin.";
    }
    return Object.entries(errorPayload)
        .map(([field, messages]) => {
            const text = Array.isArray(messages) ? messages.join(", ") : String(messages);
            return `${field}: ${text}`;
        })
        .join(" ");
}

async function submitRoommatePost(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const submitButton = form.querySelector("button[type='submit']");
    submitButton.disabled = true;
    const originalText = submitButton.textContent;
    submitButton.textContent = roommateState.editingPostId ? "Đang lưu..." : "Đang đăng...";
    showRoommateStatus(roommateState.editingPostId ? "Đang cập nhật bài ghép trọ..." : "Đang gửi bài ghép trọ...");
    try {
        const payload = formPayload(form);
        if (roommateState.editingPostId) {
            await roommateSendJson(`/api/roommate-posts/${roommateState.editingPostId}/`, "PATCH", payload);
            showRoommateStatus("Đã cập nhật bài ghép trọ.");
        } else {
            await roommateSendJson("/api/roommate-posts/", "POST", payload);
            showRoommateStatus("Đã đăng bài ghép trọ.");
        }
        resetForm();
        await loadRoommates();
        await loadMatches();
    } catch (error) {
        showRoommateStatus(readableErrors(error.payload), true);
        console.error(error);
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = originalText;
    }
}

function startEdit(post) {
    const form = roommateEls.form;
    roommateState.editingPostId = post.id;
    roommateEls.formTitle.textContent = "Sửa bài ghép trọ";
    roommateEls.cancelEdit.hidden = false;
    form.elements.post_id.value = post.id;
    form.elements.title.value = post.title || "";
    form.elements.type.value = post.type || "looking_together";
    form.elements.university.value = post.university || "";
    form.elements.ward.value = post.ward || "";
    form.elements.external_room_name.value = post.external_room_name || "";
    form.elements.address.value = post.address || "";
    form.elements.external_room_area.value = post.external_room_area || "";
    form.elements.external_room_total_rent.value = post.external_room_total_rent || "";
    form.elements.rent_price.value = post.budget_max || post.budget_min || "";
    form.elements.move_in_date.value = post.move_in_date || "";
    form.elements.available_slots.value = post.available_slots || 1;
    form.elements.max_roommates.value = post.max_roommates || 2;
    form.elements.current_occupants.value = post.current_occupants || 0;
    form.elements.gender_preference.value = post.gender_preference || "any";
    form.elements.description.value = post.description || "";
    const selected = new Set((post.lifestyle_tags || []).map((tag) => String(tag.id)));
    form.querySelectorAll("input[name='lifestyle_tags']").forEach((input) => {
        input.checked = selected.has(input.value);
    });
    document.querySelector("#createRoommatePost").scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetForm() {
    if (!roommateEls.form) {
        return;
    }
    roommateEls.form.reset();
    roommateState.editingPostId = null;
    roommateEls.formTitle.textContent = "Tạo bài ghép trọ";
    roommateEls.cancelEdit.hidden = true;
}

async function closePost(post) {
    try {
        await roommateSendJson(`/api/roommate-posts/${post.id}/close/`, "POST");
        showRoommateStatus("Đã đóng bài ghép trọ.");
        await loadRoommates();
    } catch (error) {
        showRoommateStatus("Không đóng được bài. Hãy thử lại.", true);
        console.error(error);
    }
}

async function deletePost(post) {
    try {
        await roommateSendJson(`/api/roommate-posts/${post.id}/`, "DELETE");
        showRoommateStatus("Đã xóa bài khỏi danh sách đang mở.");
        await loadRoommates();
    } catch (error) {
        showRoommateStatus("Không xóa được bài. Hãy thử lại.", true);
        console.error(error);
    }
}

function setViewMode(mode) {
    roommateState.viewMode = mode;
    roommateEls.showOpen?.classList.toggle("active", mode === "open");
    roommateEls.showMine?.classList.toggle("active", mode === "mine");
    loadRoommates();
    loadMatches();
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
roommateEls.sort.addEventListener("change", loadRoommates);
roommateEls.reset.addEventListener("click", () => {
    roommateEls.query.value = "";
    roommateEls.type.value = "";
    roommateEls.university.value = "";
    roommateEls.district.value = "";
    roommateEls.minBudget.value = "";
    roommateEls.maxBudget.value = "";
    roommateEls.sort.value = "newest";
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
roommateEls.showOpen?.addEventListener("click", () => setViewMode("open"));
roommateEls.showMine?.addEventListener("click", () => setViewMode("mine"));
roommateEls.cancelEdit?.addEventListener("click", resetForm);
if (roommateEls.form) {
    roommateEls.form.addEventListener("submit", submitRoommatePost);
}

bootstrapRoommates();
