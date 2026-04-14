# Doctor Appointment Booking System

## Description
A web-based application for booking and managing doctor appointments. The system includes a rule-based chatbot that helps users book, view, and cancel appointments, along with doctor recommendation based on symptoms.

## Features
- Book doctor appointments
- View booked appointments
- Cancel appointments
- Rule-based chatbot for user queries
- Doctor recommendation based on symptoms
- Slot availability checking
- JSON-based appointment storage

## Tech Stack
- Frontend: HTML, CSS
- Backend: Python, Flask
- Storage: JSON

## Project Structure
doctor-appointment-system/
├── app.py
├── templates/
│   └── index.html
├── static/
│   └── style.css
├── data/
│   └── appointments.json

## How to Run
1. Install Python
2. Install Flask using:
   pip install flask
3. Run the app:
   python app.py
4. Open in browser:
   http://127.0.0.1:5000

## Future Improvements
- Add database integration
- Add user authentication
- Improve chatbot intelligence
- Add appointment history dashboard
