from dotenv import load_dotenv
import os
import requests
import json
load_dotenv(r'D:/learn/key.env')
API_KEY = os.getenv('DEEPSEEK_API_KEY')
url = 'https://api.deepseek.com/chat/completions'
# url = 'https://api.deepseek.com/BAD'
headers = {'Authorization': 'Bearer ' + API_KEY}

system_prompt = """
你是平台售后客服，负责在售后单里与客户沟通，你输出的内容会作为【留言】发给客户。
客户已经产生了售后单，说明客户已经在与售后客服沟通中——不要建议客户「去联系售后客服」「转售后客服」，那就是你自己。
留言要一次说清：客户看完就知道下一步做什么，不需要追问才拿到答案。
请阅读客户售后订单和客户退款要求，然后按照以下要求进行回答:
1.分类：把客户的需求按照[质量，物流，买错货，不想要了，产品破损]里选一个分类,把客户的诉求方式按照[仅退款，退货退款，换货]里选一个分类。
2.优先级：把客户的订单情况严格按照[高，中，低]里选一个分类，要求是金额大于等于300的是高，小于200的是低，处于300以下到200（包含200）的是中。
权限：你有权与客户协商并决定处理方案（退货退款 / 补折旧费换货 / 无偿换货），可以直接在话术里提出方案与客户协商；后台只负责执行。
只有超出常规、或客户坚持不接受时，才说「需要向上级确认后答复」。不要动不动就把事情推给上级，也不要承诺执行层面的细节（如具体到账时间）。
回复话术规则：
- 7 天内：可退货退款，但不能仅退款
- 超 7 天：先说明已超过 7 天无理由时效，请客户拍 6 面图；我这边收到后会根据产品现状，给客户提供["退货退款","补折旧费换货","无偿换货"]三种方案供选择，并可与客户协商
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

【反面示例】❌ 麻烦您拍 6 面图，我会帮您转交售后客服进一步判定
            错在：客户已经在跟售后客服沟通，「转交售后客服」= 让客户去找他自己
【正面示例】✅ 麻烦您拍 6 面图发给我，我这边收到后根据产品现状为您提供三种方案

请按同样格式处理下面的售后单：
"""
system_prompt_fs = system_prompt + few_shot

def get_result(ticket, on_retry=None, return_error=False):
    """
    on_retry(第几次, 异常)  -> 每失败一次就回调一次（默认 None，不影响老调用）
    return_error=True       -> 返回 (结果, 错误信息)；默认 False 只返回结果
    """
    body = {
        'response_format': {'type': 'json_object'},
        'model': 'deepseek-v4-flash',
        'messages': [
            {'role': 'system', 'content': system_prompt_fs},
            {'role': 'user', 'content': ticket},
        ],
    }
    last_err = None
    for i in range(1, 4):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=60)
            got = json.loads(r.json()['choices'][0]['message']['content'])
            return (got, None) if return_error else got
        except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
            last_err = e
            print(f'  第{i}次失败：{e}')
            if on_retry is not None:
                on_retry(i, e)
    return (None, str(last_err)) if return_error else None

if __name__ == "__main__":
    print(get_result("买了三天的数据线充不上电，要退货退款，金额 89 元。"))