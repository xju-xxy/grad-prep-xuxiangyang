import mujoco

# 这是一个 XML 字符串，描述场景
xml = """
<mujoco model="test">
  <worldbody>
    <geom name="floor" type="plane" size="0 0 0.05"/>
    <body name="ball" pos="0 0 1">
      <joint type="free"/>
      <geom type="sphere" size="0.1" mass="1"/>
    </body>
  </worldbody>
</mujoco>
"""
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)
print(data.body("ball").xpos)
for i in range(500):
    mujoco.mj_step(model, data)
    if i % 100 == 0:
        z = data.body("ball").xpos[2]
        print(f"第{i}步，球的高度：{z:.3f}")