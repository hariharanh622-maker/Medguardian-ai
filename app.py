import os
import sqlite3
import traceback
from datetime import datetime
from functools import wraps
from io import BytesIO

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    jsonify
)

from dotenv import load_dotenv


# ============================================================
# GEMINI
# ============================================================

try:
    from google import genai
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "medguardian-development-secret-key"
)

DATABASE = "medguardian.db"

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.1-flash-lite"
)

gemini_client = None


# ============================================================
# GEMINI INITIALIZATION
# ============================================================

if GEMINI_AVAILABLE and GEMINI_API_KEY:

    try:

        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        print("=" * 60)
        print("Gemini API: Connected")
        print("Model:", MODEL_NAME)
        print("=" * 60)

    except Exception as e:

        print("Gemini Client Error:", e)

else:

    print("=" * 60)
    print("WARNING: Gemini API not configured")
    print("Local fallback mode enabled")
    print("=" * 60)


# ============================================================
# DATABASE
# ============================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    cursor = conn.cursor()

    # --------------------------------------------------------
    # PATIENTS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            age INTEGER,

            gender TEXT,

            phone TEXT,

            created_at TEXT NOT NULL

        )
    """)

    # --------------------------------------------------------
    # CONSULTATIONS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consultations (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            patient_id INTEGER,

            question TEXT NOT NULL,

            ai_response TEXT,

            risk_level TEXT,

            specialist TEXT,

            created_at TEXT NOT NULL,

            FOREIGN KEY(patient_id)
            REFERENCES patients(id)

        )
    """)

    # --------------------------------------------------------
    # MEDICINE REMINDERS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicine_reminders (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            patient_id INTEGER,

            medicine_name TEXT NOT NULL,

            reminder_time TEXT,

            created_at TEXT NOT NULL,

            FOREIGN KEY(patient_id)
            REFERENCES patients(id)

        )
    """)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return decorated_function


# ============================================================
# LOCAL TRIAGE
# ============================================================

def local_triage(symptoms):

    text = (symptoms or "").lower().strip()

    if not text:
        return {
            "risk": "MEDIUM",
            "specialist": "General Physician",
            "response": """
### Summary
Please share your main symptoms, how long they started, and if you have any fever, breathing issues, or severe pain.

### Possible Causes
Many different conditions can cause symptoms, including infections, inflammation, dehydration, stress, or common seasonal illnesses.

### What You Can Do
Rest, drink fluids, and avoid heavy activity while you are evaluating the problem.

### When To See A Doctor
See a doctor if symptoms last more than a few days, become worse, or are affecting your daily life.

### Emergency Warning Signs
Difficulty breathing, chest pain, fainting, confusion, severe bleeding, or sudden weakness should be treated urgently.

### Recommended Next Step
Have a clinical review soon and seek urgent care if symptoms worsen quickly.

Risk Level: MEDIUM
Recommended Specialist: General Physician
"""
        }

    emergency_keywords = [
        "difficulty breathing",
        "can't breathe",
        "cannot breathe",
        "severe chest pain",
        "chest pain",
        "unconscious",
        "fainted",
        "seizure",
        "severe bleeding",
        "stroke",
        "paralysis",
        "suicide",
        "blue lips",
        "trouble breathing"
    ]

    high_keywords = [
        "very high fever",
        "blood vomiting",
        "vomiting blood",
        "severe headache",
        "confusion",
        "persistent vomiting",
        "severe dehydration",
        "unable to breathe",
        "shortness of breath",
        "difficulty swallowing",
        "severe abdominal pain",
        "black stool"
    ]

    respiratory_keywords = [
        "fever", "cough", "cold", "sore throat", "throat pain",
        "runny nose", "body pain", "fatigue", "weakness", "headache",
        "chest tightness", "wheezing"
    ]

    stomach_keywords = [
        "stomach pain", "nausea", "vomiting", "diarrhea", "indigestion",
        "bloating", "acidity", "food poisoning", "loose motion"
    ]

    headache_keywords = [
        "headache", "migraine", "dizziness", "sinus", "eye pain"
    ]

    body_keywords = [
        "fatigue", "weakness", "body pain", "low energy", "sleep deprivation",
        "stress", "joint pain", "muscle pain"
    ]

    if any(word in text for word in emergency_keywords):
        return {
            "risk": "HIGH",
            "specialist": "Emergency Department",
            "response": """
### Summary
This pattern can be a medical emergency and should not be managed by home remedies alone. Severe symptoms may signal a serious infection, breathing problem, heart issue, or another urgent condition.

### Possible Causes
Possible causes include severe infection, breathing difficulty, dehydration, heart-related problems, or other dangerous conditions. This is not a confirmed diagnosis.

### What You Can Do
Stop activity, sit upright if breathing is difficult, keep the person calm, and get urgent medical help immediately. Do not wait for symptoms to get worse.

### When To See A Doctor
Go to the nearest emergency service now. Do not delay evaluation if symptoms are ongoing or worsening.

### Emergency Warning Signs
Severe breathing difficulty, chest pain, fainting, confusion, seizure, severe bleeding, sudden weakness, or stroke-like symptoms need emergency care.

### Recommended Next Step
Call emergency services or go to the nearest emergency department immediately.

Risk Level: HIGH
Recommended Specialist: Emergency Department
"""
        }

    if any(word in text for word in high_keywords):
        return {
            "risk": "HIGH",
            "specialist": "General Physician",
            "response": """
### Summary
Your symptoms may point to a more serious infection or inflammation that needs a medical review soon. A clinician needs to assess whether this is a viral illness, dehydration, infection, or another urgent condition.

### Possible Causes
Common possibilities include severe viral infection, dehydration, inflammation, or a more serious underlying problem. The exact cause cannot be confirmed from symptoms alone.

### What You Can Do
Rest, sip water regularly, avoid heavy activity, and monitor your symptoms carefully. Do not ignore worsening weakness, vomiting, or fever.

### When To See A Doctor
Book a medical review promptly, especially if symptoms continue for more than 24–48 hours, worsen, or cause dehydration.

### Emergency Warning Signs
Severe breathing trouble, chest pain, confusion, repeated vomiting, fainting, or worsening weakness need urgent assessment.

### Recommended Next Step
See a doctor today or seek urgent care if the condition is worsening.

Risk Level: HIGH
Recommended Specialist: General Physician
"""
        }

    if any(word in text for word in stomach_keywords):
        return {
            "risk": "MEDIUM",
            "specialist": "General Physician",
            "response": """
### Summary
This pattern often fits a stomach infection, indigestion, food-related irritation, or mild inflammation of the gut. It is common and often manageable at home, but it can become serious if dehydration or persistent pain develops.

### Possible Causes
Possible causes include food poisoning, gastroenteritis, stomach flu, acidity, indigestion, or a temporary inflammatory illness. The exact cause depends on the pattern of pain, vomiting, fever, and bowel changes.

### What You Can Do
Rest, drink fluids such as oral rehydration solution or water, avoid very oily or spicy food, and eat bland foods like rice, toast, bananas, or soup if tolerated. If fever or severe pain is present, do not assume it is simple indigestion.

### When To See A Doctor
See a doctor if the pain is strong or constant, there is blood in vomit or stool, dehydration is developing, or symptoms keep returning.

### Emergency Warning Signs
Severe abdominal pain, persistent vomiting, blood in stool or vomit, fainting, or severe weakness need urgent evaluation.

### Recommended Next Step
Try home hydration and bland food first, but contact a doctor if symptoms continue for more than 24–48 hours or become worse.

Risk Level: MEDIUM
Recommended Specialist: General Physician
"""
        }

    if any(word in text for word in respiratory_keywords):
        return {
            "risk": "MEDIUM",
            "specialist": "General Physician",
            "response": """
### Summary
This combination of symptoms often matches a common viral illness or mild inflammatory infection such as a cold, throat infection, flu-like illness, or sinus irritation. It is not a confirmed diagnosis, but the pattern is common and usually manageable with rest and hydration.

### Possible Causes
Common causes include viral upper respiratory infection, sore throat infection, sinus inflammation, seasonal allergies, fever, or mild dehydration. The exact cause depends on duration, fever pattern, and whether there is breathing difficulty or severe pain.

### What You Can Do
Rest adequately, drink plenty of water, avoid strain, and keep your environment warm and humid if needed. For mild fever or body ache, a clinician may suggest simple symptom-relief measures if they are appropriate for your age and medical history. Do not self-medicate heavily without checking safe use.

### When To See A Doctor
See a doctor if the fever lasts more than a few days, the cough is worsening, breathing is affected, or you feel much weaker than usual.

### Emergency Warning Signs
Trouble breathing, chest pressure, blue lips, confusion, or severe weakness need urgent medical attention.

### Recommended Next Step
Continue rest and hydration, and arrange a medical check if the illness is lasting longer than expected or getting worse.

Risk Level: MEDIUM
Recommended Specialist: General Physician
"""
        }

    if any(word in text for word in headache_keywords):
        return {
            "risk": "MEDIUM",
            "specialist": "Neurologist",
            "response": """
### Summary
Headache or dizziness can be caused by stress, dehydration, poor sleep, sinus irritation, migraine, or an infection. It may also be related to fever or other conditions, so the pattern matters.

### Possible Causes
Possible causes include dehydration, tension or stress, migraine, sinus inflammation, viral infection, or a less common but serious issue if the headache is sudden or severe.

### What You Can Do
Rest in a quiet environment, drink water, reduce screen time, and avoid overexertion. If pain is mild, simple rest and hydration often help, but do not assume every headache is harmless.

### When To See A Doctor
Seek medical review if the headache is frequent, severe, sudden, or associated with fever, vomiting, or neurological symptoms.

### Emergency Warning Signs
Sudden severe headache, weakness, confusion, vision changes, loss of balance, or seizure-like symptoms need urgent care.

### Recommended Next Step
Monitor symptoms and contact a doctor if the headache keeps recurring or becomes worse.

Risk Level: MEDIUM
Recommended Specialist: Neurologist
"""
        }

    if any(word in text for word in body_keywords):
        return {
            "risk": "LOW",
            "specialist": "General Physician",
            "response": """
### Summary
This pattern may be due to poor sleep, stress, overwork, low fluids, mild infection, or general fatigue. It is often not dangerous, but persistent weakness should be checked.

### Possible Causes
Possible causes include low sleep, dehydration, stress, mild viral illness, anemia, or low energy after exertion. The exact cause depends on the duration and whether there are other symptoms like fever, weight change, or shortness of breath.

### What You Can Do
Get adequate rest, hydration, and balanced meals, and reduce strain on the body. Light activity and a consistent sleep routine often help.

### When To See A Doctor
See a doctor if fatigue lasts more than 1–2 weeks, is worsening, or comes with fever, weight loss, chest symptoms, or a new pattern.

### Emergency Warning Signs
Severe weakness, breathing trouble, chest pain, fainting, or confusion need urgent assessment.

### Recommended Next Step
Use a follow-up health review if the fatigue continues or then becomes more severe.

Risk Level: LOW
Recommended Specialist: General Physician
"""
        }

    return {
        "risk": "MEDIUM",
        "specialist": "General Physician",
        "response": """
### Summary
The symptoms you described are common and can happen with a range of mild to moderate health issues. They are not enough by themselves to confirm a diagnosis.

### Possible Causes
Possible causes include infection, inflammation, dehydration, stress, allergies, or seasonal illness. The exact cause depends on symptom pattern, how long it lasts, and whether other warning signs appear.

### What You Can Do
Rest, stay hydrated, avoid heavy work, and monitor symptom changes. Use only safe, appropriate symptom relief if it is suitable for your medical history.

### When To See A Doctor
Book a consultation if the problem lasts more than a few days, is worsening, or begins to interfere with normal activity.

### Emergency Warning Signs
Breathing difficulty, chest pain, severe weakness, confusion, fainting, seizures, or severe bleeding need urgent evaluation.

### Recommended Next Step
Continue monitoring and arrange a medical review if symptoms persist, worsen, or new symptoms appear.

Risk Level: MEDIUM
Recommended Specialist: General Physician
"""
    }


# ============================================================
# GEMINI AI
# ============================================================

def get_ai_analysis(symptoms, language="auto"):

    fallback = local_triage(symptoms)

    if not gemini_client:

        return fallback

    symptom_text = (symptoms or "").lower()
    emergency_keywords = [
        "difficulty breathing",
        "can't breathe",
        "cannot breathe",
        "severe chest pain",
        "chest pain",
        "unconscious",
        "fainted",
        "seizure",
        "severe bleeding",
        "stroke",
        "paralysis",
        "blue lips",
        "trouble breathing",
        "shortness of breath"
    ]
    high_keywords = [
        "very high fever",
        "vomiting blood",
        "blood vomiting",
        "persistent vomiting",
        "severe dehydration",
        "severe headache",
        "confusion",
        "black stool"
    ]
    emergency_present = any(word in symptom_text for word in emergency_keywords)
    high_signal_present = any(word in symptom_text for word in high_keywords)

    if language == "ta-IN":

        language_instruction = """
Respond primarily in Tamil.
Use simple Tamil with necessary medical English
terms in brackets.
"""

    elif language == "en-IN":

        language_instruction = """
Respond in simple and clear English.
"""

    else:

        language_instruction = """
Detect the user's language.
If Tamil is used, respond primarily in Tamil.
If English is used, respond in English.
"""

    system_instruction = f"""

You are MedGuardian AI,
an educational healthcare assistant.

IMPORTANT:

1. Never claim a confirmed diagnosis.
2. Never prescribe medicine or dosages.
3. Never recommend a specific tablet, injection, or regimen.
4. Explain common likely causes in a practical and realistic way.
5. Give clear home-care guidance that is safe and reasonable.
6. Explain whether the person should rest, hydrate, monitor, or seek medical help.
7. Explain when professional medical care is needed.
8. Clearly identify emergency warning signs.
9. Keep the answer simple, realistic, and easy to understand.
10. Never pretend to be a doctor.
11. If there are no red-flag or dangerous symptoms, do not recommend emergency department care.
12. If symptoms are mild or common illness patterns, focus on rest, fluids, monitoring, and doctor review only if worsening.

{language_instruction}

Return these sections with detailed, real-world guidance:

### Summary

### Possible Causes

### What You Can Do

### When To See A Doctor

### Emergency Warning Signs

### Recommended Next Step

At the end write:

Risk Level: LOW / MEDIUM / HIGH

Recommended Specialist: specialist name

"""

    prompt = f"""

PATIENT HEALTH INFORMATION

{symptoms}

Analyze this information safely.

Do not provide a confirmed diagnosis.

Do not prescribe medicine or dosage.

"""

    try:

        response = gemini_client.models.generate_content(

            model=MODEL_NAME,

            contents=prompt,

            config={
                "system_instruction":
                    system_instruction,
                "max_output_tokens":
                    1800
            }

        )

        text = getattr(
            response,
            "text",
            None
        )

        if not text:

            return fallback

        upper_text = text.upper()

        risk = fallback["risk"]
        specialist = fallback["specialist"]

        if "RISK LEVEL: HIGH" in upper_text:
            risk = "HIGH"
        elif "RISK LEVEL: LOW" in upper_text:
            risk = "LOW"

        if not emergency_present and not high_signal_present:
            risk = fallback["risk"]
            specialist = fallback["specialist"]

        if emergency_present and "EMERGENCY" in upper_text:
            risk = "HIGH"
            specialist = "Emergency Department"
        elif emergency_present and "RISK LEVEL: HIGH" not in upper_text:
            risk = "HIGH"
            specialist = "Emergency Department"

        if high_signal_present and "RISK LEVEL: HIGH" in upper_text:
            risk = "HIGH"

        specialist_map = [
            ("EMERGENCY DEPARTMENT", "Emergency Department"),
            ("CARDIOLOGIST", "Cardiologist"),
            ("DERMATOLOGIST", "Dermatologist"),
            ("NEUROLOGIST", "Neurologist"),
            ("ORTHOPEDIST", "Orthopedist"),
            ("ENT SPECIALIST", "ENT Specialist"),
            ("PULMONOLOGIST", "Pulmonologist"),
            ("PEDIATRICIAN", "Pediatrician"),
            ("GYNECOLOGIST", "Gynecologist")
        ]

        for keyword, name in specialist_map:
            if keyword in upper_text:
                specialist = name
                break

        if not emergency_present and not high_signal_present and specialist == "Emergency Department":
            specialist = fallback["specialist"]

        return {
            "risk": risk,
            "specialist": specialist,
            "response": text
        }

    except Exception as e:

        print("=" * 60)
        print("GEMINI ERROR")
        print(e)
        print("=" * 60)

        traceback.print_exc()

        return fallback


# ============================================================
# SAVE CONSULTATION
# ============================================================

def save_consultation(

    patient_id,
    question,
    ai_response,
    risk_level,
    specialist

):

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(

        """
        INSERT INTO consultations
        (
            patient_id,
            question,
            ai_response,
            risk_level,
            specialist,
            created_at
        )

        VALUES (?, ?, ?, ?, ?, ?)
        """,

        (

            patient_id,
            question,
            ai_response,
            risk_level,
            specialist,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        )

    )

    consultation_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return consultation_id


# ============================================================
# HOME
# ============================================================

@app.route("/")
@login_required
def home():

    conn = get_db()

    patient = conn.execute(

        """
        SELECT *
        FROM patients
        WHERE id = ?
        """,

        (
            session["user_id"],
        )

    ).fetchone()

    consultations = conn.execute(

        """
        SELECT *
        FROM consultations
        WHERE patient_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,

        (
            session["user_id"],
        )

    ).fetchall()

    reminders = conn.execute(

        """
        SELECT *
        FROM medicine_reminders
        WHERE patient_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,

        (
            session["user_id"],
        )

    ).fetchall()

    conn.close()

    return render_template(

        "index.html",

        patient=patient,

        consultations=consultations,

        reminders=reminders,

        user_name=session.get(
            "user_name",
            "Patient"
        )

    )
# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        ).strip()

        age = request.form.get(
            "age",
            ""
        )

        gender = request.form.get(
            "gender",
            ""
        )

        if not name or not email or not password:

            return render_template(
                "register.html",
                error="All fields are required."
            )

        conn = get_db()

        existing = conn.execute(
            """
            SELECT *
            FROM patients
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing:

            conn.close()

            return render_template(
                "register.html",
                error="Email already exists."
            )

        conn.execute(
            """
            INSERT INTO patients
            (
                name,
                email,
                password,
                age,
                gender,
                phone,
                created_at
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                password,
                age,
                gender,
                "",
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        conn.commit()
        conn.close()

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )

# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            return render_template(

                "login.html",

                error=
                "Please enter email and password."

            )

        conn = get_db()

        patient = conn.execute(

            """
            SELECT *
            FROM patients
            WHERE email = ?
            """,

            (
                email,
            )

        ).fetchone()

        conn.close()

        if patient and patient["password"] == password:

            session["user_id"] = patient["id"]

            session["user_name"] = patient["name"]

            session["user_email"] = patient["email"]

            return redirect(
                url_for("home")
            )

        # ----------------------------------------------------
        # DEMO ACCOUNT
        # ----------------------------------------------------

        if (
            email == "test@gmail.com"
            and password == "123456"
        ):

            conn = get_db()

            try:

                conn.execute(

                    """
                    INSERT OR IGNORE INTO patients
                    (
                        name,
                        email,
                        password,
                        age,
                        gender,
                        phone,
                        created_at
                    )

                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,

                    (

                        "Test Patient",
                        email,
                        password,
                        21,
                        "Other",
                        "",
                        datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                    )

                )

                conn.commit()

                patient = conn.execute(

                    """
                    SELECT *
                    FROM patients
                    WHERE email = ?
                    """,

                    (
                        email,
                    )

                ).fetchone()

                conn.close()

                if patient:

                    session["user_id"] = patient["id"]

                    session["user_name"] = patient["name"]

                    session["user_email"] = patient["email"]

                    return redirect(
                        url_for("home")
                    )

            except Exception as e:

                print(
                    "Demo account error:",
                    e
                )

                try:
                    conn.close()
                except:
                    pass

        return render_template(

            "login.html",

            error=
            "Invalid email or password."

        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# ASK AI
# ============================================================

@app.route(
    "/ask-ai",
    methods=["POST"]
)
@login_required
def ask_ai():

    try:

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({

                "success":
                    False,

                "error":
                    "No patient data received."

            }), 400

        age = str(
            data.get("age", "")
        ).strip()

        gender = str(
            data.get("gender", "")
        ).strip()

        temperature = str(
            data.get("temperature", "")
        ).strip()

        duration = str(
            data.get("duration", "")
        ).strip()

        severity = str(
            data.get("severity", "")
        ).strip()

        main_symptom = str(
            data.get("main_symptom", "")
        ).strip()

        symptoms = str(
            data.get("symptoms", "")
        ).strip()

        language = str(
            data.get("language", "auto")
        ).strip()

        if not symptoms:

            return jsonify({

                "success":
                    False,

                "error":
                    "Please enter your symptoms."

            }), 400

        structured_prompt = f"""

PATIENT INFORMATION

Age:
{age or "Not provided"}

Gender:
{gender or "Not provided"}

Temperature:
{temperature + " °F" if temperature else "Not provided"}

Duration:
{duration or "Not provided"}

Severity:
{severity or "Not provided"}

Main Symptom:
{main_symptom or "Not provided"}

Additional Symptoms:
{symptoms}

"""

        result = get_ai_analysis(
            structured_prompt,
            language
        )

        risk = result.get(
            "risk",
            "MEDIUM"
        )

        specialist = result.get(
            "specialist",
            "General Physician"
        )

        response_text = result.get(
            "response",
            ""
        )

        if risk == "LOW":

            risk_message = (
                "Low immediate risk based on the "
                "information provided. Continue monitoring."
            )

        elif risk == "HIGH":

            risk_message = (
                "Prompt medical evaluation may be "
                "appropriate, especially if symptoms "
                "are severe or worsening."
            )

        else:

            risk_message = (
                "Monitor your symptoms and consider "
                "professional medical evaluation if "
                "they persist or worsen."
            )

        consultation_id = save_consultation(

            session["user_id"],

            symptoms,

            response_text,

            risk,

            specialist

        )

        session["last_question"] = symptoms

        session["last_response"] = response_text

        session["last_risk"] = risk

        session["last_specialist"] = specialist

        session["last_date"] = (
            datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            )
        )

        session.modified = True

        return jsonify({

            "success":
                True,

            "result":
                response_text,

            "risk":
                risk,

            "severity":
                risk,

            "risk_message":
                risk_message,

            "specialist":
                specialist,

            "consultation_id":
                consultation_id,

            "date":
                session["last_date"]

        })

    except Exception as e:

        print("=" * 60)
        print("ASK AI ERROR:", e)
        print("=" * 60)

        traceback.print_exc()

        return jsonify({

            "success":
                False,

            "error":
                "Server error: " + str(e)

        }), 500


# ============================================================
# PATIENT PROFILE API
# ============================================================

@app.route("/api/profile")
@login_required
def profile_api():

    conn = get_db()

    patient = conn.execute(

        """
        SELECT id, name, email, age,
               gender, phone, created_at
        FROM patients
        WHERE id = ?
        """,

        (
            session["user_id"],
        )

    ).fetchone()

    conn.close()

    if not patient:

        return jsonify({
            "success": False,
            "error": "Patient not found."
        }), 404

    return jsonify({

        "success": True,

        "patient": dict(patient)

    })


# ============================================================
# CONSULTATION HISTORY API
# ============================================================

@app.route("/api/history")
@login_required
def history_api():

    conn = get_db()

    rows = conn.execute(

        """
        SELECT
            id,
            question,
            ai_response,
            risk_level,
            specialist,
            created_at
        FROM consultations
        WHERE patient_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,

        (
            session["user_id"],
        )

    ).fetchall()

    conn.close()

    return jsonify({

        "success":
            True,

        "history":
            [dict(row) for row in rows]

    })


# ============================================================
# BMI
# ============================================================

@app.route(
    "/api/bmi",
    methods=["POST"]
)
@login_required
def calculate_bmi():

    try:

        data = request.get_json(
            silent=True
        )

        weight = float(
            data.get("weight", 0)
        )

        height = float(
            data.get("height", 0)
        )

        if weight <= 0 or height <= 0:

            return jsonify({

                "success":
                    False,

                "error":
                    "Enter valid weight and height."

            }), 400

        height_m = height / 100

        bmi = weight / (
            height_m * height_m
        )

        bmi = round(
            bmi,
            1
        )

        if bmi < 18.5:

            category = "Underweight"

        elif bmi < 25:

            category = "Normal"

        elif bmi < 30:

            category = "Overweight"

        else:

            category = "Obesity"

        return jsonify({

            "success":
                True,

            "bmi":
                bmi,

            "category":
                category

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 400


# ============================================================
# MEDICINE REMINDER
# ============================================================

@app.route(
    "/medicine-reminder",
    methods=["POST"]
)
@login_required
def medicine_reminder():

    try:

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({
                "success": False,
                "error": "No data received."
            }), 400

        medicine_name = str(
            data.get(
                "medicine_name",
                ""
            )
        ).strip()

        reminder_time = str(
            data.get(
                "reminder_time",
                ""
            )
        ).strip()

        if not medicine_name:

            return jsonify({

                "success":
                    False,

                "error":
                    "Medicine name is required."

            }), 400

        conn = get_db()

        conn.execute(

            """
            INSERT INTO medicine_reminders
            (
                patient_id,
                medicine_name,
                reminder_time,
                created_at
            )

            VALUES (?, ?, ?, ?)
            """,

            (

                session["user_id"],

                medicine_name,

                reminder_time,

                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            )

        )

        conn.commit()
        conn.close()

        return jsonify({

            "success":
                True,

            "message":
                "Reminder saved successfully."

        })

    except Exception as e:

        print(
            "Reminder error:",
            e
        )

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ============================================================
# DOWNLOAD HEALTH REPORT
# ============================================================

@app.route("/download-report")
@login_required
def download_report():

    question = session.get(
        "last_question",
        "No consultation available"
    )

    response = session.get(
        "last_response",
        "No AI response available"
    )

    risk = session.get(
        "last_risk",
        "MEDIUM"
    )

    specialist = session.get(
        "last_specialist",
        "General Physician"
    )

    date = session.get(
        "last_date",
        datetime.now().strftime(
            "%d-%m-%Y %H:%M"
        )
    )

    report_text = f"""

====================================================
                 MEDGUARDIAN AI
              HEALTH CONSULTATION
====================================================

Patient:
{session.get("user_name", "Patient")}

Date:
{date}

====================================================
SYMPTOMS
====================================================

{question}

====================================================
AI ANALYSIS
====================================================

{response}

====================================================
RISK LEVEL
====================================================

{risk}

====================================================
RECOMMENDED SPECIALIST
====================================================

{specialist}

====================================================
MEDICAL DISCLAIMER
====================================================

This report is generated by an AI healthcare
assistant for educational purposes only.

It is NOT a confirmed medical diagnosis.

It does NOT replace professional medical advice.

If symptoms are severe or worsening, seek
appropriate medical care.

====================================================

MedGuardian AI © 2026

"""

    try:

        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        pdf_buffer = BytesIO()

        pdf = canvas.Canvas(
            pdf_buffer,
            pagesize=A4
        )

        width, height = A4

        x = 45

        y = height - 50

        pdf.setFont(
            "Helvetica-Bold",
            16
        )

        pdf.drawString(
            x,
            y,
            "MedGuardian AI - Health Report"
        )

        y -= 30

        pdf.setFont(
            "Helvetica",
            10
        )

        for line in report_text.splitlines():

            if y < 45:

                pdf.showPage()

                pdf.setFont(
                    "Helvetica",
                    10
                )

                y = height - 50

            safe_line = (
                line.encode(
                    "ascii",
                    "ignore"
                ).decode()
            )

            pdf.drawString(
                x,
                y,
                safe_line[:110]
            )

            y -= 14

        pdf.save()

        pdf_buffer.seek(0)

        return send_file(

            pdf_buffer,

            mimetype=
                "application/pdf",

            as_attachment=True,

            download_name=
                "MedGuardian_Health_Report.pdf"

        )

    except Exception as e:

        print(
            "PDF error:",
            e
        )

        text_buffer = BytesIO(
            report_text.encode(
                "utf-8"
            )
        )

        text_buffer.seek(0)

        return send_file(

            text_buffer,

            mimetype=
                "text/plain",

            as_attachment=True,

            download_name=
                "MedGuardian_Health_Report.txt"

        )


# ============================================================
# HEALTH CHECK + STATIC PAGES
# ============================================================

@app.route("/privacy")
def privacy():

    return render_template("privacy.html")


@app.route("/terms")
def terms():

    return render_template("terms.html")


@app.route("/health")
def health():

    return jsonify({

        "status":
            "running",

        "application":
            "MedGuardian AI",

        "gemini":
            bool(gemini_client),

        "model":
            MODEL_NAME,

        "time":
            datetime.now().isoformat()

    })


# ============================================================
# 404
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return jsonify({

        "success":
            False,

        "error":
            "Page not found."

    }), 404


# ============================================================
# 405
# ============================================================

@app.errorhandler(405)
def method_not_allowed(error):

    return jsonify({

        "success":
            False,

        "error":
            "Method not allowed."

    }), 405


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 65)
    print("                 MEDGUARDIAN AI")
    print("           PHASE 6 - SMART DASHBOARD")
    print("=" * 65)

    print(
        "Gemini:",
        "Connected"
        if gemini_client
        else "Fallback Mode"
    )

    print(
        "Model:",
        MODEL_NAME
    )

    print(
        "Login:",
        "http://127.0.0.1:5000/login"
    )

    print("=" * 65)

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT",10000))
        debug=False
    ) 



