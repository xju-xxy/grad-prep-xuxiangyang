"""
第一个程序：向 GLM 发出一次最简单的对话请求
目的：确认 API Key、网络、SDK 这三样东西全部正常工作。
看懂这个文件，后面 ReAct 的代码就都是在这个基础上加东西。
"""

# os 是 Python 自带的模块，用来读取系统环境变量
import os
# load_dotenv 的作用：把 .env 文件里写的内容加载成"环境变量"
from dotenv import load_dotenv
# ZhipuAI 是智谱官方提供的客户端类，所有请求都通过它来发
from zhipuai import ZhipuAI

# 第一步：读取 .env 文件（执行完这句，.env 里的 Key 就进到环境变量里了）
load_dotenv()

# 第二步：从环境变量里把 Key 取出来
api_key = os.getenv("ZHIPUAI_API_KEY")

# 第三步：用 Key 创建一个客户端。可以把它想象成"一个帮你联系智谱服务器的信使"
client = ZhipuAI(api_key=api_key)

# 第四步：发起一次对话请求
# messages 是一个列表，里面装对话内容。
# 每条消息是一个字典，有两个字段：
#   role（谁说的）：user 表示用户，后面还会见到 assistant（模型）、system（系统设定）
#   content（说了什么）：具体的文字内容
response = client.chat.completions.create(
    model="glm-5.3-flash",          # 指定用哪个模型，对应你免费额度里的 glm-5.3-flash
    messages=[
        {"role": "user", "content": "你好，请用一句话介绍你自己。"},
    ],
)

# 第五步：从返回结果里取出模型的回答
# 返回的数据结构是层层嵌套的，固定取法就是 response.choices[0].message.content
answer = response.choices[0].message.content

# 第六步：把回答打印到屏幕上
print("GLM 的回答：")
print(answer)
