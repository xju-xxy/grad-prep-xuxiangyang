# -*- coding: utf-8 -*-
"""Flask 主程序：首页与灾情分析 API。"""

from flask import Flask, jsonify, request, send_from_directory

import agents
import config

app = Flask(__name__)


@app.route("/")
def index():
    """返回前端首页。"""
    return send_from_directory("static", "index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """接收灾情描述与灾害类型，返回推演结果。"""
    data = request.get_json(silent=True) or {}
    scene = (data.get("scene") or "").strip()
    disaster_type = (data.get("disaster_type") or "地震").strip()

    if not scene:
        return jsonify({"error": "灾情描述不能为空"}), 400

    result = agents.analyze(scene, disaster_type)
    return jsonify(result)


if __name__ == "__main__":
    # 启用 llm 模式时打印提示，方便用户确认
    if config.llm_enabled():
        print("已检测到 DEEPSEEK_API_KEY，进入 LLM 模式")
    else:
        print("未检测到 DEEPSEEK_API_KEY，进入 demo 模式")
    app.run(host="127.0.0.1", port=5000, debug=False)