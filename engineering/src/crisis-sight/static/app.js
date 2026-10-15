// 危机慧眼 · 前端交互逻辑
(function () {
  "use strict";

  var analyzeBtn = document.getElementById("analyze-btn");
  var sceneInput = document.getElementById("scene");
  var typeSelect = document.getElementById("disaster-type");
  var statusEl = document.getElementById("status");
  var resultEl = document.getElementById("result");

  // 转义 HTML，防止文本注入
  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // 渲染四段式报告
  function renderReport(report) {
    var el = document.getElementById("report");
    var order = ["情报官", "研判官", "决策官", "审核官"];
    var html = "<p class='report-summary'><strong>" + escapeHtml(report.summary) + "</strong></p>";
    order.forEach(function (name) {
      if (report[name]) {
        html += "<div class='agent-speech'><div class='agent-head'>" + escapeHtml(name) +
          "</div><div class='agent-content'>" + escapeHtml(report[name]) + "</div></div>";
      }
    });
    el.innerHTML = html;
  }

  // 渲染各 Agent 完整发言（含两轮）
  function renderMessages(messages) {
    var el = document.getElementById("messages");
    var html = "";
    messages.forEach(function (msg) {
      html += "<div class='agent-speech'><div class='agent-head'>" + escapeHtml(msg.agent) +
        "<span class='round-tag'>第" + msg.round + "轮</span></div>" +
        "<div class='agent-content'>" + escapeHtml(msg.content) + "</div></div>";
    });
    el.innerHTML = html;
  }

  // 渲染知识库命中条目
  function renderKbHits(kbHits) {
    var el = document.getElementById("kb-hits");
    var entry = kbHits.entry;
    var fields = ["特征", "主要危害", "应对要点", "次生灾害", "监测指标"];
    var html = "<p><strong>命中灾害类型：</strong>" + escapeHtml(kbHits.type) + "</p>";
    fields.forEach(function (key) {
      html += "<div class='kb-item'><strong>" + key + "：</strong>" +
        escapeHtml(entry[key]) + "</div>";
    });
    el.innerHTML = html;
  }

  // 发起推演请求
  function analyze() {
    var scene = sceneInput.value.trim();
    if (!scene) {
      statusEl.textContent = "请先填写灾情描述";
      statusEl.className = "status error";
      return;
    }

    analyzeBtn.disabled = true;
    statusEl.textContent = "多Agent推演中，请稍候……";
    statusEl.className = "status";
    resultEl.classList.add("hidden");

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
        renderReport(data.report);
        renderMessages(data.messages);
        renderKbHits(data.kb_hits);
        statusEl.textContent = "推演完成（模式：" + (data.mode === "llm" ? "LLM" : "演示") + "）";
        statusEl.className = "status";
        resultEl.classList.remove("hidden");
        resultEl.scrollIntoView({ behavior: "smooth" });
      })
      .catch(function (err) {
        statusEl.textContent = "推演失败：" + err.message;
        statusEl.className = "status error";
      })
      .finally(function () {
        analyzeBtn.disabled = false;
      });
  }

  analyzeBtn.addEventListener("click", analyze);
})();