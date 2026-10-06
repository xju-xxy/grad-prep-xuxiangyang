"""
第三个程序：单独测试 tools.py 里的两个工具（不经过大模型）。
计算器部分不花钱；搜索部分会用掉 1 次额度。
"""

import tools

print("===== 测试计算器（不花钱）=====")
print("(1200 + 350) * 2 =", tools.calculate("(1200 + 350) * 2"))
print("10 / 4 =", tools.calculate("10 / 4"))
print("15 % 4 =", tools.calculate("15 % 4"))
print("错误算式 1/0 =", tools.calculate("1/0"))
bad = '__import__("os")'
print("恶意输入 =", tools.calculate(bad))

print()
print("===== 测试搜索（花 1 次额度）=====")
out = tools.search("雅安地震是哪一年发生的")
print(out[:500])
