(function () {
  "use strict";

  var root = document.getElementById("dash-activity-chart");
  if (!root) return;

  var chartEl = document.getElementById("bar-chart");
  var subEl = document.getElementById("chart-sub");
  var selectEl = document.getElementById("chart-metric-select");
  var data = {};
  var meta = {};
  var periodSub = "";
  var currentKey = "devis";
  var BAR_MAX_H = 68;

  try {
    var payload = JSON.parse(document.getElementById("activity-chart-data").textContent);
    data = payload.series || {};
    meta = payload.meta || {};
    periodSub = payload.period_sub || "";
  } catch (e) {
    return;
  }

  function renderBarChart(key) {
    key = key || currentKey;
    currentKey = key;
    var values = data[key] || [];
    var m = meta[key] || { label: key, color: "#3b82f6", color_last: "#4fa3c7" };
    if (subEl) {
      subEl.textContent = m.label + " · " + periodSub;
    }
    if (!chartEl) return;

    var valid = values.slice(0, -1).filter(function (v) { return v !== null; });
    var max = Math.max.apply(null, valid.concat([values[values.length - 1] || 0, 1]));

    chartEl.innerHTML = values.map(function (v, i) {
      var isTotal = i === values.length - 1;
      var labels = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "Total"];
      if (v === null) {
        return (
          '<div class="flex flex-1 flex-col items-center gap-1">' +
          '<div class="text-[10px] font-semibold text-transparent">0</div>' +
          '<div class="w-full max-w-[28px] rounded-t bg-gray-200 opacity-30" style="height:4px"></div>' +
          '<div class="text-[9px] text-gray-300">' + labels[i] + "</div></div>"
        );
      }
      var h = Math.max(4, Math.round((v / max) * BAR_MAX_H));
      var fmt = key === "valeur" ? v + "k" : v;
      var valColor = isTotal ? m.color_last : "#4b5563";
      var barBg = isTotal ? m.color_last : m.color;
      var labelCls = isTotal ? "font-bold text-gray-800" : "text-gray-400";
      var barStyle = isTotal ? "box-shadow:0 0 0 2px " + m.color_last : "";
      return (
        '<div class="flex flex-1 flex-col items-center gap-1">' +
        '<div class="text-[10px] font-semibold" style="color:' + valColor + '">' + fmt + "</div>" +
        '<div class="w-full max-w-[28px] rounded-t transition-all" style="height:' + h + "px;background:" + barBg + ";" + barStyle + '"></div>' +
        '<div class="text-[9px] ' + labelCls + '">' + labels[i] + "</div></div>"
      );
    }).join("");
  }

  if (selectEl) {
    selectEl.addEventListener("change", function () {
      renderBarChart(selectEl.value);
    });
  }

  renderBarChart("devis");
})();
