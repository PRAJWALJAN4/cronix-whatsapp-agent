# Safecloak WhatsApp Bot Setup ✨

I have created all the backend Python logic required to connect your SafeCloak locker templates to a Twilio WhatsApp bot.

Here is exactly how you can install the dependencies, spin up the server, and link it to your actual Twilio account.

## Step 1: Add your API Keys
1. Open the `.env` file located at `/home/prajwal/Desktop/safeclock/whatsapp_bot/.env`.
2. Delete the placeholder values and paste in your real Twilio API keys.
3. You will also need to add your `NGROK_URL` here eventually (see Step 3).

## Step 2: Start the Python Backend Server
1. Open a new terminal.
2. Navigate to the WhatsApp bot folder:
   ```bash
   cd /home/prajwal/Desktop/safeclock/whatsapp_bot
   ```
3. Run the application:
   ```bash
   source venv/bin/activate
   python app.py
   ```
   *Your bot server is now running on `http://localhost:5000`!*

## Step 3: Expose the server to the internet 🌐
Twilio needs a public URL to send messages to your laptop. We will use `localtunnel` for free, no-account-required tunneling!
1. Open *another* new terminal.
2. Run localtunnel on port 5000:
   ```bash
   npx localtunnel --port 5000 --subdomain safecloak-test
   ```
3. Copy the secure `https://safecloak-test.loca.lt` URL it generates.
4. **Important**: Paste this URL into your `.env` file under `NGROK_URL`. This allows the bot to generate valid Image URLs to send back to WhatsApp.

## Step 4: Hook it up to Twilio
1. Go to your Twilio Console -> WhatsApp Sandbox configuration page.
2. Under "When a message comes in", paste your localtunnel URL with `/whatsapp` at the end of it.
   - Example: `https://safecloak-test.loca.lt/whatsapp`
3. Click **Save**.

## You're Ready to Test! 🚀
Send a WhatsApp message saying `"Hi"` to your Twilio number.
The bot will now sequentially guide you through selecting a language, entering an OTP (`1234`), fetching your current Safecloak Dashboard layouts as live images directly in the chat, selecting pricing hours, handling mock payments, and visually unlocking your selected locker!

> **Note**: Because the bot reads to and saves directly into your `/templates` folder, any locker bookings made from WhatsApp will immediately switch the exact locker to `🔒 Occupied` on your Safecloak web dashboard UI!

## You're Ready to Test! 🚀
Send a WhatsApp message saying `"Hi"` to your Twilio number.
The bot will now sequentially guide you through selecting a language, entering an OTP, fetching your current Safecloak Dashboard layouts as live images directly in the chat, selecting pricing hours, handling mock payments, and visually unlocking your selected locker!

> **Note**: Because the bot reads to and saves directly into your `/templates` folder, any locker bookings made from WhatsApp will immediately switch the exact locker to `🔒 Occupied` on your Safecloak web dashboard UI!
