# 6-挑战 重写6-4
import json

from dotenv import load_dotenv
import os
import requests
import pandas as pd

data = pd.read_excel('工单待处理.xlsx')
print(data)

load_dotenv(r'D:/learn/key.env')  #<-----改成自己的路径
API_KEY = os.getenv('DEEPSEEK_API_KEY')
url = 'https://api.deepseek.com/chat/completions'
headers = {'Authorization':'Bearer '+API_KEY}
fail_counts = 0
system_prompt = """
你是一位资深电商售后专员。
请阅读客户售后订单和客户退款要求，然后按照以下要求进行回答:
1.分类：把客户的需求按照[质量，物流，买错货，不想要了，产品破损]里选一个分类,把客户的诉求方式按照[仅退款，退货退款，换货]里选一个分类。
2.优先级：把客户的订单情况严格按照[高，中，低]里选一个分类，要求是金额大于等于300的是高，小于200的是低，处于300以下到200（包含200）的是中。
回复话术规则：
- 7 天内：可退货退款，但不能仅退款
- 超 7 天：先拒绝退款，告知客户因为超了7天无理由时效因此需要要求客户拍 6 面图，转售后客服判定，售后客服会根据产品现状给客户提供["退货退款","补折旧费换货","无偿换货"]三种模式
- 话术要像直接发给客户的原话话术，可以让我添加到客服宝里进行团队复用，语言要温和，不易与客户产生冲突。

请严格按下面 4 个字段输出一个JSON（字段名照抄）：
{"需求分类": "产品破损", 
"诉求方式": "仅退款", 
"优先级": "高", 
"回复话术": "您好，这边很清楚您的问题，但是本店是小本生意，不支持仅退款的，如果在七天范围内是可以给您退货退款的。"}

如果工单里缺少判断所需的信息（金额、日期等），不要猜测，
请在对应字段直接输出「信息不足」（回复草稿不在信息不足里，如信息不足则让客户提供相应信息）。

"""

few_shot = """
【示例 1】客户说下单点了两次，收到两件，多的那件用不上，要仅退款。金额 210 元，签收后 1 天。
→ {"需求分类":"不想要了","诉求方式":"仅退款","优先级":"中"}

【示例 2】客户说买错颜色装不上，要退货退款。金额 330 元，签收后 1 天。
→ {"需求分类":"买错货","诉求方式":"退货退款","优先级":"高"}

【示例 3】客户说价格一百多块，膜有气泡要退货退款，昨天签收。
→ {"需求分类":"质量","诉求方式":"退货退款","优先级":"低"}

【示例 4】客户说三百块整的壳子有划痕，要仅退款，签收后 2 天。
→ {"需求分类":"质量","诉求方式":"仅退款","优先级":"高"}

【示例 5】客户说两千一百块的行车记录仪会失灵，要换货，签收后 3 天。
→ {"需求分类":"质量","诉求方式":"换货","优先级":"高"}

请按同样格式处理下面的售后单：
"""
system_prompt = system_prompt + few_shot

def get_result(ticket):
    """传入一条售后单文本，返回 4 个字段的字典；失败返回 None"""
    body = {
        'response_format': {'type': 'json_object'},
        'model': 'deepseek-v4-flash',
        'messages':[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': ticket},
        ]
    }
    for i in range(0,3):
        try:
            r=requests.post(url,headers=headers,json=body,timeout=60)
            content = r.json()['choices'][0]['message']['content']
            return json.loads(content)
        except (json.JSONDecodeError,requests.exceptions.RequestException) as e:
            print(f'第{i}次失败，第三次失败将会退出,失败原因:{e}')
    return None

results = []
for gdh,text in zip(data['工单号'],data['工单文本']):
    result = get_result(text)
    if result is not None:
        result['工单号']=gdh
        results.append(result)
        print(f'已处理：{result["工单号"]}')
    else:
        print(f"{gdh}:失败")
        fail_counts += 1
result_Excel = pd.DataFrame(results)
# print(result_Excel)
result_Excel = result_Excel[['工单号','诉求方式','需求分类','优先级','回复话术']]
result_Excel.to_excel("工单分类结果.xlsx", index=False)
print(f'已生成：工单分类结果.xlsx 在D:/learn/code/W6/')

df = pd.read_excel('工单分类结果.xlsx')
print(f"共处理：{len(df)}条")
counts = 0
for i in df['优先级']:
    if i == '高':
        counts += 1
print(f"高优先级：{counts}")
print(f"失败：{fail_counts}")




