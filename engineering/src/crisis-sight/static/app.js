// 危机慧眼 · 前端交互逻辑
(function () {
  "use strict";

  /* ---------------- 元素引用 ---------------- */
  var analyzeBtn = document.getElementById("analyze-btn");
  var btnText = document.getElementById("btn-text");
  var btnSpinner = document.getElementById("btn-spinner");
  var sceneInput = document.getElementById("scene");
  var typeSelect = document.getElementById("disaster-type");
  var templateSelect = document.getElementById("scene-template");
  var statusEl = document.getElementById("status");
  var resultEl = document.getElementById("result");
  var emptyTip = document.getElementById("empty-tip");
  var clockEl = document.getElementById("clock");
  var historyList = document.getElementById("history-list");
  var historyEmpty = document.getElementById("history-empty");

  /* ---------------- 四个角色的元信息 ---------------- */
  var AGENTS = {
    "情报官": {
      cls: "intel",
      role: "灾情要素提取",
      icon: '<path d="M1.2 8.5c1.9-3.2 4.4-4.8 7.3-4.8s5.4 1.6 7.3 4.8c-1.9 3.2-4.4 4.8-7.3 4.8s-5.4-1.6-7.3-4.8z" fill="none"/><circle cx="8.5" cy="8.5" r="2.2"/>'
    },
    "研判官": {
      cls: "judge",
      role: "态势研判与风险定级",
      icon: '<circle cx="7" cy="7" r="4.3"/><path d="M10.3 10.3 L14.2 14.2"/>'
    },
    "决策官": {
      cls: "decide",
      role: "分级行动建议",
      icon: '<path d="M3 2.2v12.6"/><path d="M3.2 3.4h9.6l-2.3 2.8 2.3 2.8H3.2z"/>'
    },
    "审核官": {
      cls: "audit",
      role: "不确定性提示与盲点",
      icon: '<path d="M8.6 1.7l6.2 2.3v4.2c0 3.5-2.6 6.1-6.2 6.9-3.6-.8-6.2-3.4-6.2-6.9V4z"/><path d="M6.1 8.4l1.7 1.7 3.3-3.4"/>'
    }
  };

  function agentIcon(name) {
    var info = AGENTS[name] || AGENTS["情报官"];
    return '<span class="agent-icon"><svg viewBox="0 0 17 17" stroke="#fff" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
      info.icon + "</svg></span>";
  }

  /* ---------------- 顶部时钟 ---------------- */
  function tickClock() {
    var d = new Date();
    function pad(n) { return n < 10 ? "0" + n : "" + n; }
    clockEl.textContent = pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds());
  }
  tickClock();
  setInterval(tickClock, 1000);

  /* ---------------- 公共工具 ---------------- */
  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function setStatus(text, isError) {
    statusEl.hidden = false;
    statusEl.textContent = text;
    statusEl.className = "status" + (isError ? " error" : "");
  }

  /* ---------------- 示例场景下拉 ---------------- */
  var TEMPLATE_TYPES = { "0": "", "1": "地震", "2": "洪涝", "3": "山火", "4": "化工泄漏" };
  templateSelect.addEventListener("change", function () {
    if (!templateSelect.value) return;
    sceneInput.value = templateSelect.value;
    var idx = templateSelect.selectedIndex;
    var type = TEMPLATE_TYPES[idx];
    if (type && type !== "其他") typeSelect.value = type;
    templateSelect.value = ""; // 用完复位，避免误以为选中了场景
    sceneInput.focus();
  });

  /* ---------------- 风险等级徽章 ---------------- */
  function extractRisk(report) {
    var text = (report.summary || "") + " " + (report["研判官"] || "");
    var m = text.match(/风险等级[：:]\s*([高中低])/);
    return m ? m[1] : "";
  }

  function renderRiskBadge(report) {
    var badge = document.getElementById("risk-badge");
    var level = extractRisk(report);
    badge.className = "badge badge-risk";
    if (level === "高") {
      badge.classList.add("high");
      badge.textContent = "风险等级：高";
    } else if (level === "中") {
      badge.classList.add("mid");
      badge.textContent = "风险等级：中";
    } else if (level === "低") {
      badge.classList.add("low");
      badge.textContent = "风险等级：低";
    } else {
      badge.textContent = "风险等级：待评估";
    }
  }

  /* ---------------- 推演流程时间轴 ---------------- */
  function renderTimeline(messages) {
    var el = document.getElementById("timeline");
    var html = "";
    messages.forEach(function (msg) {
      html += '<li data-agent="' + escapeHtml(msg.agent) + '" data-target="msg-' +
        String(msg.round) + '-' + escapeHtml(msg.agent) + '">' +
        '<div class="t-head">' + escapeHtml(msg.agent) +
        '<span class="t-round">第 ' + msg.round + ' 轮</span></div>' +
        '<div class="t-preview">' + escapeHtml(msg.content.split("\n")[0]) + "</div></li>";
    });
    el.innerHTML = html;

    // 点击时间轴节点，滚动到对应的发言卡片
    el.querySelectorAll("li").forEach(function (li) {
      li.addEventListener("click", function () {
        var target = document.getElementById(li.getAttribute("data-target"));
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  /* ---------------- 四段式报告 ---------------- */
  function renderReport(report) {
    var el = document.getElementById("report");
    var order = ["情报官", "研判官", "决策官", "审核官"];
    var html = "";
    order.forEach(function (name) {
      if (!report[name]) return;
      html += '<div class="report-section agent-card tone-' + AGENTS[name].cls + '">' +
        '<div class="agent-head">' + agentIcon(name) +
        '<span class="agent-name">' + name + "</span>" +
        '<span class="agent-role">' + AGENTS[name].role + "</span>" +
        "</div>" +
        '<div class="agent-body">' + escapeHtml(report[name]) + "</div></div>";
    });
    el.innerHTML = html;
  }

  /* ---------------- 各 Agent 两轮完整发言 ---------------- */
  function renderMessages(messages) {
    var el = document.getElementById("messages");
    var rounds = {};
    messages.forEach(function (msg) {
      if (!rounds[msg.agent]) rounds[msg.agent] = [];
      rounds[msg.agent].push(msg);
    });

    var html = "";
    Object.keys(AGENTS).forEach(function (name) {
      var list = rounds[name];
      if (!list || !list.length) return;
      html += '<div class="agent-card tone-' + AGENTS[name].cls + '">' +
        '<div class="agent-head">' + agentIcon(name) +
        '<span class="agent-name">' + name + "</span>" +
        '<span class="agent-role">' + AGENTS[name].role + "</span>" +
        "</div>";
      list.forEach(function (msg) {
        html += '<div class="agent-body" id="msg-' + msg.round + "-" + name + '">' +
          '<span class="t-round">第 ' + msg.round + " 轮</span><br>" +
          escapeHtml(msg.content) + "</div>";
      });
      html += "</div>";
    });
    el.innerHTML = html;
  }

  /* ---------------- 知识库命中条目 ---------------- */
  function renderKbHits(kbHits) {
    var el = document.getElementById("kb-hits");
    var typeEl = document.getElementById("kb-type");
    typeEl.textContent = kbHits.type;
    var entry = kbHits.entry || {};
    var fields = ["特征", "主要危害", "应对要点", "次生灾害", "监测指标"];
    var html = "";
    fields.forEach(function (key) {
      if (!entry[key]) return;
      html += '<div class="kb-item"><strong>' + key + "：</strong><span>" +
        escapeHtml(entry[key]) + "</span></div>";
    });
    el.innerHTML = html;
  }

  /* ---------------- 报告文本（复制/下载共用） ---------------- */
  function buildMarkdown(data) {
    var report = data.report;
    var lines = [];
    lines.push("# " + report.title);
    lines.push("");
    lines.push("> " + report.summary);
    lines.push("");
    var order = ["情报官", "研判官", "决策官", "审核官"];
    order.forEach(function (name) {
      if (!report[name]) return;
      lines.push("## " + name + "（" + AGENTS[name].role + "）");
      lines.push("");
      lines.push(report[name]);
      lines.push("");
    });
    lines.push("## 各 Agent 完整发言记录");
    lines.push("");
    data.messages.forEach(function (msg) {
      lines.push("### " + msg.agent + " · 第 " + msg.round + " 轮");
      lines.push("");
      lines.push(msg.content);
      lines.push("");
    });
    lines.push("## 知识库命中条目（" + data.kb_hits.type + "）");
    lines.push("");
    var entry = data.kb_hits.entry || {};
    var fields = ["特征", "主要危害", "应对要点", "次生灾害", "监测指标"];
    fields.forEach(function (key) {
      if (entry[key]) lines.push("- **" + key + "**：" + entry[key]);
    });
    return lines.join("\n");
  }

  function downloadReport(markdown) {
    var d = new Date();
    function pad(n) { return n < 10 ? "0" + n : "" + n; }
    var filename = "推演报告-" + d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) +
      "-" + pad(d.getHours()) + pad(d.getMinutes()) + ".md";
    var blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }

  function copyReport(markdown, btn) {
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = markdown;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      btn.textContent = "已复制";
      setTimeout(function () { btn.textContent = "复制报告"; }, 1500);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(markdown).then(function () {
        btn.textContent = "已复制";
        setTimeout(function () { btn.textContent = "复制报告"; }, 1500);
      }, fallback);
    } else {
      fallback();
    }
  }

  /* ---------------- 推演记录（localStorage） ---------------- */
  var HISTORY_KEY = "crisis_sight_history";

  function loadHistory() {
    try {
      var raw = localStorage.getItem(HISTORY_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function saveToHistory(snapshot) {
    var list = loadHistory();
    list.unshift(snapshot);
    if (list.length > 5) list.length = 5;
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
    } catch (e) {
      // 存不下就算了，不影响主流程
    }
    renderHistoryList(list);
  }

  function renderHistoryList(list) {
    historyList.innerHTML = "";
    historyEmpty.hidden = list.length > 0;
    list.forEach(function (item, i) {
      var li = document.createElement("li");
      li.innerHTML = '<div class="h-time">' + escapeHtml(item.time) + "</div>" +
        '<div class="h-main">' + escapeHtml(item.type) + " · " + escapeHtml(item.summary) + "</div>" +
        '<div class="h-sub">' + escapeHtml(item.scene) + "</div>";
      li.addEventListener("click", function () {
        showSnapshot(item);
      });
      historyList.appendChild(li);
    });
  }

  function showSnapshot(item) {
    renderResult(item.data);
    emptyTip.classList.add("hidden");
    resultEl.classList.remove("hidden");
    resultEl.scrollIntoView({ behavior: "smooth" });
    setStatus("历史推演回看（" + item.time + "，" + item.type + "）", false);
  }

  /* ---------------- 结果渲染总入口 ---------------- */
  function renderResult(data) {
    document.getElementById("report-title").textContent = data.report.title;
    document.getElementById("report-summary").textContent = data.report.summary;
    renderRiskBadge(data.report);
    var modeBadge = document.getElementById("mode-badge");
    modeBadge.className = "badge badge-mode";
    modeBadge.textContent = data.mode === "llm" ? "LLM 模式" : "演示模式";
    renderTimeline(data.messages);
    renderReport(data.report);
    renderMessages(data.messages);
    renderKbHits(data.kb_hits);
  }

  /* ---------------- 发起推演 ---------------- */
  function analyze() {
    var scene = sceneInput.value.trim();
    if (!scene) {
      setStatus("请先填写灾情描述", true);
      return;
    }

    analyzeBtn.disabled = true;
    btnSpinner.classList.remove("hidden");
    btnText.textContent = "推演中…";
    setStatus("多 Agent 推演进行中，情报官 → 研判官 → 决策官 → 审核官 依次研判……", false);
    resultEl.classList.add("hidden");
    emptyTip.classList.add("hidden");

    fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scene: scene,
        disaster_type: typeSelect.value
      })
    })
      .then(function (resp) {
        if (!resp.ok) {
          return resp.json().then(function (data) {
            throw new Error(data.error || "请求失败");
          });
        }
        return resp.json();
      })
      .then(function (data) {
        renderResult(data);
        setStatus("推演完成（" + (data.mode === "llm" ? "LLM 模式" : "演示模式") + "）— 知识库命中：" + data.kb_hits.type, false);
        resultEl.classList.remove("hidden");
        resultEl.scrollIntoView({ behavior: "smooth" });

        // 存入推演记录：按 summary 里"风险等级：高"这种样式拼一个短摘要
        var d = new Date();
        function pad(n) { return n < 10 ? "0" + n : "" + n; }
        var timeStr = pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
        var risk = extractRisk(data.report);
        saveToHistory({
          time: timeStr,
          type: typeSelect.value,
          scene: scene.length > 18 ? scene.slice(0, 18) + "…" : scene,
          summary: (risk ? "风险" + risk : "已推演"),
          data: data
        });
      })
      .catch(function (err) {
        setStatus("推演失败：" + err.message, true);
      })
      .finally(function () {
        analyzeBtn.disabled = false;
        btnSpinner.classList.add("hidden");
        btnText.textContent = "开始推演";
      });
  }

  analyzeBtn.addEventListener("click", analyze);

  // 清空推演记录
  document.getElementById("clear-history").addEventListener("click", function () {
    try {
      localStorage.removeItem(HISTORY_KEY);
    } catch (e) { /* 忽略 */ }
    renderHistoryList([]);
  });

  // 复制 / 下载按钮
  var lastMarkdown = "";
  document.getElementById("copy-btn").addEventListener("click", function () {
    if (lastMarkdown) copyReport(lastMarkdown, this);
  });
  document.getElementById("download-btn").addEventListener("click", function () {
    if (lastMarkdown) downloadReport(lastMarkdown);
  });

  // 每次推演完把 markdown 存下来，供复制/下载使用
  var originRender = renderResult;
  renderResult = function (data) {
    originRender(data);
    lastMarkdown = buildMarkdown(data);
  };

  // 初始加载历史列表
  renderHistoryList(loadHistory());
})();