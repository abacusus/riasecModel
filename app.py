from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from motor.motor_asyncio import AsyncIOMotorClient

import os, json, time
from dotenv import load_dotenv
import google.generativeai as genai
import traceback


# ---------------- ENV ----------------
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY","AIzaSyC3mGkWBFYb4UVVsPUSnAO7n3H1CnVJnys")
MONGO_URI = os.getenv("MONGO_URI","mongodb+srv://naman:naman@cluster0.wfqx2hc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY missing")

if not MONGO_URI:
    # Use a warning or raise error depending on preference, for now ensuring we don't crash if just testing local logic
    print("WARNING: MONGO_URI missing from env")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ---------------- MONGO ----------------
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["riasec_db"]
profiles_collection = db["profiles"]

# ---------------- APP ----------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to specific origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- RIASEC ----------------
RIASEC_ORDER = ["R","I","A","S","E","C","R","I","A","S","E","C"]

RIASEC_INTENTS = {
    "R": "hands-on work, tools, machines, physical tasks",
    "I": "problem solving, logic, analysis, critical thinking",
    "A": "creativity, imagination, design, expression",
    "S": "helping, teaching, guiding, supporting people",
    "E": "leading, persuading, decision making, business thinking",
    "C": "organizing, planning, working with data and rules"
}

OPTION_SCORES = [3,2,1,0]

class UserProfile(BaseModel):
    name: str
    age: int
    currentStatus: str = Field(..., description="Class or Degree")
    mobile: str
    email: EmailStr

# ---------------- STATE ----------------
questions = []
questions_ready = False

state = {
    "current": 0,
    "scores": {"R":0,"I":0,"A":0,"S":0,"E":0,"C":0}
}

# ---------------- GEMINI ----------------
def generate_all_questions():
    mapping = ""
    for i, r in enumerate(RIASEC_ORDER, start=1):
        mapping += f"{i}. {r}: {RIASEC_INTENTS[r]}\n"

    prompt = f"""
Generate EXACTLY 12 UNIQUE student-life scenario questions with equal weight options.

Each question must follow the assigned intent.

Assigned intents:
{mapping}

Rules:
- Do NOT mention psychology or RIASEC
- Real-life student situations
- Exactly 4 options each
- All questions MUST be different
- Simple English
- RETURN ONLY JSON ARRAY
- Each item must have ONLY: question, options
"""

    response = model.generate_content(prompt)


    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    data = json.loads(raw)

    if not isinstance(data, list) or len(data) != 12:
        raise ValueError("Invalid Gemini response")

    # 🔥 IMPORTANT FIX: inject riasec ourselves
    final_questions = []
    for i, q in enumerate(data):
        final_questions.append({
            "riasec": RIASEC_ORDER[i],
            "question": q["question"],
            "options": q["options"]
        })

    return final_questions


@app.post("/profile")
async def create_profile(profile: UserProfile):
    try:
        # 1️⃣ Confirm request parsing
        print("DEBUG: Received profile object:")
        print(profile)

        # 2️⃣ Convert Pydantic → dict
        try:
            new_profile = profile.model_dump()
            print("DEBUG: model_dump success")
        except Exception as dump_err:
            print("DEBUG: model_dump FAILED")
            traceback.print_exc()
            raise dump_err

        print("DEBUG: Data to insert:", new_profile)

        # 3️⃣ Mongo insert
        try:
            result = await profiles_collection.insert_one(new_profile)
            print("DEBUG: Mongo insert success, ID:", result.inserted_id)
        except Exception as db_err:
            print("DEBUG: Mongo insert FAILED")
            traceback.print_exc()
            raise db_err

        return {
            "ok": True,
            "id": str(result.inserted_id)
        }

    except Exception as e:
        print("🔥 PROFILE CREATE ERROR 🔥")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Profile creation failed: {str(e)}"
        )


# ---------------- ROUTES ----------------



@app.get("/start")
def start_test():
    global questions, questions_ready

    questions_ready = False
    questions = []

    state["current"] = 0
    state["scores"] = {"R":0,"I":0,"A":0,"S":0,"E":0,"C":0}

    try:
        questions = generate_all_questions()
        questions_ready = True
    except Exception as e:
        print("❌ GEMINI FAILED:", e)
        questions_ready = False

    return {"ready": questions_ready}

@app.get("/question")
def get_question():
    if not questions_ready:
        return {"loading": True}

    i = state["current"]

    if i >= len(questions):
        return {"done": True}

    q = questions[i]
    return {
        "riasec": q["riasec"],
        "question": q["question"],
        "options": q["options"],
        "step": i + 1,
        "total": len(questions)
    }

@app.post("/answer")
async def submit_answer(payload: dict):
    state["scores"][payload["riasec"]] += OPTION_SCORES[payload["option"]]
    state["current"] += 1
    return {"ok": True}


@app.get("/result")
def result():
    sorted_scores = sorted(
        state["scores"].items(),
        key=lambda x: x[1],
        reverse=True
    )
    code = "".join([x[0] for x in sorted_scores[:3]])
    return {"code": code, "scores": state["scores"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
