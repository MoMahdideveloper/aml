/**
 * Property Modal System
 * Compatibility layer for property modal lifecycle and data loading.
 */
(function propertyModalSystemInit(globalScope) {
  "use strict";

  const globalObj = globalScope || (typeof window !== "undefined" ? window : globalThis);

  function notify(message, level) {
    if (typeof globalObj.showNotification === "function") {
      globalObj.showNotification(message, level || "info");
      return;
    }
    if (level === "error" && typeof console !== "undefined") {
      console.error(message);
      return;
    }
    if (typeof console !== "undefined") {
      console.log(message);
    }
  }

  function isDomAvailable() {
    return typeof document !== "undefined" && document && document.body;
  }

  class PropertyModalManager {
    constructor() {
      this.loadingIndicators = new Map();
      this.retryAttempts = 3;
      this.retryDelayMs = 500;
    }

    showLoadingIndicator(message, id) {
      if (!isDomAvailable()) {
        return "no-dom-loading";
      }

      const loadingId = id || `property-loading-${Date.now()}`;
      this.hideLoadingIndicator(loadingId);

      const wrapper = document.createElement("div");
      wrapper.id = loadingId;
      wrapper.className = "property-loading-indicator";
      wrapper.innerHTML = `
        <div style="position:fixed;inset:0;background:rgba(15,23,42,0.45);z-index:9998;"></div>
        <div style="position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:9999;background:#fff;border-radius:12px;padding:14px 16px;min-width:260px;box-shadow:0 20px 50px rgba(2,6,23,0.25);font-family:Inter,sans-serif;">
          <div style="font-weight:700;font-size:14px;color:#0f172a;">${message || "Loading..."}</div>
          <div style="font-size:12px;color:#64748b;margin-top:4px;">Please wait...</div>
        </div>
      `;
      document.body.appendChild(wrapper);
      this.loadingIndicators.set(loadingId, wrapper);
      return loadingId;
    }

    hideLoadingIndicator(loadingId) {
      const node = this.loadingIndicators.get(loadingId);
      if (node && node.parentNode) {
        node.parentNode.removeChild(node);
      }
      this.loadingIndicators.delete(loadingId);
    }

    async fetchWithRetry(url, options, attempts) {
      const maxAttempts = Number.isInteger(attempts) ? attempts : this.retryAttempts;
      let lastError;

      for (let i = 0; i < maxAttempts; i += 1) {
        try {
          const response = await fetch(url, {
            method: "GET",
            headers: {
              Accept: "application/json",
              "X-Requested-With": "XMLHttpRequest",
              ...(options && options.headers ? options.headers : {}),
            },
            ...(options || {}),
          });

          if (!response.ok) {
            if (response.status === 404) {
              throw new Error("Property not found (404)");
            }
            if (response.status >= 500) {
              throw new Error(`Server error (${response.status})`);
            }
            throw new Error(`Request failed (${response.status})`);
          }

          const contentType = (response.headers.get("content-type") || "").toLowerCase();
          if (contentType.indexOf("application/json") !== -1) {
            return response.json();
          }
          return response.text();
        } catch (error) {
          lastError = error;
          if (i < maxAttempts - 1) {
            const delayMs = this.retryDelayMs * Math.pow(2, i);
            await new Promise((resolve) => setTimeout(resolve, delayMs));
          }
        }
      }

      throw lastError || new Error("Request failed");
    }

    async ensureModalTemplate(modalId, templateUrl) {
      if (!isDomAvailable()) {
        return null;
      }

      let modalEl = document.getElementById(modalId);
      if (modalEl) {
        return modalEl;
      }

      if (templateUrl) {
        try {
          const response = await fetch(templateUrl, {
            method: "GET",
            headers: { Accept: "text/html", "X-Requested-With": "XMLHttpRequest" },
          });
          if (response.ok) {
            const htmlText = await response.text();
            const container = document.createElement("div");
            container.innerHTML = htmlText;
            modalEl = container.querySelector(`#${modalId}`);
            if (modalEl) {
              document.body.appendChild(modalEl);
              return modalEl;
            }
          }
        } catch (error) {
          if (typeof console !== "undefined") {
            console.warn("Failed to load modal template:", error);
          }
        }
      }

      modalEl = document.createElement("div");
      modalEl.id = modalId;
      modalEl.className = "modal";
      modalEl.innerHTML = '<div class="modal-title"></div><h4 class="text-primary"></h4><p class="text-muted"></p><div data-field="property_type"></div><div data-field="bedrooms"></div><div data-field="bathrooms"></div><div class="card bg-success"><div class="card-body"></div></div><div data-field="agent_name"></div><div class="features-list"></div><div data-field="description"></div><button onclick="editProperty()"></button><button onclick="shareProperty()"></button><a data-action="details"></a>';
      document.body.appendChild(modalEl);
      return modalEl;
    }

    showErrorModal(title, message, details) {
      if (!isDomAvailable()) {
        notify(`${title}: ${message}`, "error");
        return;
      }

      let modalEl = document.getElementById("propertyErrorModal");
      if (!modalEl) {
        modalEl = document.createElement("div");
        modalEl.id = "propertyErrorModal";
        modalEl.innerHTML = `
          <div class="error-title"></div>
          <div class="error-message"></div>
          <div class="error-details"><pre></pre></div>
        `;
        document.body.appendChild(modalEl);
      }

      const titleEl = modalEl.querySelector(".error-title");
      const messageEl = modalEl.querySelector(".error-message");
      const detailsWrap = modalEl.querySelector(".error-details");
      const detailsEl = modalEl.querySelector(".error-details pre");

      if (titleEl) titleEl.textContent = title || "Error";
      if (messageEl) messageEl.textContent = message || "Unexpected error";
      if (detailsEl) detailsEl.textContent = details || "";
      if (detailsWrap) detailsWrap.style.display = details ? "block" : "none";

      if (globalObj.bootstrap && typeof globalObj.bootstrap.Modal === "function") {
        const modal = new globalObj.bootstrap.Modal(modalEl);
        modal.show();
      }
    }
  }

  function getManager() {
    if (globalObj.propertyModalManager && typeof globalObj.propertyModalManager.fetchWithRetry === "function") {
      return globalObj.propertyModalManager;
    }
    const manager = new PropertyModalManager();
    globalObj.propertyModalManager = manager;
    return manager;
  }

  function setText(parent, selector, value) {
    if (!parent) return;
    const node = parent.querySelector(selector);
    if (!node) return;
    node.textContent = value;
  }

  function populatePropertyViewModalFallback(property) {
    if (!property) {
      if (typeof console !== "undefined") {
        console.error("Property data is null or undefined");
      }
      return;
    }

    if (!isDomAvailable()) {
      return;
    }

    const modal = document.getElementById("propertyViewModal");
    if (!modal) {
      if (typeof console !== "undefined") {
        console.error("Property view modal not found");
      }
      return;
    }

    const title = property.title || "Untitled Property";
    const address = property.address || "Address not available";
    const type = String(property.property_type || "N/A").toUpperCase();
    const bedrooms = property.bedrooms !== undefined && property.bedrooms !== null ? String(property.bedrooms) : "N/A";
    const bathrooms = property.bathrooms !== undefined && property.bathrooms !== null ? String(property.bathrooms) : "N/A";
    const agentName = property.agent_name || "Unassigned";
    const description = property.description || "No description available";

    setText(modal, ".modal-title", title);
    setText(modal, "h4.text-primary", title);
    setText(modal, "p.text-muted", address);
    setText(modal, '[data-field="property_type"]', type);
    setText(modal, '[data-field="bedrooms"]', bedrooms);
    setText(modal, '[data-field="bathrooms"]', bathrooms);
    setText(modal, '[data-field="agent_name"]', agentName);
    setText(modal, '[data-field="description"]', description);

    const priceCard = modal.querySelector(".card.bg-success .card-body");
    if (priceCard) {
      if (property.listing_type === "rental") {
        const rahn = Number(property.rahn || 0).toLocaleString();
        const ejare = Number(property.ejare || 0).toLocaleString();
        priceCard.innerHTML = `Rental Pricing<br>Rahn: ${rahn}<br>Ejare: ${ejare}`;
      } else {
        const price = Number(property.price || 0).toLocaleString();
        priceCard.innerHTML = `Sale Price<br>${price}`;
      }
    }

    const featuresNode = modal.querySelector(".features-list");
    if (featuresNode) {
      const features = String(property.property_features || "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      featuresNode.innerHTML = features.length ? features.map((feature) => `<span>${feature}</span>`).join(" ") : "<span>No features listed</span>";
    }

    const propertyId = Number(property.id || 0);
    const editBtn = modal.querySelector('button[onclick*="editProperty"]');
    const shareBtn = modal.querySelector('button[onclick*="shareProperty"]');
    const detailsLink = modal.querySelector('a[data-action="details"]');
    if (editBtn && propertyId > 0) editBtn.setAttribute("onclick", `editProperty(${propertyId})`);
    if (shareBtn && propertyId > 0) shareBtn.setAttribute("onclick", `shareProperty(${propertyId})`);
    if (detailsLink && propertyId > 0) detailsLink.setAttribute("href", `/properties/${propertyId}/detail`);
  }

  async function viewPropertyModal(propertyId) {
    if (!propertyId) {
      if (typeof console !== "undefined") {
        console.error("Property ID is required");
      }
      notify("Property ID is required", "error");
      return;
    }

    if (!Number.isInteger(Number(propertyId)) || Number(propertyId) <= 0) {
      notify(`Invalid property ID: ${propertyId}`, "error");
      return;
    }

    const manager = getManager();
    const loadingId = manager.showLoadingIndicator("Loading property details...");

    try {
      const modalEl = await manager.ensureModalTemplate("propertyViewModal");
      const payload = await manager.fetchWithRetry(`/properties/${propertyId}`);
      const property = payload && payload.property ? payload.property : payload;

      if (typeof globalObj.populatePropertyViewModal === "function") {
        globalObj.populatePropertyViewModal(property);
      } else {
        populatePropertyViewModalFallback(property);
      }

      if (modalEl && globalObj.bootstrap && typeof globalObj.bootstrap.Modal === "function") {
        const modal = new globalObj.bootstrap.Modal(modalEl);
        modal.show();
      }
    } catch (error) {
      const errorMessage = error && error.message ? error.message : "Failed to load property details";
      notify(`Failed to load property details: ${errorMessage}`, "error");
      manager.showErrorModal("Property Loading Error", "Failed to load property details", errorMessage);
    } finally {
      manager.hideLoadingIndicator(loadingId);
    }
  }

  if (typeof globalObj.PropertyModalManager === "undefined") {
    globalObj.PropertyModalManager = PropertyModalManager;
  } else if (typeof globalObj.PropertyModalManager !== "function" && typeof globalObj.PropertyModalManagerClass === "undefined") {
    globalObj.PropertyModalManagerClass = PropertyModalManager;
  }

  if (typeof globalObj.populatePropertyViewModal !== "function") {
    globalObj.populatePropertyViewModal = populatePropertyViewModalFallback;
  }

  if (typeof globalObj.viewPropertyModal !== "function") {
    globalObj.viewPropertyModal = viewPropertyModal;
  }

  if (!globalObj.propertyModalManager || typeof globalObj.propertyModalManager.fetchWithRetry !== "function") {
    globalObj.propertyModalManager = new PropertyModalManager();
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      PropertyModalManager,
      viewPropertyModal,
      populatePropertyViewModal: populatePropertyViewModalFallback,
    };
  }
})(typeof window !== "undefined" ? window : globalThis);
