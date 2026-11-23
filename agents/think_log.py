"""ChatOpenAI que salva o raciocínio (campo `reasoning` do vLLM), sem reenviá-lo ao modelo.

O ChatOpenAI descarta esse campo. Aqui ele é copiado para o arquivo do env THINK_LOG
(JSONL, uma linha por chamada ao modelo); nada muda na conversa nem no resultado do run.
"""
import json
import os
import time

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI


class ChatOpenAIThink(ChatOpenAI):
    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)
        try:
            data = response if isinstance(response, dict) else response.model_dump()
            for gen, choice in zip(result.generations, data.get("choices") or []):
                msg = choice.get("message") or {}
                # response_metadata não é reenviado ao modelo
                gen.message.response_metadata["think"] = msg.get("reasoning") or msg.get("reasoning_content")
        except Exception:
            pass  # salvar o raciocínio nunca pode derrubar o run
        return result

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        result = await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
        path = os.environ.get("THINK_LOG")
        if path:
            try:
                msg = result.generations[0].message
                users = [m.content for m in messages if isinstance(m, HumanMessage)]
                line = {"t": time.time(), "query": users[-1] if users else None, "n_msgs": len(messages),
                        "think": msg.response_metadata.pop("think", None), "content": msg.content,
                        "tool_calls": msg.tool_calls, "usage": msg.usage_metadata}
                with open(path, "a") as f:
                    f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
            except Exception:
                pass
        return result
