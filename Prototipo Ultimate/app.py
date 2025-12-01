import os
import threading
import queue
import psutil
import pyautogui
import pyttsx3
import speech_recognition as sr
import webbrowser
import screen_brightness_control as sbc
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from AppOpener import open as open_app
import google.generativeai as genai
from urllib.parse import quote 

# --- CONFIGURAÇÃO ---
app = Flask(__name__)
audio_queue = queue.Queue()
load_dotenv()

# ==========================================
# SUA CHAVE API (Fixa no código)
# ==========================================
MINHA_CHAVE = "AIzaSyBb4ZqAp-KXo682K8hDntZ_Z8GTlt9JxLs"

# --- CLASSE: GERENCIADOR TOTAL DO SISTEMA ---
class SystemController:
    def get_status(self):
        battery = psutil.sensors_battery()
        percent = int(battery.percent) if battery else 100
        return { 
            "cpu": psutil.cpu_percent(), 
            "ram": psutil.virtual_memory().percent,
            "bat": percent
        }

    def ajustar_volume(self, acao):
        if acao == "up": pyautogui.press("volumeup", presses=5)
        elif acao == "down": pyautogui.press("volumedown", presses=5)
        elif acao == "mute": pyautogui.press("volumemute")
        return "Áudio ajustado."

    def ajustar_brilho(self, acao):
        try:
            current = sbc.get_brightness()[0]
            if acao == "up": sbc.set_brightness(min(100, current + 10))
            elif acao == "down": sbc.set_brightness(max(0, current - 10))
            return "Brilho ajustado."
        except: return "Não controlei o brilho (Monitor não suportado)."

    def abrir_programa_universal(self, nome_sujo):
        """Tenta abrir QUALQUER programa instalado no Windows"""
        nome_limpo = nome_sujo.replace("abra", "").replace("o ", "").replace("a ", "").strip()
        
        # Atalhos manuais de sistema
        if "cmd" in nome_limpo or "prompt" in nome_limpo:
            os.popen("start cmd")
            return "Prompt aberto."
        if "config" in nome_limpo:
            os.popen("start ms-settings:")
            return "Configurações abertas."

        # AppOpener tenta achar o programa sozinho
        try:
            print(f">>> Buscando programa: {nome_limpo}")
            open_app(nome_limpo, match_closest=True, throw_error=True)
            return f"Abrindo {nome_limpo}..."
        except:
            return None # Não achou, passa para a próxima tentativa (site)

    def abrir_site_rapido(self, termo):
        """Usa o navegador padrão (Instantâneo)"""
        termo = termo.replace("acesse", "").replace("o site", "").replace("abra", "").strip()
        
        if termo.startswith("o "): termo = termo[2:]
        if termo.startswith("a "): termo = termo[2:]

        if "youtube" in termo: url = "https://youtube.com"
        elif "globo" in termo: url = "https://ge.globo.com"
        elif "whatsapp" in termo: url = "https://web.whatsapp.com"
        elif ".com" in termo or "www" in termo:
            url = termo if termo.startswith("http") else f"https://{termo}"
        else:
            url = f"https://www.google.com/search?q={quote(termo)}"
            
        webbrowser.open(url)
        return f"Acessando {termo}"

# --- CLASSE: VOZ ---
class VoiceManager(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.start()

    def run(self):
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for v in voices:
            if "brazil" in v.name.lower() or "portuguese" in v.name.lower():
                engine.setProperty('voice', v.id)
                break
        engine.setProperty('rate', 170)
        
        while True:
            texto = audio_queue.get()
            if texto:
                try:
                    engine.say(texto)
                    engine.runAndWait()
                except: pass
            audio_queue.task_done()

    def falar(self, texto):
        audio_queue.put(texto)

# --- CLASSE: CÉREBRO (IA Estável) ---
class Brain:
    def __init__(self, api_key):
        self.connected = False
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.chat = self.model.start_chat(history=[])
                self.connected = True
                print(">>> ISA 6.0 Conectada!")
            except Exception as e:
                print(f">>> ERRO CÉREBRO: {e}")
                self.connected = False

    def pensar(self, texto):
        if not self.connected: return "Estou offline."
        try:
            prompt = f"Você é uma assistente pessoal. Responda em 1 frase curta: {texto}"
            response = self.chat.send_message(prompt)
            return response.text
        except: return "Erro na IA."

# --- INICIALIZAÇÃO ---
sys_ctrl = SystemController()
voice_mgr = VoiceManager()
brain = Brain(MINHA_CHAVE)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/status')
def status(): return jsonify(sys_ctrl.get_status())

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    msg = data.get('msg', '').lower()
    resp = ""

    # 1. Hardware
    if "volume" in msg:
        if "aumentar" in msg or "sobe" in msg: resp = sys_ctrl.ajustar_volume("up")
        elif "diminuir" in msg or "baixa" in msg: resp = sys_ctrl.ajustar_volume("down")
        elif "mudo" in msg: resp = sys_ctrl.ajustar_volume("mute")
    
    elif "brilho" in msg:
        if "aumentar" in msg: resp = sys_ctrl.ajustar_brilho("up")
        elif "diminuir" in msg: resp = sys_ctrl.ajustar_brilho("down")

    elif "print" in msg:
        if not os.path.exists('static'): os.makedirs('static')
        pyautogui.screenshot("static/print_last.png")
        resp = "Print salvo."

    # 2. Programa Universal (Tenta abrir App -> Se falhar, tenta Site)
    elif "abra" in msg or "abrir" in msg:
        resp_prog = sys_ctrl.abrir_programa_universal(msg)
        if resp_prog: 
            resp = resp_prog 
        else:
            resp = sys_ctrl.abrir_site_rapido(msg)

    # 3. Site Explícito
    elif "acesse" in msg or "site" in msg:
        resp = sys_ctrl.abrir_site_rapido(msg)

    # 4. IA
    if not resp:
        resp = brain.pensar(msg)

    if len(resp) < 200:
        voice_mgr.falar(resp.replace("*", ""))

    return jsonify({"response": resp})

@app.route('/api/listen', methods=['POST'])
def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            r.adjust_for_ambient_noise(source, duration=0.2)
            audio = r.listen(source, timeout=5)
            text = r.recognize_google(audio, language='pt-BR')
            return jsonify({"success": True, "text": text})
        except: return jsonify({"success": False})

if __name__ == '__main__':
    if not os.path.exists('static'): os.makedirs('static')
    print("--- ISA 6.0: UNLIMITED EDITION ---")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)