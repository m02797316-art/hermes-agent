import os
import logging
import json
import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from groq import Groq
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO)

GROQ_API_KEY = "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"
TELEGRAM_TOKEN = "7959130159:AAEj2p2EpDul39wYBAxIgmJY0JWjNm8KEhw"
MEMORY_FILE = "memory.json"

client = Groq(api_key=GROQ_API_KEY)

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {"conversations": {}, "skills": [], "facts": []}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def search_web(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
    except:
        return "Keine Suchergebnisse gefunden."

def update_skills(memory, user_input, response):
    if len(user_input) > 100:
        skill = f"[{datetime.datetime.now().strftime('%Y-%m-%d')}] Komplexe Aufgabe: {user_input[:80]}..."
        if skill not in memory["skills"]:
            memory["skills"].append(skill)
            if len(memory["skills"]) > 50:
                memory["skills"].pop(0)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_input = update.message.text
    memory = load_memory()

    if user_id not in memory["conversations"]:
        memory["conversations"][user_id] = []

    search_results = search_web(user_input)
    history = memory["conversations"][user_id][-10:]
    skills_text = "\n".join(memory["skills"][-10:]) if memory["skills"] else "Noch keine Skills gelernt."

    system_prompt = f"""Du bist HERMES, ein hochintelligenter, lernfähiger KI-Agent.
Du antwortest immer auf Deutsch und duzt den User.
Du hast folgende Skills gelernt:
{skills_text}

Aktuelle Web-Suche zu der Anfrage:
{search_results}

Nutze die Web-Suchergebnisse um immer aktuelle Antworten zu geben.
Lerne aus jeder Unterhaltung und werde besser."""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append(msg)
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1000
    )

    reply = response.choices[0].message.content

    memory["conversations"][user_id].append({"role": "user", "content": user_input})
    memory["conversations"][user_id].append({"role": "assistant", "content": reply})

    if len(memory["conversations"][user_id]) > 50:
        memory["conversations"][user_id] = memory["conversations"][user_id][-50:]

    update_skills(memory, user_input, reply)
    save_memory(memory)

    await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
