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

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
audio_queue = queue.Queue()
load_dotenv() # Carrega as variáveis do arquivo .env

# Verifica se a pasta static existe (para salvar prints)
if not os.path.exists('static'):
    os.makedirs('static')

# ==========================================
# CONFIGURAÇÃO DA IA (SEGURA)
# ==========================================
MINHA_CHAVE = os.getenv("GEMINI_API_KEY")

if not MINHA_CHAVE:
    print("⚠️ AVISO: Chave API não encontrada no arquivo .env!")

# --- CLASSE: GERENCIADOR DO SISTEMA ---
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
            # Tenta pegar o brilho do primeiro monitor
            currents = sbc.get_brightness()
            current = currents[0] if currents else 50
            
            if acao == "up": sbc.set_brightness(min(100, current + 10))
            elif acao == "down": sbc.set_brightness(max(0, current - 10))
            return "Brilho ajustado."
        except Exception as e: 
            print(f"Erro brilho: {e}")
            return "Monitor não suporta controle de brilho via software."

    def abrir_programa_universal(self, nome_sujo):
        """Tenta abrir programas ou comandos do sistema"""
        nome_limpo = nome_sujo.lower().replace("abra", "").replace("o ", "").replace("a ", "").strip()
        
        # Comandos manuais
        if "cmd" in nome_limpo or "prompt" in nome_limpo:
            os.popen("start cmd")
            return "Prompt de Comando aberto."
        if "calculadora" in nome_limpo:
            os.popen("calc")
            return "Calculadora aberta."
        if "bloco de notas" in nome_limpo:
            os.popen("notepad")
            return "Bloco de Notas aberto."

        # AppOpener para outros programas
        try:
            print(f">>> Tentando abrir: {nome_limpo}")
            open_app(nome_limpo, match_closest=True, throw_error=True)
            return f"Abrindo {nome_limpo}..."
        except:
            return None # Falhou, vai tentar abrir como site

    def abrir_site_rapido(self, termo):
        """Abre sites no navegador padrão"""
        termo = termo.replace("acesse", "").replace("o site", "").replace("abra", "").strip()
        
        # Remove artigos iniciais
        if termo.startswith("o "): termo = termo[2:]
        if termo.startswith("a "): termo = termo[2:]

        # Mapeamento direto
        if "youtube" in termo: url = "https://youtube.com"
        elif "globo" in termo: url = "https://ge.globo.com"
        elif "whatsapp" in termo: url = "https://web.whatsapp.com"
        elif "google" in termo: url = "https://google.com"
        elif "q-acadêmico" in termo or "qacademico" in termo: url = "https://qacademico.ifce.edu.br/"
        
        # Tratamento de URL genérica
        elif ".com" in termo or "www" in termo:
            url = termo if termo.startswith("http") else f"https://{termo}"
        else:
            url = f"https://www.google.com/search?q={quote(termo)}"
            
        webbrowser.open(url)
        return f"Acessando {termo}"

# --- CLASSE: VOZ (GERENCIADA) ---
class VoiceManager(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True # Mata a thread quando o programa fecha
        self.start()

    def run(self):
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            # Tenta achar voz em PT-BR
            for v in voices:
                if "brazil" in v.name.lower() or "portuguese" in v.name.lower():
                    engine.setProperty('voice', v.id)
                    break
            engine.setProperty('rate', 180) # Velocidade da fala
            
            while True:
                texto = audio_queue.get()
                if texto:
                    try:
                        engine.say(texto)
                        engine.runAndWait()
                    except: pass
                audio_queue.task_done()
        except Exception as e:
            print(f"Erro fatal no motor de voz: {e}")

    def falar(self, texto):
        audio_queue.put(texto)

# --- CLASSE: CÉREBRO (IA) - MELHORADA ---
class Brain:
    def __init__(self, api_key):
        self.connected = False
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Prompt de sistema para dar personalidade
                system_instruction = """
                Você é a ISA 6.0, uma assistente virtual do IFCE Campus Canindé. 
                Seja útil, educada e breve. 
                Se o usuário pedir para gerar texto, música ou poema, faça com criatividade.
                Responda em no máximo 3 frases, a menos que peçam um texto longo.
                """
                
                self.chat = self.model.start_chat(history=[
                    {"role": "user", "parts": "Quem é você e como deve agir?"},
                    {"role": "model", "parts": system_instruction}
                ])
                self.connected = True
                print(">>> SUCESSO: ISA 6.0 Conectada ao Google Gemini!")
            except Exception as e:
                print(f">>> ERRO FATAL DE CONEXÃO: {e}")
                self.connected = False
        else:
            print(">>> AVISO: Nenhuma chave API encontrada no .env")

    def pensar(self, texto):
        if not self.connected: 
            return "Minha conexão com a IA não foi estabelecida. Verifique a chave API no terminal."
        
        try:
            # Envia a mensagem para o Google
            response = self.chat.send_message(texto)
            return response.text
        except Exception as e:
            # ISSO VAI MOSTRAR O ERRO REAL NO SEU VS CODE
            print(f">>> ERRO AO PROCESSAR RESPOSTA: {e}")
            return "Tive um problema técnico. Olhe o terminal do VS Code para ver o erro."

# --- INICIALIZAÇÃO ---
sys_ctrl = SystemController()
voice_mgr = VoiceManager()
brain = Brain(MINHA_CHAVE)

# --- ROTAS FLASK ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/status')
def status(): return jsonify(sys_ctrl.get_status())

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    msg = data.get('msg', '').lower()
    resp = ""

    # 1. Hardware e Sistema
    if "volume" in msg:
        if "aumentar" in msg or "sobe" in msg: resp = sys_ctrl.ajustar_volume("up")
        elif "diminuir" in msg or "baixa" in msg: resp = sys_ctrl.ajustar_volume("down")
        elif "mudo" in msg: resp = sys_ctrl.ajustar_volume("mute")
    
    elif "brilho" in msg or "luz" in msg:
        if "aumentar" in msg or "mais" in msg: resp = sys_ctrl.ajustar_brilho("up")
        elif "diminuir" in msg or "menos" in msg: resp = sys_ctrl.ajustar_brilho("down")

    elif "print" in msg or "captura" in msg:
        caminho = os.path.join("static", "print_last.png")
        pyautogui.screenshot(caminho)
        resp = "Captura de tela salva."

    # 2. Comandos de Abrir (Híbrido: App ou Site)
    elif "abra" in msg or "abrir" in msg:
        resp_prog = sys_ctrl.abrir_programa_universal(msg)
        if resp_prog: 
            resp = resp_prog 
        else:
            resp = sys_ctrl.abrir_site_rapido(msg)

    # 3. Site Direto
    elif "acesse" in msg or "site" in msg:
        resp = sys_ctrl.abrir_site_rapido(msg)

    # 4. Inteligência Artificial (Se nada acima funcionar)
    if not resp:
        resp = brain.pensar(msg)

    # Falar resposta (se não for muito longa)
    if len(resp) < 300:
        voice_mgr.falar(resp.replace("*", ""))

    return jsonify({"response": resp})

@app.route('/api/listen', methods=['POST'])
def listen():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.2)
            # Timeout curto para não travar a interface
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            text = r.recognize_google(audio, language='pt-BR')
            return jsonify({"success": True, "text": text})
    except sr.WaitTimeoutError:
        return jsonify({"success": False, "error": "timeout"})
    except Exception as e:
        print(f"Erro Mic: {e}")
        return jsonify({"success": False, "error": "erro"})

if __name__ == '__main__':
    print("--- ISA 6.0: ULTIMATE EDITION INICIADA ---")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)