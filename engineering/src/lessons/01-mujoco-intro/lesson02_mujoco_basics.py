"""
第 02 课：MuJoCo 入门
=====================

这一课我们学习：
1. 什么是 MuJoCo？
2. 怎么用 MuJoCo 创建一个最简单的仿真场景？
3. 怎么运行仿真并查看数据？

MuJoCo = Multi-Joint dynamics with Contact
是一个物理仿真引擎，专门用于机器人、生物力学等领域的研究。
"""

import mujoco
import numpy as np

# ============================================================
# 1. 创建一个最简单的 MuJoCo 模型
# ============================================================
# MuJoCo 用 XML 格式描述物理场景
# 我们创建一个：地面 + 一个小球 的场景

simple_xml = """
<mujoco model="lesson1_ball">
  <worldbody>
    <!-- 地面 -->
    <geom name="floor" type="plane" size="0 0 0.05" rgba="0.8 0.8 0.8 1"/>

    <!-- 小球：放在地面上方 1 米处 -->
    <body name="ball_body" pos="0 0 1">
      <joint type="free"/>  <!-- 允许自由运动 -->
      <geom name="ball" type="sphere" size="0.1" rgba="0.9 0.2 0.2 1" mass="1"
            contype="1" conaffinity="1"/>
    </body>
  </worldbody>
</mujoco>
"""

def part1_basic_simulation():
    """最基本的仿真：加载模型 + 运行 + 打印"""
    print("=" * 50)
    print("Part 1: 最基本的仿真")
    print("=" * 50)

    # 1. 加载模型
    model = mujoco.MjModel.from_xml_string(simple_xml)
    # 2. 创建数据对象（存储仿真状态）
    data = mujoco.MjData(model)
    # 3. 初始化（计算初始位置等）
    mujoco.mj_forward(model, data)

    print(f"仿真时间步长: {model.opt.timestep} 秒")
    print(f"初始位置: ball 在 z = {data.body('ball_body').xpos[2]:.3f}")

    # 4. 运行仿真（每次 mj_step 推进一步）
    for i in range(500):
        mujoco.mj_step(model, data)

    print(f"500 步后: ball 在 z = {data.body('ball_body').xpos[2]:.3f}")
    print("小球应该掉到地面附近了！（z ≈ 0.1，因为球半径 0.1）")
    print(f"当前速度: {data.body('ball_body').cvel}\n")

    return model, data


def part2_data_structure():
    """了解 MuJoCo data 对象里有什么"""
    print("=" * 50)
    print("Part 2: MuJoCo data 对象详解")
    print("=" * 50)

    model = mujoco.MjModel.from_xml_string(simple_xml)
    data = mujoco.MjData(model)

    # 跑几步让球掉下来
    for _ in range(500):
        mujoco.mj_step(model, data)

    print("【data 里最重要的内容】")
    print(f"  data.time           仿真时间: {data.time:.3f}s")
    print(f"  data.body('ball_body').xpos  位置: {data.body('ball_body').xpos}")
    print(f"  data.body('ball_body').xquat 姿态(四元数): {data.body('ball_body').xquat}")
    print(f"  data.body('ball_body').cvel  速度(线速度+角速度): {data.body('ball_body').cvel}")
    print()
    print("  data.geom('floor').xpos      地面位置: {data.geom('floor').xpos}")
    print(f"  data.geom('ball').xpos       小球位置: {data.geom('ball').xpos}")
    print()
    print("【model 里最重要的内容】")
    print(f"  model.nbody         body 数量: {model.nbody}")
    print(f"  model.ngeom         geom 数量: {model.ngeom}")
    print(f"  model.njnt          joint 数量: {model.njnt}")
    print(f"  model.opt.gravity   重力: {model.opt.gravity}")
    print()
    print("【重力】")
    print(f"  model.opt.gravity = {model.opt.gravity}  (z 方向是 -9.81)")


def part3_modify_simulation():
    """修改仿真参数：关掉重力试试"""
    print("=" * 50)
    print("Part 3: 修改仿真参数")
    print("=" * 50)

    model = mujoco.MjModel.from_xml_string(simple_xml)
    data = mujoco.MjData(model)

    # 关掉重力
    model.opt.gravity[:] = 0  # 三个轴都设为 0

    mujoco.mj_forward(model, data)
    print(f"关掉重力前: ball z = {data.body('ball_body').xpos[2]:.3f}")

    for _ in range(500):
        mujoco.mj_step(model, data)

    print(f"500 步后(无重力): ball z = {data.body('ball_body').xpos[2]:.3f}")
    print("小球没有掉下来！因为重力被关掉了。\n")


def part4_visualization_hint():
    """可视化提示"""
    print("=" * 50)
    print("Part 4: 可视化（需要 GUI）")
    print("=" * 50)
    print("""
如果你的电脑有图形界面，可以这样打开可视化：

    with mujoco.viewer.launch_passive(model, data) as viewer:
        while viewer.is_running():
            mujoco.mj_step(model, data)
            viewer.sync()

按空格暂停，按 R 重置，关掉窗口退出。
    """)


if __name__ == "__main__":
    part1_basic_simulation()
    part2_data_structure()
    part3_modify_simulation()
    part4_visualization_hint()
