# 🤖 Cronix WhatsApp Agent - Safecloak 🔐

![Banner](assets/banner.png)

## 🚀 Overview
**Cronix** is an intelligent AI-powered WhatsApp agent designed to revolutionize how users interact with **Safecloak** luggage lockers. Built with speed, security, and accessibility in mind, Cronix enables users to book, manage, and retrieve their belongings through a seamless multilingual chat interface.

## ✨ Key Features
- **🌐 Multilingual Support**: Communicates in **14 Indian languages** (Hindi, Kannada, Tamil, Telugu, etc.) using Google Gemini AI for natural translations.
- **⚡ OTP Verification**: Secure user authentication via Twilio SMS.
- **🖼️ Dynamic Grid Generation**: Visualizes locker availability in real-time with custom-generated grid images.
- **📍 Geofencing & Location Detection**: Automatically identifies the nearest Safecloak booth based on coordinates or place names.
- **📱 Hybrid Interface**: Includes a WhatsApp bot and a web-based simulator for testing and administration.
- **💳 Integrated Payments**: Seamless flow for payment verification via QR codes.

## 🛠️ Tech Stack
- **Backend**: Python (Flask)
- **AI/ML**: Google Gemini Pro & Flash (Natural Language Processing & Translation)
- **Communication**: Twilio API (WhatsApp Business & SMS)
- **Frontend**: HTML5, Vanilla CSS, JS (Simulator & Template Manager)
- **Server**: Node.js (for Layout Management)
- **Image Processing**: Pillow (Dynamic Grid Generation)

## 📁 Project Structure
```text
.
├── whatsapp_bot/          # Core Python Flask Application
│   ├── app.py             # Main entry point for the WhatsApp bot
│   ├── image_generator.py # Logic for Pillow-based grid visualization
│   ├── static/            # Static assets and generated snapshots
│   └── templates/         # Locker layout definitions (JSON)
├── server.js              # Node.js server for layout management
├── index.html             # Layout manager dashboard
├── assets/                # README assets and images
└── README.md              # Project documentation
```

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+
- Node.js (for layout management)
- Twilio Account (SID, Auth Token, WhatsApp Number)
- Google Gemini API Key
- Ngrok (for local webhook testing)

### 2. Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/PRAJWALJAN4/cronix-whatsapp-agent.git
   cd cronix-whatsapp-agent
   ```
2. Install Python dependencies:
   ```bash
   pip install -r whatsapp_bot/requirements.txt
   ```
3. Install Node dependencies (if any):
   ```bash
   npm install
   ```

### 3. Configuration
Create a `.env` file in the `whatsapp_bot/` directory:
```env
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_SMS_NUMBER=your_sms_number
TWILIO_WHATSAPP_NUMBER=whatsapp:your_whatsapp_number
GEMINI_API_KEY=your_gemini_key
NGROK_URL=your_ngrok_url
```

### 4. Running the App
1. Start the WhatsApp bot:
   ```bash
   python whatsapp_bot/app.py
   ```
2. Start the Layout Manager (Optional):
   ```bash
   node server.js
   ```



## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

---
**Made with ❤️ by Prajwal**
