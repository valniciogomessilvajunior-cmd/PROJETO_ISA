import speech_recognition as sr
import pyttsx3
from flask import Flask, render_template, jsonify, request

# --- 1. Configuração Inicial ---
app = Flask(__name__)

# Configura o motor de FALA (pyttsx3)
try:
    engine = pyttsx3.init()
    # Tenta definir uma voz em português
    voices = engine.getProperty('voices')
    for voice in voices:
        if "brazil" in voice.name.lower() or "portuguese" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
except Exception as e:
    print(f"Erro ao inicializar motor de voz: {e}")
    engine = None

# Configura o motor de AUDIÇÃO (SpeechRecognition)
recognizer = sr.Recognizer()
microphone = sr.Microphone()

# --- 2. Funções de "Sentidos" (Falar e Ouvir) ---

def falar(texto):
    """ Função que faz o robô falar """
    print(f"Robô falando: {texto}")
    if engine:
        engine.say(texto)
        engine.runAndWait()
    else:
        print("Motor de voz não inicializado.")

def ouvir_comando():
    """ Função que ouve o microfone e retorna o texto """
    with microphone as source:
        print("Robô ouvindo...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source)
    
    try:
        print("Reconhecendo...")
        # Usando a API do Google (requer internet)
        texto = recognizer.recognize_google(audio, language='pt-BR')
        print(f"Usuário disse: {texto}")
        return texto
    except sr.UnknownValueError:
        print("Não entendi o que foi dito.")
        return ""
    except sr.RequestError as e:
        print(f"Erro no serviço de reconhecimento; {e}")
        return ""

def processar_comando_texto(id_botao):
    """ Processa a lógica baseada no TOQUE na tela """
    if id_botao == 'btn-agenda':
        return "A agenda de hoje inclui a Palestra de Robótica às 15h no Laboratório Maker."
    elif id_botao == 'btn-mapa':
        return "O Bloco C fica à sua esquerda, seguindo este corredor."
    elif id_botao == 'btn-faq':
        return "O horário da biblioteca é das 8h às 21h."
    else:
        return "Desculpe, não entendi essa opção."

def processar_comando_voz(texto_voz):
    """ Processa a lógica baseada na VOZ do usuário """
    texto_voz = texto_voz.lower()
    if "agenda" in texto_voz or "eventos" in texto_voz:
        return "A agenda de hoje inclui a Palestra de Robótica às 15h."
    elif "biblioteca" in texto_voz:
        return "O horário da biblioteca é das 8h às 21h."
    elif "mapa" in texto_voz or "onde fica" in texto_voz:
        return "O Bloco C fica à sua esquerda, seguindo este corredor."
    else:
        return "Desculpe, não entendi o comando de voz."


# --- 3. Rotas da API (A ponte entre Interface e Cérebro) ---

@app.route('/')
def index():
    """ Rota principal: Carrega a página index.html """
    return render_template('index.html')

@app.route('/api/get-info', methods=['POST'])
def api_get_info():
    """ API para quando o usuário TOCA num botão """
    button_id = request.json['id']
    resposta_texto = processar_comando_texto(button_id)
    
    # Manda o robô FALAR a resposta
    falar(resposta_texto)
    
    # Retorna o texto para a tela
    return jsonify({'texto_resposta': resposta_texto})

@app.route('/api/ouvir', methods=['POST'])
def api_ouvir():
    """ API para quando o usuário clica no botão de microfone """
    texto_ouvido = ouvir_comando()
    
    if texto_ouvido:
        resposta_texto = processar_comando_voz(texto_ouvido)
    else:
        resposta_texto = "Não consegui te ouvir. Pode repetir?"

    # Manda o robô FALAR a resposta
    falar(resposta_texto)
    
    # Retorna o que foi ouvido e a resposta para a tela
    return jsonify({'texto_resposta': resposta_texto, 'texto_ouvido': texto_ouvido})


# --- 4. Inicialização ---
if __name__ == '__main__':
    print("Iniciando assistente ACI...")
    falar("Sistema iniciado. Aguardando comandos.")
    # 'host=0.0.0.0' torna o servidor visível (útil para o celular)
    # 'debug=True' reinicia o servidor se você alterar o código
    app.run(host='0.0.0.0', port=5000, debug=True)