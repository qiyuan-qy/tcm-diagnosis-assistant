from zhipuai import ZhipuAI
from typing import List, Dict, Optional
from app.core.config import settings
from app.services.rag_service import rag_service

class LLMService:
    """智谱AI服务 - 伤寒论跳跃式问诊"""

    def __init__(self):
        self.client = None
        self.model = settings.ZHIPUAI_MODEL
        self._init_client()

    def _init_client(self):
        if settings.ZHIPUAI_API_KEY:
            try:
                self.client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)
            except Exception as e:
                print(f"智谱AI初始化失败: {e}")
                self.client = None

    def chat_with_rag(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, any]:
        """基于伤寒论的跳跃式问诊"""

        # 获取对话历史，分析已收集的症状
        collected_symptoms = self._extract_symptoms(conversation_history)
        symptom_count = len(collected_symptoms)

        # 检索知识库
        try:
            relevant_docs = rag_service.similarity_search(message, k=5)
        except:
            relevant_docs = []

        # 构建知识库上下文
        if relevant_docs:
            kb_content = "\n".join([doc['content'] for doc in relevant_docs])
        else:
            kb_content = "头痛\n身体痛"

        # 设计跳跃式问诊prompt
        system_prompt = """你是"小艾"，一位温柔专业的中医诊疗助手。你精通《伤寒论》，正在为患者进行问诊。

【核心原则】
1. **只使用知识库内容**：你的所有诊断和建议必须基于提供的知识库（伤寒论相关内容）
2. **白话文交流**：用通俗易懂的大白话和患者沟通，不要用太专业的术语
3. **跳跃式问答**：根据患者的回答，智能判断下一个问题，不需要按固定顺序问
4. **温柔亲切**：语气要温柔，多用"您"、"呢"、"呀"，让患者感觉温暖

【问诊策略】
当前可用的症状：
- 头痛
- 身体痛（包括全身各处疼痛、酸痛）

根据伤寒论的辨证要点，你需要询问：

**第一步：主诉确认**（第一轮对话）
- 患者说哪里不舒服
- 用大白话确认："嗯嗯，您说头痛是吗？具体是哪个地方疼呢？是前额、后脑勺，还是整个头都疼？"

**第二步：收集鉴别症状**（根据已有信息跳跃提问）

如果患者说"头痛"：
- 问发热情况："有没有发热呀？发烧吗？体温大概多少度？"
- 问出汗："出汗吗？是大汗淋漓还是一点点汗？"
- 问恶寒："怕不怕冷？是不是要盖厚被子才觉得暖和？"
- 问身体疼痛："除了头痛，身体其他地方疼吗？比如腰疼、腿疼、关节疼？"

如果患者说"身体痛"：
- 问具体部位："具体哪里疼呢？是全身酸痛，还是某个部位疼？"
- 问头痛："头也疼吗？"
- 问发热："有没有发烧呀？"

**第三步：症状细节**（根据已收集症状深入）
- 如果"发热+头痛"：问"什么时候最难受？是发热的时候头痛加重，还是退烧后舒服点？"
- 如果"怕冷+无汗"：问"口干吗？想喝水吗？"
- 如果"有汗"：问"汗出后舒服点吗？还是还是难受？"

**第四步：做出判断**（通常5-7轮对话后）
当收集到足够症状（至少3-4个症状）时：
1. 基于知识库做出辨证判断
2. 用大白话解释诊断
3. 给出原文引用（如果知识库有）
4. 给出建议方剂（如果知识库有）

【诊断格式】
当准备做诊断时，请按以下格式输出：

📋 **诊断结果**
（用大白话说明是什么证型，比如"太阳病证"、"伤寒表证"等）

📖 **原文依据**
（从知识库中引用相关原文，如果有）

💊 **建议方剂**
（从知识库中提取的方剂，如果有）

💡 **温馨提示**
（生活建议和注意事项）

【语气示例】
- "嗯嗯，好的~"
- "还有哪里不舒服吗？"
- "明白了，那我问您几个问题哈~"
- "您说的这个情况很重要"
- "谢谢您告诉我这些"

【重要提醒】
- 如果知识库中没有相关信息，诚实地说："知识库里暂时没有这方面的内容呢~"
- 不要自己编造诊断和方剂
- 每次回复只问1-2个问题，不要一次问太多
"""

        # 构建对话历史摘要
        history_summary = ""
        if conversation_history and len(conversation_history) > 0:
            for i, item in enumerate(conversation_history[-8:]):
                role = "您" if item.get('role') == 'user' else "小艾"
                content = item.get('content', '')
                history_summary += f"{role}：{content}\n"

        # 判断是否应该做诊断
        should_diagnose = symptom_count >= 4

        # 调用智谱AI
        if self.client:
            try:
                if should_diagnose:
                    instruction = f"""【已收集的症状】
{chr(10).join(f'- {s}' for s in collected_symptoms)}

【当前问题】
{message}

请根据知识库内容和已收集的症状，做出诊断判断。"""
                else:
                    instruction = f"""【知识库内容】
{kb_content}

【已收集的症状】
{chr(10).join(f'- {s}' for s in collected_symptoms) if collected_symptoms else '暂无'}

【对话历史】
{history_summary}

【当前问题】
{message}

请根据知识库内容和对话历史，判断下一步该问什么问题，用大白话询问患者。"""

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": instruction}
                ]

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.8,
                    max_tokens=1200
                )

                ai_response = response.choices[0].message.content

            except Exception as e:
                print(f"智谱AI调用失败: {e}")
                ai_response = "抱歉，我现在无法为您服务，请稍后再试~"
        else:
            ai_response = "系统提示：请先配置智谱AI API Key。"

        # 更新症状列表
        if conversation_history:
            last_user_message = conversation_history[-1].get('content', '')
            if last_user_message and last_user_message not in str(collected_symptoms):
                collected_symptoms.append(last_user_message)

        return {
            'response': ai_response,
            'session_id': session_id or 'session_tcm',
            'need_more_info': not should_diagnose,
            'is_complete': should_diagnose,
            'collected_symptoms': collected_symptoms,
            'sources': [doc.get('metadata', {}).get('filename', '') for doc in relevant_docs[:3]]
        }

    def _extract_symptoms(self, conversation_history: List[Dict]) -> List[str]:
        """从对话历史中提取症状"""
        symptoms = []
        if not conversation_history:
            return symptoms

        for item in conversation_history:
            if item.get('role') == 'user':
                content = item.get('content', '')
                # 简单的症状关键词提取
                symptom_keywords = ['头痛', '身痛', '发热', '怕冷', '恶寒', '无汗', '有汗', '酸痛']
                for keyword in symptom_keywords:
                    if keyword in content:
                        symptoms.append(keyword)
                        break

        return symptoms

llm_service = LLMService()
