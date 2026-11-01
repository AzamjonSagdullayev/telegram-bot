import httpx
from app.config import settings

def system_prompt(business: dict) -> str:
    services = "\n".join(
        f"- {s['name']}: {s['price']} ({s.get('duration', '')})"
        for s in business.get("services", [])
        if s.get("is_active", True)
    )
    faq = "\n".join(f"Q: {x['q']}\nA: {x['a']}" for x in business.get("faq", []))
    return f"""
Sen {business['name']} biznesining virtual Telegram yordamchisisan.
Biznes haqida: {business.get('description', '')}
Xizmatlar:
{services}
FAQ:
{faq}
Qo'shimcha qoidalar: {business.get('system_rules', '')}
Foydalanuvchi qaysi tilda yozsa, shu tilda javob ber. Faqat berilgan ma'lumotlardan foydalan.
Narx, chegirma, manzil yoki bo'sh vaqtni uydirma. Bilmasang operatorga yo'naltir.
Javoblaring qisqa, muloyim va tushunarli bo'lsin. Karta paroli yoki maxfiy ma'lumot so'rama.
""".strip()

async def ask_ai(history: list[dict], business: dict) -> str:
    if not settings.ai_api_key:
        return "AI xizmati sozlanmagan. Iltimos, administratorga murojaat qiling."
    url = settings.ai_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.ai_api_key}"}
    payload = {
        "model": settings.ai_model,
        "temperature": settings.ai_temperature,
        "messages": [{"role": "system", "content": system_prompt(business)}, *history[-12:]]
    }
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return "Hozir texnik muammo yuz berdi. Birozdan keyin urinib ko'ring yoki operatorga yozing."
