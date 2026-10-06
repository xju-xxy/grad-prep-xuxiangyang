"""第一个测试文件：确认 API key、网络、SDK 都正常。"""

import os

from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

response = client.chat.completions.create(
    model="glm-5.3-flash",
    messages=[{"role": "user", "content": "你好，请用一句话介绍你自己。"}],
)

print("GLM 的回答：")
print(response.choices[0].message.content)