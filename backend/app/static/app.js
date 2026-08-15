/**
 * LifeGift Chatbot Client Application
 */

document.addEventListener("DOMContentLoaded", () => {
  let currentSessionId = null;
  const messagesContainer = document.getElementById("messages-container");
  const chatInput = document.getElementById("chat-input");
  const sendButton = document.getElementById("send-button");
  const userSelect = document.getElementById("user-select");
  const productModal = document.getElementById("product-modal");
  const modalBody = document.getElementById("modal-body");
  const modalCloseBtn = document.getElementById("modal-close-btn");

  // Format VND Currency
  const formatCurrency = (val) => {
    if (val === null || val === undefined) return "";
    return new Intl.NumberFormat("vi-VN").format(val) + "đ";
  };

  // Scroll chat to bottom
  const scrollToBottom = () => {
    const viewport = document.querySelector(".chat-viewport");
    viewport.scrollTop = viewport.scrollHeight;
  };

  // Append a User Message
  const appendUserMessage = (text) => {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message user-message animate-fade-in";
    msgDiv.innerHTML = `
      <div class="message-avatar">
        <div class="avatar-badge">Bạn</div>
      </div>
      <div class="message-body">
        <div class="message-author">Bạn</div>
        <div class="message-content">${escapeHtml(text)}</div>
      </div>
    `;
    messagesContainer.appendChild(msgDiv);
    scrollToBottom();
  };

  // Append a Loading Indicator
  const appendLoadingIndicator = () => {
    const loadingDiv = document.createElement("div");
    loadingDiv.id = "assistant-loading";
    loadingDiv.className = "message assistant-message animate-fade-in";
    loadingDiv.innerHTML = `
      <div class="message-avatar">
        <div class="avatar-badge">LG</div>
      </div>
      <div class="message-body">
        <div class="message-author">Trợ Lý LifeGift</div>
        <div class="message-content">
          <div class="typing-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    `;
    messagesContainer.appendChild(loadingDiv);
    scrollToBottom();
  };

  const removeLoadingIndicator = () => {
    const el = document.getElementById("assistant-loading");
    if (el) el.remove();
  };

  // Append Assistant Message with Product Cards
  const appendAssistantMessage = (answer, products = []) => {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message assistant-message animate-fade-in";

    let productsHtml = "";
    if (products && products.length > 0) {
      productsHtml = `
        <div class="product-cards-grid">
          ${products.map(p => `
            <div class="product-card">
              <div class="product-card-img-wrapper">
                <img src="${p.image_url || 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600'}" alt="${escapeHtml(p.name)}" class="product-card-img" />
                ${p.sale_price ? `<span class="discount-badge">Giảm giá</span>` : ""}
                <span class="availability-badge ${p.is_available ? 'in-stock' : 'out-of-stock'}">
                  ${p.is_available ? `Còn hàng (${p.available_quantity})` : 'Hết hàng'}
                </span>
              </div>
              <div class="product-card-content">
                <div class="product-origin-tag">📍 ${escapeHtml(p.origin || 'Việt Nam')}</div>
                <div class="product-card-title">${escapeHtml(p.name)}</div>
                ${p.reason ? `<div class="recommendation-reason">💡 ${escapeHtml(p.reason)}</div>` : ""}
                <div class="product-card-pricing">
                  <span class="effective-price">${formatCurrency(p.effective_price)}</span>
                  ${p.sale_price ? `<span class="original-price">${formatCurrency(p.price)}</span>` : ""}
                </div>
                <button class="view-detail-btn" data-product-id="${p.id}">Xem chi tiết & Chứng chỉ</button>
              </div>
            </div>
          `).join("")}
        </div>
      `;
    }

    msgDiv.innerHTML = `
      <div class="message-avatar">
        <div class="avatar-badge">LG</div>
      </div>
      <div class="message-body">
        <div class="message-author">Trợ Lý LifeGift</div>
        <div class="message-content">${formatAnswerMarkdown(answer)}</div>
        ${productsHtml}
      </div>
    `;
    messagesContainer.appendChild(msgDiv);
    scrollToBottom();

    // Attach click listeners to product detail buttons
    msgDiv.querySelectorAll(".view-detail-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const prodId = btn.getAttribute("data-product-id");
        openProductModal(prodId);
      });
    });
  };

  // Open Product Modal
  const openProductModal = async (productId) => {
    modalBody.innerHTML = `<div style="text-align:center; padding: 40px;"><div class="typing-dots"><span></span><span></span><span></span></div><p style="margin-top:12px; color:#666;">Đang tải thông tin chi tiết...</p></div>`;
    productModal.classList.remove("hidden");

    try {
      const res = await fetch(`/api/products/${productId}`);
      if (!res.ok) throw new Error("Không thể tải thông tin sản phẩm");
      const prod = await res.json();

      let certsHtml = "<span style='font-size:0.85rem; color:#777;'>Chưa có chứng chỉ niêm yết</span>";
      if (prod.certificates && prod.certificates.length > 0) {
        certsHtml = prod.certificates.map(c => `
          <div class="cert-pill">
            <span>🛡️</span>
            <span>${escapeHtml(c.name)} (${escapeHtml(c.certificate_code || 'Chính thức')}) - Cấp bởi: ${escapeHtml(c.issuer || 'Cơ quan thẩm quyền')}</span>
          </div>
        `).join("");
      }

      modalBody.innerHTML = `
        <div style="display:flex; gap:20px; flex-wrap:wrap; margin-bottom:16px;">
          <img src="${prod.image_url || 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=600'}" style="width:160px; height:160px; object-fit:cover; border-radius:12px; border:1px solid #e2ece5;" />
          <div style="flex:1;">
            <div style="font-size:0.75rem; color:#c87a32; font-weight:700; text-transform:uppercase;">${escapeHtml(prod.category_name || 'Nông sản')} - ${escapeHtml(prod.brand_name || 'LifeGift')}</div>
            <h2 style="font-size:1.25rem; font-weight:800; color:#144734; margin:4px 0 8px;">${escapeHtml(prod.name)}</h2>
            <div style="display:flex; align-items:baseline; gap:10px; margin-bottom:8px;">
              <span style="font-size:1.3rem; font-weight:800; color:#144734;">${formatCurrency(prod.effective_price)}</span>
              ${prod.sale_price ? `<span style="font-size:0.9rem; color:#888; text-decoration:line-through;">${formatCurrency(prod.price)}</span>` : ""}
            </div>
            <div style="font-size:0.85rem; color:#2e7d32; font-weight:600;">
              📍 Xuất xứ: ${escapeHtml(prod.origin || 'Việt Nam')} | 📦 Tồn kho khả dụng: ${prod.available_quantity} sản phẩm
            </div>
          </div>
        </div>

        <div class="modal-section-title">Chứng chỉ an toàn & tiêu chuẩn chất lượng</div>
        <div class="modal-badges-row">${certsHtml}</div>

        ${prod.taste_profile ? `
          <div class="modal-section-title">Hương vị & Cảm quan đặc trưng</div>
          <div class="modal-section-body">${escapeHtml(prod.taste_profile)}</div>
        ` : ""}

        ${prod.ingredients ? `
          <div class="modal-section-title">Thành phần nguyên liệu</div>
          <div class="modal-section-body">${escapeHtml(prod.ingredients)}</div>
        ` : ""}

        ${prod.key_benefits ? `
          <div class="modal-section-title">Công dụng & Lợi ích sức khỏe</div>
          <div class="modal-section-body">${escapeHtml(prod.key_benefits)}</div>
        ` : ""}

        ${prod.usage_instructions ? `
          <div class="modal-section-title">Hướng dẫn sử dụng & Pha chế</div>
          <div class="modal-section-body">${escapeHtml(prod.usage_instructions)}</div>
        ` : ""}

        ${prod.product_story ? `
          <div class="modal-section-title">Câu chuyện nguồn gốc sản phẩm</div>
          <div class="modal-section-body" style="font-style:italic;">"${escapeHtml(prod.product_story)}"</div>
        ` : ""}
      `;
    } catch (err) {
      modalBody.innerHTML = `<div style="color:#c0392b; padding:20px; text-align:center;">Lỗi: ${err.message}</div>`;
    }
  };

  // Close Modal Listeners
  modalCloseBtn.addEventListener("click", () => productModal.classList.add("hidden"));
  productModal.addEventListener("click", (e) => {
    if (e.target === productModal) productModal.classList.add("hidden");
  });

  // Send Message
  const sendMessage = async (messageText) => {
    const text = messageText || chatInput.value.trim();
    if (!text) return;

    appendUserMessage(text);
    chatInput.value = "";
    chatInput.style.height = "auto";
    sendButton.disabled = true;
    appendLoadingIndicator();

    const headers = { "Content-Type": "application/json" };
    const selectedUserId = userSelect.value;
    if (selectedUserId) {
      headers["X-User-Id"] = selectedUserId;
    }

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          session_id: currentSessionId,
          message: text,
        }),
      });

      removeLoadingIndicator();
      sendButton.disabled = false;

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        appendAssistantMessage(errorData.detail || "Đã xảy ra lỗi khi kết nối đến hệ thống. Vui lòng thử lại!");
        return;
      }

      const data = await response.json();
      currentSessionId = data.session_id;
      appendAssistantMessage(data.answer, data.products);
    } catch (error) {
      removeLoadingIndicator();
      sendButton.disabled = false;
      appendAssistantMessage("Không thể gửi tin nhắn. Vui lòng kiểm tra kết nối mạng và thử lại.");
    }
  };

  // Event Listeners for Input and Send
  sendButton.addEventListener("click", () => sendMessage());

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
  });

  // Prompt Chips Click Handlers
  document.querySelectorAll(".prompt-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const promptText = chip.getAttribute("data-prompt");
      sendMessage(promptText);
    });
  });

  // Helper Escape HTML
  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Format basic Markdown into HTML
  function formatAnswerMarkdown(text) {
    if (!text) return "";
    let html = escapeHtml(text);
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Bullet lists
    html = html.replace(/^\s*-\s+(.*)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");
    return html;
  }
});
