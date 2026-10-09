/**
 * notifications-ui.js — Automated Multi-Channel Notification UI for CampusLink
 * Replaces manual email/WhatsApp coordination with automated, targeted notifications for:
 * 1. Shortlisting & Interview Schedules
 * 2. Document Submission Deadlines
 * 3. Offer Status Updates
 * 4. Drive Announcements with Eligibility Criteria
 */

(function () {
  let notificationsData = [];
  let currentCategory = "all";
  let activeTab = "all";

  // Inject CSS styles for notification bell, badge, and drawer
  const styleEl = document.createElement("style");
  styleEl.textContent = `
    .notif-bell-btn {
      position: relative;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 8px 12px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 14px;
      font-weight: 600;
      color: #334155;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      transition: all 0.2s ease;
    }
    .notif-bell-btn:hover {
      background: #f8fafc;
      border-color: #cbd5e1;
      transform: translateY(-1px);
    }
    .notif-badge {
      background: #ef4444;
      color: #ffffff;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 10px;
      min-width: 18px;
      text-align: center;
      line-height: 1.2;
    }
    .notif-badge.zero {
      display: none;
    }

    /* Notification Drawer Overlay */
    .notif-drawer-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.45);
      backdrop-filter: blur(4px);
      z-index: 1050;
      justify-content: flex-end;
    }
    .notif-drawer-overlay.active {
      display: flex;
    }
    .notif-drawer {
      background: #ffffff;
      width: 100%;
      max-width: 520px;
      height: 100vh;
      display: flex;
      flex-direction: column;
      box-shadow: -4px 0 25px rgba(0,0,0,0.15);
      animation: slideInRight 0.25s ease-out;
    }
    @keyframes slideInRight {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }
    .notif-header {
      padding: 18px 20px;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #f8fafc;
    }
    .notif-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 700;
      color: #0f172a;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .notif-close-btn {
      background: none;
      border: none;
      font-size: 24px;
      color: #64748b;
      cursor: pointer;
      line-height: 1;
    }
    .notif-tabs-bar {
      padding: 10px 16px;
      background: #ffffff;
      border-bottom: 1px solid #f1f5f9;
      display: flex;
      gap: 6px;
      overflow-x: auto;
      scrollbar-width: thin;
    }
    .notif-tab {
      padding: 5px 11px;
      border: 1px solid #e2e8f0;
      border-radius: 20px;
      font-size: 12px;
      background: #f8fafc;
      color: #475569;
      cursor: pointer;
      white-space: nowrap;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.15s ease;
    }
    .notif-tab:hover {
      background: #edf2f7;
    }
    .notif-tab.active {
      background: #2563eb;
      color: #ffffff;
      border-color: #2563eb;
      font-weight: 600;
    }
    .notif-list-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }
    .notif-card {
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 12px;
      background: #ffffff;
      transition: all 0.2s ease;
      position: relative;
    }
    .notif-card.unread {
      border-left: 4px solid #2563eb;
      background: #f8faff;
    }
    .notif-card.read {
      opacity: 0.85;
      border-left: 4px solid #94a3b8;
    }
    .notif-card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 6px;
      gap: 8px;
    }
    .notif-cat-chip {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 2px 7px;
      border-radius: 4px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .cat-interview { background: #dbeafe; color: #1e40af; }
    .cat-deadline { background: #fee2e2; color: #991b1b; }
    .cat-offer { background: #dcfce7; color: #166534; }
    .cat-drive { background: #fef3c7; color: #92400e; }
    .cat-general { background: #f1f5f9; color: #475569; }

    .notif-channel-tag {
      font-size: 10.5px;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
      background: #f1f5f9;
      color: #334155;
    }
    .tag-whatsapp {
      background: #dcfce7;
      color: #15803d;
    }
    .tag-email {
      background: #e0e7ff;
      color: #3730a3;
    }
    .notif-title {
      font-size: 13.5px;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 5px;
    }
    .notif-message {
      font-size: 12.8px;
      color: #334155;
      line-height: 1.45;
      margin-bottom: 8px;
    }
    .notif-meta-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      margin-top: 6px;
    }
    .notif-meta-chip {
      font-size: 11px;
      background: #f1f5f9;
      color: #475569;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
    }
    .notif-actions-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px solid #f1f5f9;
      font-size: 11.5px;
    }
    .notif-btn-preview {
      background: none;
      border: 1px solid #cbd5e1;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      cursor: pointer;
      color: #475569;
      font-weight: 500;
    }
    .notif-btn-preview:hover {
      background: #f8fafc;
      color: #0f172a;
    }
    .notif-preview-box {
      display: none;
      background: #f8fafc;
      border: 1px dashed #cbd5e1;
      border-radius: 6px;
      padding: 8px 10px;
      margin-top: 8px;
      font-size: 11.5px;
      white-space: pre-wrap;
      font-family: inherit;
      color: #334155;
      line-height: 1.4;
    }
  `;
  document.head.appendChild(styleEl);

  // Create Drawer Modal markup
  const drawerOverlay = document.createElement("div");
  drawerOverlay.id = "notifDrawerOverlay";
  drawerOverlay.className = "notif-drawer-overlay";
  drawerOverlay.innerHTML = `
    <div class="notif-drawer" onclick="event.stopPropagation()">
      <div class="notif-header">
        <div>
          <h3>
            <span>🔔</span> Automated Communication Center
          </h3>
          <span style="font-size:12px;color:#64748b;">
            Targeted notifications replacing manual email &amp; WhatsApp coordination
          </span>
        </div>
        <button class="notif-close-btn" onclick="closeNotificationDrawer()">&times;</button>
      </div>

      <div class="notif-tabs-bar">
        <button class="notif-tab active" data-cat="all" onclick="filterNotifs('all')">
          All (<span id="tabCountAll">0</span>)
        </button>
        <button class="notif-tab" data-cat="shortlist_interview" onclick="filterNotifs('shortlist_interview')">
          🎯 Interviews (<span id="tabCountInterview">0</span>)
        </button>
        <button class="notif-tab" data-cat="document_deadline" onclick="filterNotifs('document_deadline')">
          ⏰ Deadlines (<span id="tabCountDeadline">0</span>)
        </button>
        <button class="notif-tab" data-cat="offer_status" onclick="filterNotifs('offer_status')">
          🎉 Offers (<span id="tabCountOffer">0</span>)
        </button>
        <button class="notif-tab" data-cat="drive_announcement" onclick="filterNotifs('drive_announcement')">
          📢 Drives (<span id="tabCountDrive">0</span>)
        </button>
      </div>

      <div style="padding:8px 16px;background:#f8fafc;border-bottom:1px solid #f1f5f9;display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:12px;color:#64748b;" id="notifStatusSummary">Loading automated notifications...</span>
        <button type="button" onclick="markAllNotifsAsRead()" style="background:none;border:none;color:#2563eb;font-size:12px;font-weight:600;cursor:pointer;">
          Mark all as read
        </button>
      </div>

      <div class="notif-list-body" id="notifListContainer">
        <div style="text-align:center;padding:40px 20px;color:#94a3b8;font-size:13px;">
          Loading automated dispatches...
        </div>
      </div>
    </div>
  `;
  drawerOverlay.addEventListener("click", closeNotificationDrawer);
  document.body.appendChild(drawerOverlay);

  // Mount notification bell into top navigation or page-head
  function mountNotificationBell() {
    let mountPoint = document.getElementById("notificationBellMount");
    if (!mountPoint) {
      const pageHead = document.querySelector(".page-head");
      if (pageHead) {
        mountPoint = document.createElement("div");
        mountPoint.style.display = "flex";
        mountPoint.style.alignItems = "center";
        mountPoint.style.gap = "10px";
        pageHead.appendChild(mountPoint);
      } else {
        const nav = document.querySelector(".nav");
        if (nav) {
          mountPoint = document.createElement("div");
          mountPoint.style.padding = "10px 14px";
          nav.insertBefore(mountPoint, nav.querySelector(".nav-links"));
        }
      }
    }

    if (mountPoint && !document.getElementById("btnNotificationBell")) {
      const bellBtn = document.createElement("button");
      bellBtn.type = "button";
      bellBtn.id = "btnNotificationBell";
      bellBtn.className = "notif-bell-btn";
      bellBtn.innerHTML = `
        <span>🔔</span>
        <span>Alerts</span>
        <span class="notif-badge zero" id="navNotifBadge">0</span>
      `;
      bellBtn.onclick = openNotificationDrawer;
      mountPoint.appendChild(bellBtn);
    }
  }

  // Load and render notifications from API
  async function loadNotifications() {
    try {
      if (typeof getNotifications !== "function") return;
      const res = await getNotifications();
      notificationsData = res.notifications || [];
      const counts = res.category_counts || {};
      const unread = res.unread_count || 0;

      // Update badge
      const badge = document.getElementById("navNotifBadge");
      if (badge) {
        badge.textContent = unread;
        badge.className = unread > 0 ? "notif-badge" : "notif-badge zero";
      }

      // Update tab counts
      const setC = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val || 0;
      };
      setC("tabCountAll", res.total || notificationsData.length);
      setC("tabCountInterview", counts.shortlist_interview);
      setC("tabCountDeadline", counts.document_deadline);
      setC("tabCountOffer", counts.offer_status);
      setC("tabCountDrive", counts.drive_announcement);

      renderNotifsList();
    } catch (err) {
      console.warn("Could not load notifications:", err);
    }
  }

  function renderNotifsList() {
    const container = document.getElementById("notifListContainer");
    const summary = document.getElementById("notifStatusSummary");
    if (!container) return;

    const filtered = currentCategory === "all"
      ? notificationsData
      : notificationsData.filter(n => n.category === currentCategory);

    if (summary) {
      summary.textContent = `Showing ${filtered.length} notification(s)`;
    }

    if (!filtered.length) {
      container.innerHTML = `
        <div style="text-align:center;padding:50px 20px;color:#94a3b8;font-size:13.5px;">
          <div style="font-size:32px;margin-bottom:8px;">📭</div>
          No notifications found in this category.
        </div>
      `;
      return;
    }

    const catBadge = (cat) => {
      switch (cat) {
        case "shortlist_interview":
          return `<span class="notif-cat-chip cat-interview">🎯 Interview Schedule</span>`;
        case "document_deadline":
          return `<span class="notif-cat-chip cat-deadline">⏰ Submission Deadline</span>`;
        case "offer_status":
          return `<span class="notif-cat-chip cat-offer">🎉 Offer Status</span>`;
        case "drive_announcement":
          return `<span class="notif-cat-chip cat-drive">📢 Drive Announcement</span>`;
        default:
          return `<span class="notif-cat-chip cat-general">🔔 Notice</span>`;
      }
    };

    container.innerHTML = filtered.map(n => {
      const isUnread = !n.read;
      const meta = n.meta_data || {};
      const metaChips = [];

      if (meta.company) metaChips.push(`<span class="notif-meta-chip">🏢 ${escapeHtml(meta.company)}</span>`);
      if (meta.role) metaChips.push(`<span class="notif-meta-chip">💼 ${escapeHtml(meta.role)}</span>`);
      if (meta.date) metaChips.push(`<span class="notif-meta-chip">📅 ${escapeHtml(meta.date)}</span>`);
      if (meta.time_slot) metaChips.push(`<span class="notif-meta-chip">⏰ ${escapeHtml(meta.time_slot)}</span>`);
      if (meta.deadline) metaChips.push(`<span class="notif-meta-chip" style="background:#fee2e2;color:#991b1b;font-weight:700;">⏳ Deadline: ${escapeHtml(meta.deadline)}</span>`);
      if (meta.ctc_lpa) metaChips.push(`<span class="notif-meta-chip" style="background:#dcfce7;color:#166534;font-weight:700;">💰 ${escapeHtml(String(meta.ctc_lpa))} LPA</span>`);
      if (meta.eligibility_summary) metaChips.push(`<span class="notif-meta-chip">🎯 ${escapeHtml(meta.eligibility_summary)}</span>`);

      // Simulated WhatsApp and Email templates
      const whatsappText = `🔔 *CampusLink Alert*\nDear *${escapeHtml(n.recipient_name || "Student")}*,\n${escapeHtml(n.message)}\n\nStatus: Delivered ✓✓`;
      const emailText = `Subject: [CampusLink] ${escapeHtml(n.title)}\nTo: ${escapeHtml(n.recipient_email || "student@campus.edu")}\n\n${escapeHtml(n.message)}`;

      return `
        <div class="notif-card ${isUnread ? 'unread' : 'read'}" id="notif-card-${n.id}">
          <div class="notif-card-top">
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
              ${catBadge(n.category)}
              <span class="notif-channel-tag tag-whatsapp">💬 WhatsApp ✓✓</span>
              <span class="notif-channel-tag tag-email">📧 Email</span>
              <span class="notif-channel-tag">📱 In-App</span>
            </div>
            <span style="font-size:11px;color:#94a3b8;">${formatDateRel(n.created_at)}</span>
          </div>

          <div class="notif-title">${escapeHtml(n.title)}</div>
          <div class="notif-message">${escapeHtml(n.message)}</div>

          ${metaChips.length ? `<div class="notif-meta-chips">${metaChips.join("")}</div>` : ""}

          <div class="notif-actions-row">
            <div style="display:flex;gap:6px;">
              <button type="button" class="notif-btn-preview" onclick="toggleNotifPreview('wa-${n.id}')">💬 WhatsApp Template</button>
              <button type="button" class="notif-btn-preview" onclick="toggleNotifPreview('em-${n.id}')">📧 Email Dispatch</button>
            </div>
            <div>
              ${
                isUnread
                  ? `<button type="button" onclick="markSingleNotifRead(${n.id})" style="background:none;border:none;color:#2563eb;cursor:pointer;font-weight:600;font-size:11.5px;">Mark read</button>`
                  : `<span style="color:#94a3b8;font-size:11px;">✓ Read</span>`
              }
            </div>
          </div>

          <div id="wa-${n.id}" class="notif-preview-box" style="border-left:3px solid #22c55e;">
<strong>WhatsApp Dispatch Payload (Delivered):</strong>
${whatsappText}
          </div>

          <div id="em-${n.id}" class="notif-preview-box" style="border-left:3px solid #6366f1;">
<strong>Email Dispatch Payload (Sent):</strong>
${emailText}
          </div>
        </div>
      `;
    }).join("");
  }

  function formatDateRel(isoStr) {
    if (!isoStr) return "";
    try {
      const d = new Date(isoStr);
      const now = new Date();
      const diffMs = now - d;
      const mins = Math.floor(diffMs / 60000);
      if (mins < 2) return "Just now";
      if (mins < 60) return `${mins}m ago`;
      const hrs = Math.floor(mins / 60);
      if (hrs < 24) return `${hrs}h ago`;
      return d.toLocaleDateString();
    } catch {
      return "";
    }
  }

  // Global functions attached to window
  window.openNotificationDrawer = function () {
    const el = document.getElementById("notifDrawerOverlay");
    if (el) el.classList.add("active");
    loadNotifications();
  };

  window.closeNotificationDrawer = function () {
    const el = document.getElementById("notifDrawerOverlay");
    if (el) el.classList.remove("active");
  };

  window.filterNotifs = function (cat) {
    currentCategory = cat;
    document.querySelectorAll(".notif-tab").forEach(tab => {
      tab.classList.toggle("active", tab.getAttribute("data-cat") === cat);
    });
    renderNotifsList();
  };

  window.toggleNotifPreview = function (id) {
    const el = document.getElementById(id);
    if (el) {
      el.style.display = el.style.display === "block" ? "none" : "block";
    }
  };

  window.markSingleNotifRead = async function (id) {
    try {
      if (typeof markNotificationRead === "function") {
        await markNotificationRead(id);
        const card = document.getElementById(`notif-card-${id}`);
        if (card) {
          card.classList.remove("unread");
          card.classList.add("read");
        }
        await loadNotifications();
      }
    } catch (err) {
      console.warn("Could not mark notification read:", err);
    }
  };

  window.markAllNotifsAsRead = async function () {
    try {
      if (typeof markAllNotificationsRead === "function") {
        await markAllNotificationsRead();
        await loadNotifications();
      }
    } catch (err) {
      console.warn("Could not mark all notifications read:", err);
    }
  };

  window.refreshNotificationsUI = loadNotifications;
  window.refreshNotificationUI = loadNotifications;

  // Initialize on DOM load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      mountNotificationBell();
      loadNotifications();
    });
  } else {
    mountNotificationBell();
    loadNotifications();
  }
})();
