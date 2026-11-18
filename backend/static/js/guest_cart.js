/**
 * Panier invité (localStorage) + fusion au compte patient.
 * Variables globales attendues (définies dans base.html) :
 *   MEDCARE_IS_AUTHENTICATED, MEDCARE_IS_PATIENT, MEDCARE_GUEST_CART_MERGE_URL
 */
(function () {
  var KEY = "medcare_guest_cart_v1";

  function getCookie(name) {
    var m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? decodeURIComponent(m[2]) : "";
  }

  function normalizeItems(items) {
    var map = {};
    (items || []).forEach(function (x) {
      var id = parseInt(x.pa_id, 10);
      if (!id) return;
      var q = parseInt(x.qty != null ? x.qty : x.q, 10);
      if (isNaN(q) || q < 1) q = 1;
      if (q > 999) q = 999;
      map[id] = (map[id] || 0) + q;
    });
    return Object.keys(map).map(function (k) {
      return { pa_id: parseInt(k, 10), qty: map[k] };
    });
  }

  function readRaw() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return { v: 1, items: [], insurance_id: null };
      var o = JSON.parse(raw);
      if (!o || typeof o !== "object") return { v: 1, items: [], insurance_id: null };
      var ins = o.insurance_id;
      if (ins != null && ins !== "") {
        ins = parseInt(ins, 10);
        if (isNaN(ins)) ins = null;
      } else ins = null;
      return {
        v: 1,
        items: normalizeItems(o.items || []),
        insurance_id: ins,
      };
    } catch (e) {
      return { v: 1, items: [], insurance_id: null };
    }
  }

  function writeRaw(data) {
    data.items = normalizeItems(data.items);
    localStorage.setItem(KEY, JSON.stringify(data));
  }

  function setAllCartBadges(n) {
    var num = parseInt(n, 10) || 0;
    document.querySelectorAll(".medcare-cart-badge").forEach(function (el) {
      el.textContent = num;
      if (num > 0) el.classList.remove("hidden");
      else el.classList.add("hidden");
    });
    document.querySelectorAll(".medcare-cart-pac-badge").forEach(function (el) {
      el.textContent = num;
      el.classList.toggle("hidden", num === 0);
    });
    document.querySelectorAll(".medcare-cart-pac-mob").forEach(function (el) {
      el.textContent = num;
    });
    document.querySelectorAll(".medcare-cart-pac-mob-wrap").forEach(function (el) {
      el.classList.toggle("hidden", num === 0);
    });
  }

  var MedcareGuestCart = {
    read: readRaw,
    clear: function () {
      localStorage.removeItem(KEY);
      this.updateBadges();
    },
    setInsurance: function (id) {
      var d = readRaw();
      if (id != null && id !== "") {
        id = parseInt(id, 10);
        d.insurance_id = isNaN(id) ? null : id;
      } else d.insurance_id = null;
      writeRaw(d);
    },
    addPa: function (paId, qty) {
      paId = parseInt(paId, 10);
      qty = parseInt(qty, 10) || 1;
      if (!paId) return;
      var d = readRaw();
      var hit = false;
      d.items.forEach(function (row) {
        if (row.pa_id === paId) {
          row.qty = Math.min(999, row.qty + qty);
          hit = true;
        }
      });
      if (!hit) d.items.push({ pa_id: paId, qty: Math.min(999, Math.max(1, qty)) });
      writeRaw(d);
      this.updateBadges();
    },
    addBulkPaIds: function (ids) {
      var self = this;
      (ids || []).forEach(function (id) {
        self.addPa(id, 1);
      });
    },
    removePa: function (paId) {
      paId = parseInt(paId, 10);
      var d = readRaw();
      d.items = d.items.filter(function (x) {
        return x.pa_id !== paId;
      });
      writeRaw(d);
      this.updateBadges();
    },
    setQty: function (paId, qty) {
      paId = parseInt(paId, 10);
      qty = Math.max(1, Math.min(999, parseInt(qty, 10) || 1));
      var d = readRaw();
      d.items.forEach(function (row) {
        if (row.pa_id === paId) row.qty = qty;
      });
      writeRaw(d);
      this.updateBadges();
    },
    clearAll: function () {
      this.clear();
    },
    replaceItems: function (rows) {
      var d = readRaw();
      d.items = normalizeItems(rows);
      writeRaw(d);
      this.updateBadges();
    },
    lineCount: function () {
      return readRaw().items.length;
    },
    /** Somme des quantités (cohérent avec le compteur session serveur). */
    totalQty: function () {
      var d = readRaw();
      return d.items.reduce(function (sum, row) {
        var q = parseInt(row.qty, 10);
        if (isNaN(q) || q < 1) q = 1;
        return sum + q;
      }, 0);
    },
    updateBadges: function () {
      if (window.MEDCARE_IS_AUTHENTICATED) return;
      var local = this.totalQty();
      var body = document.body;
      var server = 0;
      if (body && body.hasAttribute("data-medcare-guest-cart-count")) {
        server = parseInt(body.getAttribute("data-medcare-guest-cart-count") || "0", 10) || 0;
      }
      setAllCartBadges(Math.max(server, local));
    },
  };

  window.MedcareGuestCart = MedcareGuestCart;
  window.MedcareSetCartBadges = setAllCartBadges;

  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-guest-cart-add]");
    if (!el) return;
    var id = el.getAttribute("data-guest-cart-add");
    if (!id) return;
    e.preventDefault();
    MedcareGuestCart.addPa(id, 1);
  });

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.MEDCARE_IS_AUTHENTICATED) {
      MedcareGuestCart.updateBadges();
    }
    if (window.MEDCARE_IS_AUTHENTICATED && window.MEDCARE_IS_PATIENT && window.MEDCARE_GUEST_CART_MERGE_URL) {
      var g = readRaw();
      if (!g.items.length) return;
      fetch(window.MEDCARE_GUEST_CART_MERGE_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        credentials: "same-origin",
        body: JSON.stringify({ items: g.items, insurance_id: g.insurance_id }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (j) {
          if (j.ok) {
            localStorage.removeItem(KEY);
            var cnt =
              typeof j.cart_item_count === "number"
                ? j.cart_item_count
                : typeof j.cart_line_count === "number"
                  ? j.cart_line_count
                  : 0;
            if (cnt > 0) setAllCartBadges(cnt);
            else setAllCartBadges(0);
          }
        })
        .catch(function () {});
    }
  });
})();
