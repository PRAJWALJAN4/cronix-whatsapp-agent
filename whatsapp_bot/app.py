import os
import json
import logging
import random
import requests
from requests.auth import HTTPBasicAuth
from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from google import genai
import math
from dotenv import load_dotenv

# We import the local pillow-based image generator
from image_generator import generate_grid_image

# Load .env from same directory as app.py
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_url_path='/static', static_folder='static')

@app.route('/simulator')
def simulator_page():
    return send_from_directory('static', 'simulator.html')

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_SMS_NUMBER = os.getenv('TWILIO_SMS_NUMBER') # Add this to .env
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
NGROK_URL = os.getenv('NGROK_URL', 'http://localhost:5000')

# In-memory session store (Replace with DB for production)
user_sessions = {}

# Check if credentials are placeholders
HAS_VALID_TWILIO = TWILIO_ACCOUNT_SID and "your_account_sid" not in TWILIO_ACCOUNT_SID
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if HAS_VALID_TWILIO else None

# Gemini Setup
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
HAS_VALID_GEMINI = GEMINI_API_KEY and "your_gemini_api_key" not in GEMINI_API_KEY
if HAS_VALID_GEMINI:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    genai_client = None

# Fallback translations in case Gemini is throttled or offline
FALLBACK_TRANSLATIONS = {
    "Hindi": {
        "Hi! Welcome to Safecloak! 🔐": "नमस्ते! सेफक्लोक में आपका स्वागत है! 🔐",
        "Hi! I am your Safecloak AI agent. I can help you with loading your luggage without standing in the line, and I am very fast! 🚀\n\nTo get started, please enter the OTP (use 1234 for demo) to verify your number.": "नमस्ते! मैं आपका सेफक्लोक AI एजेंट हूं। मैं आपको लाइन में खड़े हुए बिना अपना सामान लोड करने में मदद कर सकता हूं, और मैं बहुत तेज़ हूं! 🚀\n\nशुरू करने के लिए, कृपया ओटीपी (OTP) (डेमो के लिए 1234 का उपयोग करें) दर्ज करें।",
        "✅ OTP Verified Successfully.\n\nHow would you like to proceed?\n1. 📱 Book for yourself (I'm at the booth)\n2. 📦 Book for someone else (remote booking)": "✅ ओटीपी सफलतापूर्वक सत्यापित।\n\nआप कैसे आगे बढ़ना चाहेंगे?\n1. 📱 अपने लिए बुक करें (मैं बूथ पर हूं)\n2. 📦 किसी और के लिए बुक करें (रिमोट बुकिंग)",
        "📷 Great! You're at the booth.\n\nPlease scan the QR code on the Safecloak machine and send the image here.": "📷 बहुत बढ़िया! आप बूथ पर हैं।\n\nकृपया सेफक्लोक मशीन पर क्यूआर (QR) कोड स्कैन करें और यहां इमेज भेजें।",
        "Please type the location name (e.g., 'MG Road, Bangalore' or 'Airport Terminal 1') to fetch live booth availability.": "लाइव बूथ उपलब्धता प्राप्त करने के लिए कृपया स्थान का नाम टाइप करें (जैसे 'एमजी रोड, बैंगलोर')।",
        "🎉 Awesome! You're at the {booth_name} Safecloak booth!\n\n🟢 Green = Available\n🔴 Red = Occupied\n\nPlease select the box code you want to book (e.g., M1, S1):": "🎉 बहुत बढ़िया! आप {booth_name} सेफक्लोक बूथ पर हैं!\n\n🟢 हरा = उपलब्ध\n🔴 लाल = भरा हुआ\n\nकृपया वह बॉक्स कोड चुनें जिसे आप बुक करना चाहते हैं (जैसे M1, S1):",
        "📍 I found a Safecloak booth near {incoming_msg}!\n\n🟢 Green = Available\n🔴 Red = Occupied\n\nPlease select the box code you want to book (e.g., M1, S1):": "📍 मुझे {incoming_msg} के पास एक सेफक्लोक बूथ मिला!\n\n🟢 हरा = उपलब्ध\n🔴 लाल = भरा हुआ\n\nकृपया वह बॉक्स कोड चुनें जिसे आप बुक करना चाहते हैं (जैसे M1, S1):",
        "⏱️ You selected {selected_code} ({size_label})\n\nPlease select the duration:\n\n{options_text}\n\nReply with the option number (e.g., '1', '3'):": "⏱️ आपने {selected_code} ({size_label}) चुना है\n\nकृपया अवधि चुनें:\n\n{options_text}\n\nविकल्प संख्या (जैसे, '1', '3') के साथ उत्तर दें:",
        "💳 Great! Please scan the QR code to make the payment.\n\nOnce done, just reply with exactly -> *paid* to proceed.": "💳 बहुत बढ़िया! भुगतान करने के लिए कृपया क्यूआर (QR) कोड स्कैन करें।\n\nहो जाने के बाद, आगे बढ़ने के लिए बस *paid* के साथ उत्तर दें।",
        "Please reply with '1' (at the booth) or '2' (remote booking).": "कृपया '1' (बूथ पर) या '2' (रिमोट बुकिंग) के साथ उत्तर दें।",
        "🔓 Locker {selected_code} opened! Please load the luggage and close the lock properly.": "🔓 लॉकर {selected_code} खुल गया है! कृपया अपना सामान लोड करें और लॉक को ठीक से बंद करें।",
        "✅ Locker {selected_code} is now securely locked.\n\nThank you for choosing Safecloak! 🙏 Your luggage is safe with us.\n\nWhenever you're ready to collect it, just send 'Hi' and we'll guide you through the retrieval process. Enjoy your time! 🌟": "✅ लॉकर {selected_code} अब सुरक्षित रूप से लॉक हो गया है।\n\nसेफक्लोक चुनने के लिए धन्यवाद! 🙏 आपका सामान हमारे पास सुरक्षित है।\n\nजब भी आप इसे लेने के लिए तैयार हों, बस 'Hi' भेजें और हम आपको इसे वापस लेने की प्रक्रिया में मार्गदर्शन करेंगे। अपने समय का आनंद लें! 🌟"
    },
    "Kannada": {
        "Hi! Welcome to Safecloak! 🔐": "ನಮಸ್ಕಾರ! ಸೇಫ್‌ಕ್ಲೋಕ್-ಗೆ ಸುಸ್ವಾಗತ! 🔐",
        "Hi! I am your Safecloak AI agent. I can help you with loading your luggage without standing in the line, and I am very fast! 🚀\n\nTo get started, please enter the OTP (use 1234 for demo) to verify your number.": "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ಸೇಫ್‌ಕ್ಲೋಕ್ AI ಏಜೆಂಟ್. ಲೈನ್‌ನಲ್ಲಿ ನಿಲ್ಲದೆ ನಿಮ್ಮ ಲಗೇಜ್ ಅನ್ನು ಲೋಡ್ ಮಾಡಲು ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ, ಮತ್ತು ನಾನು ತುಂಬಾ ವೇಗವಾಗಿದ್ದೇನೆ! 🚀\n\nಪ್ರಾರಂಭಿಸಲು, ದಯವಿಟ್ಟು OTP (ಡೆಮೊಗಾಗಿ 1234 ಬಳಸಿ) ನಮೂದಿಸಿ.",
        "✅ OTP Verified Successfully.\n\nHow would you like to proceed?\n1. 📱 Book for yourself (I'm at the booth)\n2. 📦 Book for someone else (remote booking)": "✅ OTP ಯಶಸ್ವಿಯಾಗಿ ಪರಿಶೀಲಿಸಲಾಗಿದೆ.\n\nನೀವು ಹೇಗೆ ಮುಂದುವರಿಯಲು ಬಯಸುತ್ತೀರಿ?\n1. 📱 ನಿಮಗಾಗಿ ಬುಕ್ ಮಾಡಿ (ನಾನು ಬೂತ್‌ನಲ್ಲಿದ್ದೇನೆ)\n2. 📦 ಬೇರೆಯವರಿಗಾಗಿ ಬುಕ್ ಮಾಡಿ (ದೂರದ ಬುಕ್ಕಿಂಗ್)",
        "📷 Great! You're at the booth.\n\nPlease scan the QR code on the Safecloak machine and send the image here.": "📷 ಉತ್ತಮ! ನೀವು ಬೂತ್‌ನಲ್ಲಿದ್ದೀರಿ.\n\nದಯವಿಟ್ಟು ಸೇಫ್‌ಕ್ಲೋಕ್ ಯಂತ್ರದಲ್ಲಿರುವ QR ಕೋಡ್ ಅನ್ನು ಸ್ಕ್ಯಾನ್ ಮಾಡಿ ಮತ್ತು ಚಿತ್ರವನ್ನು ಇಲ್ಲಿ ಕಳುಹಿಸಿ.",
        "Please type the location name (e.g., 'MG Road, Bangalore' or 'Airport Terminal 1') to fetch live booth availability.": "ಲೈವ್ ಬೂತ್ ಲಭ್ಯತೆಯನ್ನು ಪಡೆಯಲು ದಯವಿಟ್ಟು ಸ್ಥಳದ ಹೆಸರನ್ನು ಟೈಪ್ ಮಾಡಿ (ಉದಾಹರಣೆಗೆ 'MG ರಸ್ತೆ, ಬೆಂಗಳೂರು').",
        "🎉 Awesome! You're at the {booth_name} Safecloak booth!\n\n🟢 Green = Available\n🔴 Red = Occupied\n\nPlease select the box code you want to book (e.g., M1, S1):": "🎉 ಅದ್ಭುತ! ನೀವು {booth_name} ಸೇಫ್‌ಕ್ಲೋಕ್ ಬೂತ್‌ನಲ್ಲಿದ್ದೀರಿ!\n\n🟢 ಹಸಿರು = ಲಭ್ಯವಿದೆ\n🔴 ಕೆಂಪು = ಭರ್ತಿಯಾಗಿದೆ\n\nದಯವಿಟ್ಟು ನೀವು ಬುಕ್ ಮಾಡಲು ಬಯಸುವ ಬಾಕ್ಸ್ ಕೋಡ್ ಅನ್ನು ಆಯ್ಕೆ ಮಾಡಿ (ಉದಾಹರಣೆಗೆ M1, S1):",
        "📍 I found a Safecloak booth near {incoming_msg}!\n\n🟢 Green = Available\n🔴 Red = Occupied\n\nPlease select the box code you want to book (e.g., M1, S1):": "📍 {incoming_msg} ಹತ್ತಿರ ನಾನು ಸೇಫ್‌ಕ್ಲೋಕ್ ಬೂತ್ ಕಂಡುಕೊಂಡೆ!\n\n🟢 ಹಸಿರು = ಲಭ್ಯವಿದೆ\n🔴 ಕೆಂಪು = ಭರ್ತಿಯಾಗಿದೆ\n\nದಯವಿಟ್ಟು ನೀವು ಬುಕ್ ಮಾಡಲು ಬಯಸುವ ಬಾಕ್ಸ್ ಕೋಡ್ ಅನ್ನು ಆಯ್ಕೆ ಮಾಡಿ (ಉದಾಹರಣೆಗೆ M1, S1):",
        "⏱️ You selected {selected_code} ({size_label})\n\nPlease select the duration:\n\n{options_text}\n\nReply with the option number (e.g., '1', '3'):": "⏱️ ನೀವು {selected_code} ({size_label}) ಅನ್ನು ಆರಿಸಿದ್ದೀರಿ\n\nದಯವಿಟ್ಟು ಅವಧಿಯನ್ನು ಆಯ್ಕೆಮಾಡಿ:\n\n{options_text}\n\nಆಯ್ಕೆಯ ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಉತ್ತರಿಸಿ (ಉದಾಹರಣೆಗೆ, '1', '3'):",
        "💳 Great! Please scan the QR code to make the payment.\n\nOnce done, just reply with exactly -> *paid* to proceed.": "💳 ಉತ್ತಮ! ಪಾವತಿ ಮಾಡಲು ದಯವಿಟ್ಟು QR ಕೋಡ್ ಅನ್ನು ಸ್ಕ್ಯಾನ್ ಮಾಡಿ.\n\nಮುಗಿದ ನಂತರ, ಮುಂದುವರಿಯಲು *paid* ಎಂದು ಉತ್ತರಿಸಿ.",
        "Please reply with '1' (at the booth) or '2' (remote booking).": "ದಯವಿಟ್ಟು '1' (ಬೂತ್‌ನಲ್ಲಿ) ಅಥವಾ '2' (ದೂರದ ಬುಕ್ಕಿಂಗ್) ನೊಂದಿಗೆ ಉತ್ತರಿಸಿ.",
        "🔓 Locker {selected_code} opened! Please load the luggage and close the lock properly.": "🔓 ಲಾಕರ್ {selected_code} ತೆರೆಯಲಾಗಿದೆ! ದಯವಿಟ್ಟು ಲಗೇಜ್ ಅನ್ನು ಲೋಡ್ ಮಾಡಿ ಮತ್ತು ಲಾಕ್ ಅನ್ನು ಸರಿಯಾಗಿ ಮುಚ್ಚಿ.",
        "✅ Locker {selected_code} is now securely locked.\n\nThank you for choosing Safecloak! 🙏 Your luggage is safe with us.\n\nWhenever you're ready to collect it, just send 'Hi' and we'll guide you through the retrieval process. Enjoy your time! 🌟": "✅ ಲಾಕರ್ {selected_code} ಈಗ ಸುರಕ್ಷಿತವಾಗಿ ಲಾಕ್ ಆಗಿದೆ.\n\nಸೇಫ್‌ಕ್ಲೋಕ್ ಆಯ್ಕೆ ಮಾಡಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು! 🙏 ನಿಮ್ಮ ಲಗೇಜ್ ನಮ್ಮ ಬಳಿ ಸುರಕ್ಷಿತವಾಗಿದೆ.\n\nಯಾವಾಗ ಬೇಕಾದರೂ ನೀವು ಅದನ್ನು ಸಂಗ್ರಹಿಸಲು ಸಿದ್ಧರಾದಾಗ, ಕೇವಲ 'Hi' ಎಂದು ಕಳುಹಿಸಿ ಮತ್ತು ಸಂಗ್ರಹಣೆ ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿ ನಾವು ನಿಮಗೆ ಮಾರ್ಗದರ್ಶನ ನೀಡುತ್ತೇವೆ. ನಿಮ್ಮ ಸಮಯವನ್ನು ಆನಂದಿಸಿ! 🌟",
        "👋 Welcome back!\n\nYour luggage is stored in Locker {selected_code}.\n\nWould you like to retrieve it?\n1. Yes, open my locker\n2. No, keep it stored": "👋 ಮತ್ತೆ ಸುಸ್ವಾಗತ!\n\nನಿಮ್ಮ ಲಗೇಜ್ ಅನ್ನು ಲಾಕರ್ {selected_code} ನಲ್ಲಿ ಸಂಗ್ರಹಿಸಲಾಗಿದೆ.\n\nನೀವು ಅದನ್ನು ಹಿಂಪಡೆಯಲು ಬಯಸುವಿರಾ?\n1. ಹೌದು, ನನ್ನ ಲಾಕರ್ ತೆರೆಯಿರಿ\n2. ಇಲ್ಲ, ಹಾಗೆಯೇ ಇರಲಿ",
        "🔑 Unlocking Locker {selected_code}...\n\nReply '1' to confirm and open the locker.": "🔑 ಲಾಕರ್ {selected_code} ಅನ್ನು ಅನ್‌ಲಾಕ್ ಮಾಡಲಾಗುತ್ತಿದೆ...\n\nದೃಢೀಕರಿಸಲು ಮತ್ತು ಲಾಕರ್ ತೆರೆಯಲು '1' ಎಂದು ಉತ್ತರಿಸಿ.",
        "🔓 Locker {selected_code} is now open!\n\nPlease collect your luggage and reply 'done' once you have taken it.": "🔓 ಲಾಕರ್ {selected_code} ಈಗ ತೆರೆಯಲಾಗಿದೆ!\n\nದಯವಿಟ್ಟು ನಿಮ್ಮ ಲಗೇಜ್ ಅನ್ನು ಸಂಗ್ರಹಿಸಿ ಮತ್ತು ನೀವು ಅದನ್ನು ತೆಗೆದುಕೊಂಡ ನಂತರ 'done' ಎಂದು ಉತ್ತರಿಸಿ.",
        "✅ Luggage collected from Locker {selected_code}.\n\nThank you for using Safecloak! We hope to see you again soon. 😊\n\nSend 'Hi' to start a new booking.": "✅ ಲಾಕರ್ {selected_code} ನಿಂದ ಲಗೇಜ್ ಸಂಗ್ರಹಿಸಲಾಗಿದೆ.\n\nಸೇಫ್‌ಕ್ಲೋಕ್ ಬಳಸಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು! ಶೀಘ್ರದಲ್ಲೇ ನಿಮ್ಮನ್ನು ಮತ್ತೆ ನೋಡುತ್ತೇವೆ ಎಂದು ನಾವು ಭಾವಿಸುತ್ತೇವೆ. 😊\n\nಹೊಸ ಬುಕಿಂಗ್ ಪ್ರಾರಂಭಿಸಲು 'Hi' ಎಂದು ಕಳುಹಿಸಿ.",
        "₹30 for 3 hours": "3 ಗಂಟೆಗಳಿಗೆ ₹30",
        "₹60 for 6 hours": "6 ಗಂಟೆಗಳಿಗೆ ₹60",
        "₹90 for 9 hours": "9 ಗಂಟೆಗಳಿಗೆ ₹90",
        "₹120 per day": "ಒಂದು ದಿನಕ್ಕೆ ₹120",
        "₹40 for 3 hours": "3 ಗಂಟೆಗಳಿಗೆ ₹40",
        "₹80 for 6 hours": "6 ಗಂಟೆಗಳಿಗೆ ₹80",
        "₹120 for 9 hours": "9 ಗಂಟೆಗಳಿಗೆ ₹120",
        "₹160 per day": "ಒಂದು ದಿನಕ್ಕೆ ₹160",
        "₹60 for 3 hours": "3 ಗಂಟೆಗಳಿಗೆ ₹60",
        "₹110 for 6 hours": "6 ಗಂಟೆಗಳಿಗೆ ₹110",
        "₹160 for 9 hours": "9 ಗಂಟೆಗಳಿಗೆ ₹160",
        "₹220 per day": "ಒಂದು ದಿನಕ್ಕೆ ₹220"
    },
    "Hindi": {
        "Hi! Welcome to Safecloak! 🔐": "नमस्ते! सेफक्लोक में आपका स्वागत है! 🔐",
        "Hi! I am your Safecloak AI agent. I can help you with loading your luggage without standing in the line, and I am very fast! 🚀\n\nTo get started, please enter the OTP (use 1234 for demo) to verify your number.": "नमस्ते! मैं आपका सेफक्लोक AI एजेंट हूं। मैं आपको लाइन में खड़े हुए बिना अपना सामान लोड करने में मदद कर सकता हूं, और मैं बहुत तेज़ हूं! 🚀\n\nशुरू करने के लिए, कृपया ओटीपी (OTP) (डेमो के लिए 1234 का उपयोग करें) दर्ज करें।",
        "✅ OTP Verified Successfully.\n\nHow would you like to proceed?\n1. 📱 Book for yourself (I'm at the booth)\n2. 📦 Book for someone else (remote booking)": "✅ ओटीपी सफलतापूर्वक सत्यापित।\n\nआप कैसे आगे बढ़ना चाहेंगे?\n1. 📱 अपने लिए बुक करें (मैं बूथ पर हूं)\n2. 📦 किसी और के लिए बुक करें (रिमोट बुकिंग)",
        "📷 Great! You're at the booth.\n\nPlease scan the QR code on the Safecloak machine and send the image here.": "📷 बहुत बढ़िया! आप बूथ पर हैं।\n\nकृपया सेफक्लोक मशीन पर क्यूआर (QR) कोड स्कैन करें और यहां इमेज भेजें।",
        "Please type the location name (e.g., 'MG Road, Bangalore' or 'Airport Terminal 1') to fetch live booth availability.": "लाइव बूथ उपलब्धता प्राप्त करने के लिए कृपया स्थान का नाम टाइप करें (जैसे 'एमजी रोड, बैंगलोर')।",
        "🎉 Awesome! You're at the {booth_name} Safecloak booth!\n\n🟢 Green = Available\n🔴 Red = Occupied\n\nPlease select the box code you want to book (e.g., M1, S1):": "🎉 बहुत बढ़िया! आप {booth_name} सेफक्लोक बूथ पर हैं!\n\n🟢 हरा = उपलब्ध\n🔴 लाल = भरा हुआ\n\nकृपया वह बॉक्स कोड चुनें जिसे आप बुक करना चाहते हैं (जैसे M1, S1):",
        "📍 I found a Safecloak booth near {incoming_msg}!\n\n🟢 Green = Available\n🔴 Red = Occupied\n\nPlease select the box code you want to book (e.g., M1, S1):": "📍 मुझे {incoming_msg} के पास एक सेफक्लोक बूथ मिला!\n\n🟢 हरा = उपलब्ध\n🔴 लाल = भरा हुआ\n\nकृपया वह बॉक्स कोड चुनें जिसे आप बुक करना चाहते हैं (जैसे M1, S1):",
        "⏱️ You selected {selected_code} ({size_label})\n\nPlease select the duration:\n\n{options_text}\n\nReply with the option number (e.g., '1', '3'):": "⏱️ आपने {selected_code} ({size_label}) चुना है\n\nकृपया अवधि चुनें:\n\n{options_text}\n\nविकल्प संख्या (जैसे, '1', '3') के साथ उत्तर दें:",
        "💳 Great! Please scan the QR code to make the payment.\n\nOnce done, just reply with exactly -> *paid* to proceed.": "💳 बहुत बढ़िया! भुगतान करने के लिए कृपया क्यूआर (QR) कोड स्कैन करें।\n\nहो जाने के बाद, आगे बढ़ने के लिए बस *paid* के साथ उत्तर दें।",
        "Please reply with '1' (at the booth) or '2' (remote booking).": "कृपया '1' (बूथ पर) या '2' (रिमोट बुकिंग) के साथ उत्तर दें।",
        "🔓 Locker {selected_code} opened! Please load the luggage and close the lock properly.": "🔓 लॉकर {selected_code} खुल गया है! कृपया अपना सामान लोड करें और लॉक को ठीक से बंद करें।",
        "✅ Locker {selected_code} is now securely locked.\n\nThank you for choosing Safecloak! 🙏 Your luggage is safe with us.\n\nWhenever you're ready to collect it, just send 'Hi' and we'll guide you through the retrieval process. Enjoy your time! 🌟": "✅ लॉकर {selected_code} अब सुरक्षित रूप से लॉक हो गया है।\n\nसेफक्लोक चुनने के लिए धन्यवाद! 🙏 आपका सामान हमारे पास सुरक्षित है।\n\nजब भी आप इसे लेने के लिए तैयार हों, बस 'Hi' भेजें और हम आपको इसे वापस लेने की प्रक्रिया में मार्गदर्शन करेंगे। अपने समय का आनंद लें! 🌟",
        "👋 Welcome back!\n\nYour luggage is stored in Locker {selected_code}.\n\nWould you like to retrieve it?\n1. Yes, open my locker\n2. No, keep it stored": "👋 स्वागत है!\n\nआपका सामान लॉकर {selected_code} में जमा है।\n\nक्या आप इसे वापस लेना चाहेंगे?\n1. हाँ, मेरा लॉकर खोलें\n2. नहीं, इसे जमा रहने दें",
        "🔑 Unlocking Locker {selected_code}...\n\nReply '1' to confirm and open the locker.": "🔑 लॉकर {selected_code} को अनलॉक किया जा रहा है...\n\nपुष्टि करने और लॉकर खोलने के लिए '1' के साथ उत्तर दें।",
        "🔓 Locker {selected_code} is now open!\n\nPlease collect your luggage and reply 'done' once you have taken it.": "🔓 लॉकर {selected_code} अब खुला है!\n\nकृपया अपना सामान लें और लेने के बाद 'done' के साथ उत्तर दें।",
        "✅ Luggage collected from Locker {selected_code}.\n\nThank you for using Safecloak! We hope to see you again soon. 😊\n\nSend 'Hi' to start a new booking.": "✅ लॉकर {selected_code} से सामान ले लिया गया है।\n\nसेफक्लोक का उपयोग करने के लिए धन्यवाद! हमें उम्मीद है कि हम आपसे फिर मिलेंगे। 😊\n\nनया बुकिंग शुरू करने के लिए 'Hi' भेजें。",
        "₹30 for 3 hours": "3 घंटों के लिए ₹30",
        "₹60 for 6 hours": "6 घंटों के लिए ₹60",
        "₹90 for 9 hours": "9 घंटों के लिए ₹90",
        "₹120 per day": "प्रति दिन ₹120",
        "₹40 for 3 hours": "3 घंटों के लिए ₹40",
        "₹80 for 6 hours": "6 घंटों के लिए ₹80",
        "₹120 for 9 hours": "9 घंटों के लिए ₹120",
        "₹160 per day": "प्रति दिन ₹160",
        "₹60 for 3 hours": "3 घंटों के लिए ₹60",
        "₹110 for 6 hours": "6 घंटों के लिए ₹110",
        "₹160 for 9 hours": "9 घंटों के लिए ₹160",
        "₹220 per day": "प्रति दिन ₹220"
    }
}

# All supported Indian languages
SUPPORTED_LANGUAGES = {
    "1": "English",
    "2": "Hindi",
    "3": "Kannada",
    "4": "Tamil",
    "5": "Telugu",
    "6": "Malayalam",
    "7": "Marathi",
    "8": "Bengali",
    "9": "Gujarati",
    "10": "Punjabi",
    "11": "Odia",
    "12": "Assamese",
    "13": "Urdu",
    "14": "Konkani",
}

# Native script names for the welcome menu
LANG_NATIVE_NAMES = {
    "English": "English",
    "Hindi": "हिन्दी",
    "Kannada": "ಕನ್ನಡ",
    "Tamil": "தமிழ்",
    "Telugu": "తెలుగు",
    "Malayalam": "മലയാളം",
    "Marathi": "मराठी",
    "Bengali": "বাংলা",
    "Gujarati": "ગુજરાતી",
    "Punjabi": "ਪੰਜਾਬੀ",
    "Odia": "ଓଡ଼ିଆ",
    "Assamese": "অসমীয়া",
    "Urdu": "اردو",
    "Konkani": "कोंकणी",
}

# Translation cache to avoid repeated Gemini calls
translation_cache = {}

def translate_text(text, target_lang, **kwargs):
    if not target_lang or target_lang.lower() == 'english':
        return text
    
    # Check cache first
    cache_key = f"{target_lang}::{text}"
    if cache_key in translation_cache:
        result = translation_cache[cache_key]
        for var_name, var_value in kwargs.items():
            result = result.replace("{" + var_name + "}", str(var_value))
        return result

    # Use Gemini for translation
    if genai_client:
        prompt = f"""Translate the following text into {target_lang}. 
Rules:
- Keep it friendly and natural sounding
- Preserve all emojis exactly as they are
- Preserve all numbers, codes (like M1, S2, XL1), and currency symbols (₹) exactly
- Preserve all newlines
- DO NOT add any explanation, just return the translated text

Text: {text}"""
        try:
            # Using gemini-flash-latest for better general availability
            response = genai_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
            )
            if response and response.text:
                translated = response.text.strip()
                translation_cache[cache_key] = translated
                for var_name, var_value in kwargs.items():
                    translated = translated.replace("{" + var_name + "}", str(var_value))
                return translated
        except Exception as e:
            logging.error(f"Gemini translation error for {target_lang}: {e}")

    # 3. Fallback to hardcoded translations if Gemini fails or throttled
    if target_lang in FALLBACK_TRANSLATIONS:
        for eng_key, transl in FALLBACK_TRANSLATIONS[target_lang].items():
            # Handle messages with variables (e.g., {booth_name})
            # Split key into static parts and check if ALL parts exist in the text
            clean_key = eng_key
            vars_found = []
            import re
            variables = re.findall(r'\{(\w+)\}', eng_key)
            
            # Escape special regex chars in the key but keep placeholders
            regex_pattern = re.escape(eng_key)
            for var in variables:
                regex_pattern = regex_pattern.replace(f'\\{{{var}\\}}', '(.*)')
            
            match = re.match(f"^{regex_pattern}$", text, re.DOTALL)
            if match:
                result = transl
                # If we have matches, map them back to the translation variables
                for i, var_name in enumerate(variables):
                    val = match.group(i+1)
                    result = result.replace("{" + var_name + "}", val)
                    
                # Substitutes remaining variables from kwargs
                for var_name, var_value in kwargs.items():
                    result = result.replace("{" + var_name + "}", str(var_value))
                return result
            
            # Simple direct match fallback
            if eng_key == text:
                result = transl
                for var_name, var_value in kwargs.items():
                    result = result.replace("{" + var_name + "}", str(var_value))
                return result

    return text

# Paths
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

# Create necessary directories
os.makedirs(STATIC_DIR, exist_ok=True)

def update_session(sender, key, value):
    if sender not in user_sessions:
        user_sessions[sender] = {"state": "init"}
    user_sessions[sender][key] = value

def get_session(sender):
    if sender not in user_sessions:
        user_sessions[sender] = {"state": "init"}
    return user_sessions[sender]

def reset_session(sender):
    user_sessions[sender] = {"state": "init"}

def send_sms_otp(to_number, otp_code):
    if not client:
        logging.warning("Twilio client not initialized. Cannot send SMS.")
        return False
    
    # Strip 'whatsapp:' if present
    phone = to_number.replace('whatsapp:', '')
    
    try:
        message = client.messages.create(
            body=f"Your Safecloak verification code is: {otp_code}. Valid for 5 minutes.",
            from_=TWILIO_SMS_NUMBER,
            to=phone
        )
        logging.info(f"OTP SMS sent to {phone}: {message.sid}")
        return True
    except Exception as e:
        logging.error(f"Error sending SMS to {phone}: {e}")
        return False

def download_twilio_media(media_url, save_path):
    try:
        response = requests.get(media_url, auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        else:
            logging.error(f"Failed to download media: {response.status_code} {response.text}")
    except Exception as e:
        logging.error(f"Error downloading media from {media_url}: {e}")
    return False

def safe_load_template(location_name):
    # Attempt to load the JSON file representing the locker setup
    safe_name = "".join(c for c in location_name if c.isalnum() or c in (" ", ",", ".", "-", "_"))
    filepath = os.path.join(TEMPLATES_DIR, f"{safe_name}.json")
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None

def save_template(location_name, data):
    # Save disabled per user request to keep templates pristine
    pass

def get_distance(lat1, lon1, lat2, lon2):
    # Haversine formula to calculate distance in meters
    R = 6371000 # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def extract_location_name(message):
    message_lower = message.lower()
    
    # 1. Coordinate-based Geofencing (Instant & Accurate)
    if "coordinates:" in message_lower:
        try:
            # Extract numbers from "coordinates: 13.9615905, 75.5089735"
            parts = message_lower.replace("coordinates:", "").split(",")
            u_lat = float(parts[0].strip())
            u_lon = float(parts[1].strip())
            
            # Shivamogga / PES Coordinates
            pes_lat, pes_lon = 13.9617, 75.5090
            
            dist = get_distance(u_lat, u_lon, pes_lat, pes_lon)
            logging.info(f"Geofence check: Distance to PES is {dist:.2f} meters")
            
            if dist < 1000: # Within 1km radius
                return "Shivamogga"
        except Exception as e:
            logging.error(f"Geofence calculation error: {e}")

    # 2. FAST PATH: Local keyword matching
    if any(k in message_lower for k in ["shivamogga", "shivamoga", "pes", "shivmogga"]):
        return "Shivamogga"
    
    if any(k in message_lower for k in ["bangalore", "bengaluru", "bagalour", "blre", "bluru"]):
        return "Bangalore"
    
    if not genai_client:
        return message
    
    # 3. Gemini fallback for URLs and general text
    if "coordinates:" in message:
        prompt = f"The user shared their live location: {message}. Identify the city or facility name (like 'PES University' or 'Shivamogga') at these coordinates. Respond with ONLY the place/city name, no extra words."
    elif "http" in message or "maps" in message:
        prompt = f"The user sent a Google Maps link or location: {message}. Extract the name of the city or specific building/area from this link. Respond with ONLY the name, nothing else. If you can't determine it, respond with 'Unknown'."
    else:
        prompt = f"Extract the city or place name from this text: '{message}'. Respond with ONLY the place name, no extra words."
        
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        if response and response.text:
            cleaned = response.text.strip().replace("'", "").replace('"', "")
            return cleaned
    except Exception as e:
        logging.error(f"Gemini location extraction error: {e}")
    return message

def process_message(sender, incoming_msg, latitude=None, longitude=None, address=None, base_url=None):
    session = get_session(sender)
    state = session.get("state", "init")
    logging.info(f"User state for {sender}: {state}")
    msg_lower = incoming_msg.lower()

    # Use provided base_url or fallback to NGROK_URL from env or localhost
    effective_base_url = base_url if base_url else NGROK_URL
    if not effective_base_url.startswith('http'):
        effective_base_url = f"http://{effective_base_url}" if effective_base_url else "http://localhost:5000"

    if msg_lower in ['reset', 'restart']:
        reset_session(sender)
        return "Session restarted. Send 'Hi' to begin again.", None

    selected_lang = session.get("selected_lang", "English")

    # State Machine
    if state == "init":
        # Build language menu with native names
        lang_lines = []
        for num, lang in SUPPORTED_LANGUAGES.items():
            native = LANG_NATIVE_NAMES.get(lang, lang)
            lang_lines.append(f" {num}. {lang} ({native})")
        lang_menu = "\n".join(lang_lines)
        
        msg = f"""Hi! Welcome to Safecloak! 🔐
Please select your preferred language:
{lang_menu}

(Reply with the number)"""
        update_session(sender, "state", "language")
        return msg, None

    elif state == "language":
        selected_lang = SUPPORTED_LANGUAGES.get(incoming_msg)
        if not selected_lang:
            return "Please reply with a valid number (1-14).", None
        
        # Generate and Send OTP
        otp_code = str(random.randint(1000, 9999))
        update_session(sender, "selected_lang", selected_lang)
        update_session(sender, "state", "otp")
        update_session(sender, "expected_otp", otp_code)
        
        send_sms_otp(sender, otp_code)
        
        msg = f"Hi! I am your Safecloak AI agent. I can help you with loading your luggage without standing in the line, and I am very fast! 🚀\n\nTo get started, please enter the OTP sent to your phone via SMS to verify your number."
        return translate_text(msg, target_lang=selected_lang), None

    elif state == "otp":
        expected = session.get("expected_otp")
        if incoming_msg == expected: 
            update_session(sender, "state", "booking_type")
            msg = "✅ OTP Verified Successfully.\n\nHow would you like to proceed?\n1. 📱 Book for yourself (I'm at the booth)\n2. 📦 Book for someone else (remote booking)"
            return translate_text(msg, target_lang=selected_lang), None
        else:
            return translate_text(f"❌ Incorrect OTP. Please try again with the code sent to your phone.", target_lang=selected_lang), None

    elif state == "booking_type":
        if incoming_msg == "1":
            update_session(sender, "state", "scan_qr")
            msg = "📷 Great! You're at the booth.\n\nPlease scan the QR code on the Safecloak machine and send the image here."
            return translate_text(msg, target_lang=selected_lang), None
        elif incoming_msg == "2":
            update_session(sender, "state", "location")
            msg = "Please type the location name (e.g., 'MG Road, Bangalore' or 'Airport Terminal 1') to fetch live booth availability."
            return translate_text(msg, target_lang=selected_lang), None
        else:
            return translate_text("Please reply with '1' (at the booth) or '2' (remote booking).", target_lang=selected_lang), None

    elif state == "scan_qr":
        # Accept any message (text or image) as a QR scan confirmation
        # In a real scenario this would decode the QR, for now we simulate
        
        # Pick a random template to simulate booth detection
        try:
            all_templates = [f.replace('.json', '') for f in os.listdir(TEMPLATES_DIR) if f.endswith('.json')]
            target_template = random.choice(all_templates)
        except:
            target_template = "demo"
        
        template_data = safe_load_template(target_template)
        update_session(sender, "session_location", target_template)
        update_session(sender, "current_template_data", template_data)
        
        # Generate the grid image
        img_filename = f"{sender.split(':')[-1]}_grid.png"
        img_path = generate_grid_image(template_data, os.path.join(STATIC_DIR, img_filename))
        image_url = f"{effective_base_url}/static/{img_filename}"
        
        update_session(sender, "state", "select_locker")
        
        booth_names = ["PES College", "MG Road", "Majestic Bus Stand", "Airport Terminal 1", "Railway Station"]
        booth_name = random.choice(booth_names)
        
        msg = f"🎉 Awesome! You're at the {booth_name} Safecloak booth!\n\n🟢 Green = Available\n🔴 Red = Occupied\n\nPlease select the box code you want to book (e.g., M1, S1):"
        return translate_text(msg, target_lang=selected_lang), image_url

    elif state == "location":
        selected_lang = session.get("selected_lang", "English")
        # In demo mode, we just say "Found a booth near you!" regardless of input
        extracted_name = extract_location_name(incoming_msg)
        if not extracted_name or extracted_name == "Unknown":
            extracted_name = "your current location"
            
        logging.info(f"Detected location: {extracted_name} from input: {incoming_msg}")
        
        # Pick a RANDOM template from the templates directory
        try:
            all_templates = [f.replace('.json', '') for f in os.listdir(TEMPLATES_DIR) if f.endswith('.json')]
            target_template = random.choice(all_templates)
            logging.info(f"Randomly selected template: {target_template}")
        except Exception as e:
            logging.error(f"Error picking random template: {e}")
            target_template = "demo"
        
        # Load the fresh template data
        template_data = safe_load_template(target_template)
        
        # Store a copy in session so we can modify it locally without saving to disk
        update_session(sender, "session_location", target_template)
        update_session(sender, "current_template_data", template_data)
        
        # Generate the Image
        img_filename = f"{sender.split(':')[-1]}_grid.png"
        img_path = generate_grid_image(template_data, os.path.join(STATIC_DIR, img_filename))
        image_url = f"{effective_base_url}/static/{img_filename}"
        
        update_session(sender, "state", "select_locker")
        
        msg = f"📍 I found a Safecloak booth near {extracted_name}!\n\n🟢 Green = Available\n🔴 Red = Occupied\n\nPlease select the box code you want to book (e.g., M1, S1):"
        return translate_text(msg, target_lang=selected_lang, incoming_msg=extracted_name), image_url

    elif state == "select_locker":
        # Get template data from session
        template_data = session.get("current_template_data")
        if not template_data:
            sel_loc = session.get("session_location")
            template_data = safe_load_template(sel_loc)
        
        selected_code = incoming_msg.upper()
        
        from image_generator import calculate_display_blocks
        blocks = calculate_display_blocks(template_data)
        
        target_block = next((b for b in blocks if b['displayCode'] == selected_code), None)
        
        if not target_block:
            return translate_text(f"❌ Box '{selected_code}' not found in this booth layout. Please select a valid code.", target_lang=selected_lang), None
        
        l_status = template_data.get('lockerStatus', {})
        block_id = target_block['blockId']
        block_status = l_status.get(block_id, 'available')
        
        if block_status == 'occupied':
            return translate_text(f"⚠️ Sorry, {selected_code} is already occupied by someone else. Please choose another green box.", target_lang=selected_lang), None
        
        # Box is free
        update_session(sender, "selected_code", selected_code)
        update_session(sender, "selected_blockId", block_id)
        update_session(sender, "selected_size", target_block['size'])
        update_session(sender, "state", "duration")
        
        # Show pricing only for the selected locker size
        size = target_block['size']
        size_labels = {'s': '📦 Small', 'm': '🎒 Medium', 'l': '🧳 Large', 'xl': '🧳 Extra Large'}
        size_label = size_labels.get(size, '📦 Locker')
        
        pricing_tiers = {
            's': [
                ("1", "₹30 for 3 hours"),
                ("2", "₹60 for 6 hours"),
                ("3", "₹90 for 9 hours"),
                ("4", "₹120 per day"),
            ],
            'm': [
                ("1", "₹40 for 3 hours"),
                ("2", "₹80 for 6 hours"),
                ("3", "₹120 for 9 hours"),
                ("4", "₹160 per day"),
            ],
            'l': [
                ("1", "₹60 for 3 hours"),
                ("2", "₹110 for 6 hours"),
                ("3", "₹160 for 9 hours"),
                ("4", "₹220 per day"),
            ],
            'xl': [
                ("1", "₹60 for 3 hours"),
                ("2", "₹110 for 6 hours"),
                ("3", "₹160 for 9 hours"),
                ("4", "₹220 per day"),
            ],
        }
        
        options = pricing_tiers.get(size, pricing_tiers['m'])
        # Translate each option label individually
        translated_options = []
        for num, price_text in options:
            translated_price = translate_text(price_text, target_lang=selected_lang)
            translated_options.append(f"{num}. {translated_price}")
        options_text = "\n".join(translated_options)
        
        pricing = f"⏱️ You selected {selected_code} ({size_label})\n\nPlease select the duration:\n\n{options_text}\n\nReply with the option number (e.g., '1', '3'):"
        return translate_text(pricing, target_lang=selected_lang, selected_code=selected_code, size_label=size_label, options_text=options_text), None

    elif state == "duration":
        update_session(sender, "state", "payment")
        qr_url = "https://cdn.pixabay.com/photo/2013/07/12/14/45/qr-code-148732_1280.png"
        msg = "💳 Great! Please scan the QR code to make the payment.\n\nOnce done, just reply with exactly -> *paid* to proceed."
        return translate_text(msg, target_lang=selected_lang), qr_url

    elif state == "payment":
        if any(x in incoming_msg.lower() for x in ["paid", "done", "ok", "payed"]):
            update_session(sender, "state", "open_box")
            selected_code = session.get("selected_code")
            msg = f"✅ Payment verified!\n\nYour locker ({selected_code}) is ready.\n\nReply '1' to UNLOCK and open your locker."
            return translate_text(msg, target_lang=selected_lang, selected_code=selected_code), None
        else:
            return translate_text("Please complete the payment and type *paid*.", target_lang=selected_lang), None

    elif state == "open_box":
        if incoming_msg == "1":
            template_data = session.get("current_template_data")
            block_id = session.get("selected_blockId")
            
            if 'lockerStatus' not in template_data:
                template_data['lockerStatus'] = {}
            template_data['lockerStatus'][block_id] = 'occupied'
            
            # We skip save_template(sel_loc, template_data) to avoid overwriting files
            update_session(sender, "current_template_data", template_data)
            selected_code = session.get("selected_code")
            
            # Generate new updated image snapshot (showing it OPENED/Yellow)
            img_filename = f"{sender.split(':')[-1]}_opened.png"
            img_path = generate_grid_image(template_data, os.path.join(STATIC_DIR, img_filename), opened_block=block_id)
            image_url = f"{effective_base_url}/static/{img_filename}"
            
            # After confirmation, the session state reflects the occupancy
            # but next time someone starts, the JSON will be clean.
            update_session(sender, "state", "await_loading")
            msg = f"🔓 Locker {selected_code} opened! Please load the luggage and close the lock properly."
            return translate_text(msg, target_lang=selected_lang, selected_code=selected_code), image_url
        else:
            return translate_text("Reply '1' to trigger the unlock process.", target_lang=selected_lang), None

    elif state == "await_loading":
        if any(x in msg_lower for x in ["loaded", "loded", "done", "closed"]):
            template_data = session.get("current_template_data")
            selected_code = session.get("selected_code")
            
            # Generate image showing it LOCKED/Red (no opened_block flag)
            img_filename = f"{sender.split(':')[-1]}_locked.png"
            img_path = generate_grid_image(template_data, os.path.join(STATIC_DIR, img_filename))
            image_url = f"{effective_base_url}/static/{img_filename}"
            
            update_session(sender, "state", "completed")
            msg = f"✅ Locker {selected_code} is now securely locked.\n\nThank you for choosing Safecloak! 🙏 Your luggage is safe with us.\n\nWhenever you're ready to collect it, just send 'Hi' and we'll guide you through the retrieval process. Enjoy your time! 🌟"
            return translate_text(msg, target_lang=selected_lang, selected_code=selected_code), image_url
        else:
            return translate_text("Please reply with 'loaded' once you have closed the locker.", target_lang=selected_lang), None

    elif state == "completed":
        if msg_lower == "hi":
            selected_code = session.get("selected_code", "your locker")
            update_session(sender, "state", "retrieve")
            msg = f"👋 Welcome back!\n\nYour luggage is stored in Locker {selected_code}.\n\nWould you like to retrieve it?\n1. Yes, open my locker\n2. No, keep it stored"
            return translate_text(msg, target_lang=selected_lang, selected_code=selected_code), None
        return translate_text("Send 'Hi' when you're ready to collect your luggage.", target_lang=selected_lang), None

    elif state == "retrieve":
        if incoming_msg == "1":
            selected_code = session.get("selected_code")
            update_session(sender, "state", "retrieve_unlock")
            msg = f"🔑 Unlocking Locker {selected_code}...\n\nReply '1' to confirm and open the locker."
            return translate_text(msg, target_lang=selected_lang, selected_code=selected_code), None
        elif incoming_msg == "2":
            update_session(sender, "state", "completed")
            return translate_text("No worries! Your luggage is safe. Send 'Hi' whenever you're ready to collect it. 🔒", target_lang=selected_lang), None
        else:
            return translate_text("Please reply with '1' to open your locker or '2' to keep it stored.", target_lang=selected_lang), None

    elif state == "retrieve_unlock":
        if incoming_msg == "1":
            template_data = session.get("current_template_data")
            selected_code = session.get("selected_code")
            block_id = session.get("selected_blockId")
            
            # Show the locker as opened (yellow)
            img_filename = f"{sender.split(':')[-1]}_retrieved.png"
            img_path = generate_grid_image(template_data, os.path.join(STATIC_DIR, img_filename), opened_block=block_id)
            image_url = f"{effective_base_url}/static/{img_filename}"
            
            update_session(sender, "state", "retrieve_collect")
            msg = f"🔓 Locker {selected_code} is now open!\n\nPlease collect your luggage and reply 'done' once you have taken it."
            return translate_text(msg, target_lang=selected_lang, selected_code=selected_code), image_url
        else:
            return translate_text("Reply '1' to confirm and open the locker.", target_lang=selected_lang), None

    elif state == "retrieve_collect":
        if any(x in msg_lower for x in ["done", "collected", "taken", "got it", "yes"]):
            selected_code = session.get("selected_code")
            reset_session(sender)
            msg = f"✅ Luggage collected from Locker {selected_code}.\n\nThank you for using Safecloak! We hope to see you again soon. 😊\n\nSend 'Hi' to start a new booking."
            return translate_text(msg, target_lang=selected_lang, selected_code=selected_code), None
        else:
            return translate_text("Please reply 'done' once you have collected your luggage.", target_lang=selected_lang), None



def respond(msg_text, media_url=None):
    resp = MessagingResponse()
    msg = resp.message(msg_text)
    if media_url:
        msg.media(media_url)
    return str(resp)

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        incoming_msg = request.form.get('Body', '').strip()
        sender = request.form.get('From', 'unknown')
        
        # Handle Media (QR Scan)
        media_url = request.form.get('MediaUrl0')
        if media_url:
            # Create a unique filename for the downloaded image
            filename = f"scan_{sender.replace(':', '_')}_{random.randint(100,999)}.jpg"
            save_path = os.path.join(STATIC_DIR, filename)
            if download_twilio_media(media_url, save_path):
                logging.info(f"Downloaded media from {sender} to {save_path}")
                # We can store the path to use it for QR decoding if needed later
                update_session(sender, "latest_scan_path", save_path)
                if not incoming_msg:
                    incoming_msg = "Image received (QR Scan)"

        # Native WhatsApp location
        latitude = request.form.get('Latitude')
        longitude = request.form.get('Longitude')
        address = request.form.get('Address')
        
        if latitude and longitude and not incoming_msg:
            incoming_msg = f"coordinates: {latitude}, {longitude}"
            if address:
                incoming_msg += f" (Address: {address})"
    
        reply_text, media_url = process_message(sender, incoming_msg, latitude, longitude, address)
        return respond(reply_text, media_url)
    except Exception as e:
        logging.error(f"Webhook error: {e}", exc_info=True)
        return respond("⚠️ Service temporarily unavailable. Please try again later.")


@app.route('/chat', methods=['POST'])
def chat_api():
    data = request.json
    sender = data.get('sender', 'web-user')
    incoming_msg = data.get('message', '').strip()
    
    # Get the host from the request to build a working image URL for the browser
    base_url = f"{request.scheme}://{request.host}"
    
    reply_text, media_url = process_message(sender, incoming_msg, base_url=base_url)
    return {
        "reply": reply_text,
        "media": media_url
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
