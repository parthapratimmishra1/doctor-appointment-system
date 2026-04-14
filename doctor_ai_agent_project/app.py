from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
APPOINTMENTS_FILE = DATA_DIR / "appointments.json"

DOCTORS = [
    {
        "id": 1,
        "name": "Dr. Ananya Sen",
        "specialization": "General Physician",
        "keywords": ["fever", "cold", "cough", "body pain", "infection", "weakness", "headache"],
        "fee": 500,
        "slots": ["10:00 AM", "11:00 AM", "01:00 PM", "04:00 PM"],
    },
    {
        "id": 2,
        "name": "Dr. Rahul Mehta",
        "specialization": "Cardiologist",
        "keywords": ["chest pain", "heart", "bp", "blood pressure", "palpitation", "breathlessness"],
        "fee": 900,
        "slots": ["09:30 AM", "12:30 PM", "03:00 PM", "05:30 PM"],
    },
    {
        "id": 3,
        "name": "Dr. Priya Sharma",
        "specialization": "Dermatologist",
        "keywords": ["skin", "rash", "pimples", "itching", "allergy", "acne"],
        "fee": 700,
        "slots": ["10:30 AM", "12:00 PM", "02:30 PM", "06:00 PM"],
    },
    {
        "id": 4,
        "name": "Dr. Arjun Roy",
        "specialization": "Orthopedic",
        "keywords": ["bone", "joint", "knee", "back pain", "fracture", "shoulder pain"],
        "fee": 800,
        "slots": ["11:30 AM", "02:00 PM", "04:30 PM", "07:00 PM"],
    },
    {
        "id": 5,
        "name": "Dr. Neha Kapoor",
        "specialization": "Pediatrician",
        "keywords": ["child", "baby", "kid", "vaccination", "children", "newborn"],
        "fee": 650,
        "slots": ["09:00 AM", "11:30 AM", "01:30 PM", "05:00 PM"],
    },
]

DEFAULT_SLOTS = ["09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "02:00 PM", "04:00 PM"]


if not APPOINTMENTS_FILE.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    APPOINTMENTS_FILE.write_text("[]", encoding="utf-8")


# ---------- Utility Functions ----------

def load_appointments() -> List[Dict]:
    try:
        with open(APPOINTMENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []



def save_appointments(appointments: List[Dict]) -> None:
    with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(appointments, f, indent=2)



def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()



def detect_intent(message: str) -> str:
    msg = normalize_text(message)
    if any(word in msg for word in ["cancel", "delete", "remove"]):
        return "cancel"
    if any(word in msg for word in ["show my appointments", "view my appointments", "list appointments", "my bookings"]):
        return "view"
    if any(word in msg for word in ["book", "appointment", "schedule", "consult", "meet doctor"]):
        return "book"
    if any(word in msg for word in ["doctor", "specialist", "symptom", "suggest"]):
        return "recommend"
    return "general"



def extract_date(message: str) -> Optional[str]:
    msg = normalize_text(message)
    today = datetime.now().date()

    if "today" in msg:
        return today.isoformat()
    if "tomorrow" in msg:
        return today.replace(day=today.day).fromordinal(today.toordinal() + 1).isoformat()

    patterns = [
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{1,2}/\d{1,2}/\d{4})",
        r"(\d{1,2}-\d{1,2}-\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            date_str = match.group(1)
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(date_str, fmt).date().isoformat()
                except ValueError:
                    continue
    return None



def extract_time(message: str) -> Optional[str]:
    match_12h = re.search(r"(1[0-2]|0?[1-9])(?::([0-5][0-9]))?\s?(am|pm)", message, re.I)
    if match_12h:
        hour = int(match_12h.group(1))
        minute = match_12h.group(2) or "00"
        period = match_12h.group(3).upper()
        return f"{hour:02d}:{minute} {period}"

    match_24h = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", message)
    if match_24h:
        raw = f"{match_24h.group(1)}:{match_24h.group(2)}"
        dt = datetime.strptime(raw, "%H:%M")
        return dt.strftime("%I:%M %p")
    return None



def extract_name(message: str) -> Optional[str]:
    patterns = [
        r"my name is ([a-zA-Z ]+)",
        r"i am ([a-zA-Z ]+)",
        r"patient name is ([a-zA-Z ]+)",
        r"for ([a-zA-Z ]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.I)
        if match:
            name = match.group(1).strip()
            if len(name.split()) <= 4:
                return name.title()
    return None



def extract_phone(message: str) -> Optional[str]:
    match = re.search(r"\b[6-9]\d{9}\b", message)
    return match.group(0) if match else None



def find_best_doctors(message: str) -> List[Dict]:
    msg = normalize_text(message)
    scored: List[Tuple[int, Dict]] = []
    for doctor in DOCTORS:
        score = 0
        if doctor["specialization"].lower() in msg:
            score += 3
        for keyword in doctor["keywords"]:
            if keyword in msg:
                score += 2
        scored.append((score, doctor))

    scored.sort(key=lambda item: item[0], reverse=True)
    best = [doctor for score, doctor in scored if score > 0]
    return best[:3] if best else DOCTORS[:3]



def get_doctor_by_name(message: str) -> Optional[Dict]:
    msg = normalize_text(message)
    for doctor in DOCTORS:
        if normalize_text(doctor["name"]) in msg:
            return doctor
        last_name = normalize_text(doctor["name"]).split()[-1]
        if last_name in msg:
            return doctor
        spec = doctor["specialization"].lower()
        if spec in msg:
            return doctor
    return None



def doctor_slots_for_date(doctor: Dict, date_str: str) -> List[str]:
    appointments = load_appointments()
    booked = {
        appt["time"]
        for appt in appointments
        if appt["doctor_id"] == doctor["id"] and appt["date"] == date_str
    }
    return [slot for slot in doctor.get("slots", DEFAULT_SLOTS) if slot not in booked]



def create_appointment(patient_name: str, phone: str, doctor: Dict, date_str: str, time_str: str) -> Dict:
    appointments = load_appointments()
    appointment_id = 1000 + len(appointments) + 1
    record = {
        "appointment_id": appointment_id,
        "patient_name": patient_name,
        "phone": phone,
        "doctor_id": doctor["id"],
        "doctor_name": doctor["name"],
        "specialization": doctor["specialization"],
        "date": date_str,
        "time": time_str,
        "status": "Booked",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    appointments.append(record)
    save_appointments(appointments)
    return record



def cancel_appointment_by_id(appointment_id: int) -> bool:
    appointments = load_appointments()
    new_appointments = [a for a in appointments if a["appointment_id"] != appointment_id]
    if len(new_appointments) == len(appointments):
        return False
    save_appointments(new_appointments)
    return True



def get_user_appointments(phone: str) -> List[Dict]:
    appointments = load_appointments()
    return [a for a in appointments if a["phone"] == phone]



def ai_response(message: str) -> Dict:
    intent = detect_intent(message)
    date_str = extract_date(message) or datetime.now().date().isoformat()
    time_str = extract_time(message)
    patient_name = extract_name(message) or "Patient"
    phone = extract_phone(message)

    if intent == "view":
        if not phone:
            return {"reply": "Please provide your 10-digit phone number to view your appointments.", "action": "need_phone"}
        appointments = get_user_appointments(phone)
        if not appointments:
            return {"reply": "No appointments found for this phone number.", "action": "view", "appointments": []}
        return {"reply": "Here are your booked appointments.", "action": "view", "appointments": appointments}

    if intent == "cancel":
        id_match = re.search(r"\b(10\d{2,})\b", message)
        if not id_match:
            return {"reply": "Please send the appointment ID to cancel. Example: cancel 1001", "action": "need_id"}
        appointment_id = int(id_match.group(1))
        success = cancel_appointment_by_id(appointment_id)
        if success:
            return {"reply": f"Appointment {appointment_id} has been cancelled successfully.", "action": "cancel"}
        return {"reply": "Appointment ID not found.", "action": "cancel_failed"}

    if intent in {"recommend", "general"}:
        doctors = find_best_doctors(message)
        doctor_lines = [
            f"{index + 1}. {doc['name']} - {doc['specialization']} (Fee: ₹{doc['fee']})"
            for index, doc in enumerate(doctors)
        ]
        return {
            "reply": "Based on your symptoms, these doctors are recommended:\n" + "\n".join(doctor_lines) + "\n\nYou can type: Book appointment with Dr. Ananya Sen tomorrow at 10 AM my name is Rahul 9876543210",
            "action": "recommend",
            "doctors": doctors,
        }

    if intent == "book":
        doctor = get_doctor_by_name(message)
        if not doctor:
            doctors = find_best_doctors(message)
            doctor = doctors[0]

        if not phone:
            return {"reply": "Please provide your 10-digit phone number to book the appointment.", "action": "need_phone"}

        if patient_name == "Patient":
            return {"reply": "Please provide your name. Example: my name is Rohan", "action": "need_name"}

        available_slots = doctor_slots_for_date(doctor, date_str)
        if not available_slots:
            return {
                "reply": f"No slots are available for {doctor['name']} on {date_str}. Please choose another date.",
                "action": "no_slots",
            }

        if not time_str:
            return {
                "reply": f"Available slots for {doctor['name']} on {date_str}: {', '.join(available_slots)}. Please choose one.",
                "action": "choose_time",
                "doctor": doctor,
                "slots": available_slots,
            }

        normalized_slots = {slot.upper(): slot for slot in available_slots}
        time_key = time_str.upper()
        if time_key not in normalized_slots:
            return {
                "reply": f"Selected time is not available. Available slots for {doctor['name']} on {date_str}: {', '.join(available_slots)}",
                "action": "invalid_time",
                "slots": available_slots,
            }

        booking = create_appointment(patient_name, phone, doctor, date_str, normalized_slots[time_key])
        return {
            "reply": (
                f"Appointment booked successfully.\n"
                f"Appointment ID: {booking['appointment_id']}\n"
                f"Patient: {booking['patient_name']}\n"
                f"Doctor: {booking['doctor_name']}\n"
                f"Specialization: {booking['specialization']}\n"
                f"Date: {booking['date']}\n"
                f"Time: {booking['time']}"
            ),
            "action": "booked",
            "appointment": booking,
        }

    return {"reply": "Sorry, I could not understand that. Please try again.", "action": "fallback"}


# ---------- Routes ----------

@app.route("/")
def home():
    appointments = load_appointments()
    return render_template("index.html", doctors=DOCTORS, appointments=appointments)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    response = ai_response(message)
    return jsonify(response)


@app.route("/book-form", methods=["POST"])
def book_form():
    patient_name = request.form.get("patient_name", "").strip()
    phone = request.form.get("phone", "").strip()
    doctor_id = int(request.form.get("doctor_id", "0"))
    date_str = request.form.get("date", "").strip()
    time_str = request.form.get("time", "").strip()

    doctor = next((doc for doc in DOCTORS if doc["id"] == doctor_id), None)
    if not doctor:
        return jsonify({"success": False, "message": "Doctor not found."})

    if not patient_name or not phone or not date_str or not time_str:
        return jsonify({"success": False, "message": "Please fill all fields."})

    available_slots = doctor_slots_for_date(doctor, date_str)
    if time_str not in available_slots:
        return jsonify({"success": False, "message": f"This slot is not available. Free slots: {', '.join(available_slots)}"})

    booking = create_appointment(patient_name, phone, doctor, date_str, time_str)
    return jsonify({"success": True, "message": "Appointment booked successfully.", "appointment": booking})


@app.route("/appointments")
def appointments():
    return jsonify(load_appointments())


if __name__ == "__main__":
    app.run(debug=True)
