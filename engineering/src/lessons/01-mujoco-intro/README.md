# 第 02 课：MuJoCo 入门

## 这节课学什么

1. MuJoCo 是什么
2. 怎么创建最简单的仿真场景
3. 怎么运行仿真、读取数据、修改参数

## 运行方式

```bash
conda activate t800
python lessons/01-mujoco-intro/lesson02_mujoco_basics.py
```

## 核心概念

### MuJoCo 是什么

MuJoCo = **Mu**lti-**Jo**int dynamics with **Co**ntact

- 一个**物理仿真引擎**，能精确模拟刚体动力学
- 广泛用于机器人控制、生物力学、强化学习等研究
- 输入：**模型**（XML 描述场景）+ **控制指令**
- 输出：每一帧的**物理状态**（位置、速度、力等）

### MuJoCo 的两个核心对象

| 对象 | 作用 | 类比 |
|------|------|------|
| `MjModel` | 模型（静态信息） | 场景的"图纸" |
| `MjData` | 数据（动态状态） | 场景的"实时快照" |

### 基本三步走

```python
# 1. 加载模型
model = mujoco.MjModel.from_xml_string(xml_string)

# 2. 创建数据对象
data = mujoco.MjData(model)

# 3. 推进一步仿真
mujoco.mj_step(model, data)
```

### MuJoCo XML 基本结构

```xml
<mujoco model="名字">
  <worldbody>                          <!-- 世界根节点 -->
    <geom name="floor" type="plane"/>  <!-- 几何体 -->
    <body name="ball" pos="0 0 1">     <!-- 刚体 body -->
      <joint type="free"/>             <!-- 关节（控制自由度） -->
      <geom type="sphere" size="0.1"/> <!-- body 里的几何体 -->
    </body>
  </worldbody>
</mujoco>
```

### data 对象里有什么

| 字段 | 含义 |
|------|------|
| `data.time` | 当前仿真时间（秒） |
| `data.body('名字').xpos` | body 的世界坐标位置 |
| `data.body('名字').xquat` | body 的姿态（四元数） |
| `data.body('名字').cvel` | body 的速度（线速度+角速度，6维） |
| `data.geom('名字').xpos` | geom 的位置 |
| `data.qpos` | 所有关节位置（一维数组） |
| `data.qvel` | 所有关节速度（一维数组） |

### model 对象里有什么

| 字段 | 含义 |
|------|------|
| `model.nbody` | body 数量 |
| `model.ngeom` | geom 数量 |
| `model.njnt` | joint 数量 |
| `model.opt.gravity` | 重力向量 `[x, y, z]`，默认 `[0, 0, -9.81]` |
| `model.opt.timestep` | 仿真步长（秒） |

## 动手试试

### 练习 1：让小球从 2 米高处掉落

修改 `lesson02_mujoco_basics.py` 里的 XML，把小球的初始 z 坐标改成 2，看看需要多少步落地。

### 练习 2：修改重力

地球重力是 -9.81，月球是 -1.62。试试改成月球重力，小球会怎样？

### 练习 3：让小球有初始速度

在仿真开始前给 `data.qvel` 赋一个初值，让小球往上抛，看看会发生什么。

## 下节课预告

第 03 课：加载 T800 人形机器人！
