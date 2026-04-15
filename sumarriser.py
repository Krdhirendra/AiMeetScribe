import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import textwrap

# Load transcript properly
with open("transcripts/meeting_transcript.txt", "r", encoding="utf-8") as f:
    meeting_transcript = f.read()

load_dotenv()
GROQ_TOKEN = os.getenv("GROQ_TOKEN")
writer_llm = ChatGroq(
    model='openai/gpt-oss-20b',
    api_key=GROQ_TOKEN,
    temperature=0.3,
)

writer_system_prompt = """... (same as yours)"""

def wrap_text(text, width=100):
    return "\n".join(textwrap.fill(line, width=width) for line in text.split("\n"))

def summarise_transcript():
    writer_human_prompt = f"""
    Here is the transcript:
    {meeting_transcript}
    """

    writer_messages = [
        SystemMessage(writer_system_prompt),
        HumanMessage(writer_human_prompt)
    ]

    response = writer_llm.invoke(writer_messages)
    return response.content


final_report = summarise_transcript()
final_report = wrap_text(final_report)

with open("transcripts/meeting_summary.txt", "w", encoding="utf-8") as f:
    f.write(final_report)

print("Summary generated successfully!")