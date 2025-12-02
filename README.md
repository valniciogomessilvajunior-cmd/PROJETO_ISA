# 🤖 PROJETO ISA (Assistente Virtual - IFCE)
Versão Atual: ISA 6.0 (Ultimate Edition)

Desenvolvido em: LabMaker - IFCE Campus Canindé

Este repositório contém o código-fonte e a evolução do projeto ISA, uma assistente virtual desenvolvida em Python. O projeto explora diferentes interfaces (Desktop/Tkinter e Web/Flask) e integrações com Inteligência Artificial (Google Gemini), automação de sistema e comandos de voz.

## 📂 Estrutura do Projeto
O projeto está dividido em três fases principais de desenvolvimento:

### 1. 🚀 Prototipo Ultimate (Versão Final/Atual)
A versão mais completa e estável (ISA 6.0).

Interface: Web App moderno (Flask) com dashboard escuro (Dark Mode).

Monitoramento: Exibe uso de CPU, RAM e Bateria em tempo real.

IA: Integração nativa com Google Gemini 1.5 Flash para conversação natural.

Controle de Hardware: Ajuste de volume, brilho da tela e capturas de tela (print).

Automação: Abre programas (Calculadora, Bloco de Notas) e sites (YouTube, Q-Acadêmico, SUAP).

Interação: Suporta comandos por voz e texto.

### 2. 🧪 Prototipo 02
Uma versão intermediária focada em interface web simplificada.

Interface: Web (Flask) estilo "Totem/Quiosque".

Foco: Botões grandes para acessibilidade (Agenda, Mapa, FAQ).

Funcionalidade: Respostas predefinidas e motor de voz básico.

### 3. 🖥️ Prototipo 01
A primeira versão desktop.

Interface: GUI via Tkinter.

Funcionalidade: Automação via Selenium (controle de navegador) e comandos básicos de sistema.

## 🛠️ Tecnologias Utilizadas
O projeto foi construído utilizando Python e as seguintes bibliotecas principais:

Core/Web: Flask, threading

Inteligência Artificial: google-generativeai (Gemini API)

Voz (STT/TTS): SpeechRecognition, pyttsx3

Automação & Sistema: * psutil (Monitoramento de hardware)

pyautogui (Teclado/Mouse/Screenshots)

screen_brightness_control (Controle de brilho)

AppOpener (Abrir aplicações)

Frontend: HTML5, CSS3, JavaScript (Fetch API)

## ⚙️ Instalação e Configuração
Pré-requisitos
Python 3.x instalado.

Uma chave de API do Google Gemini (Google AI Studio).

1. Clonar o repositório
Bash

git clone https://github.com/seu-usuario/projeto_isa.git
cd projeto_isa
2. Instalar dependências
Navegue até a pasta da versão que deseja executar (recomenda-se a Prototipo Ultimate) e instale as bibliotecas:

Bash

pip install flask google-generativeai speechrecognition pyttsx3 psutil pyautogui screen_brightness_control AppOpener python-dotenv
(Nota: Para o reconhecimento de voz funcionar, pode ser necessário instalar o pyaudio separadamente).

3. Configurar Variáveis de Ambiente
Crie um arquivo .env na pasta Prototipo Ultimate com a sua chave de API:

Snippet de código

GEMINI_API_KEY="SUA_CHAVE_API_AQUI"
4. Executar
Bash

python app.py
Acesse no navegador: http://localhost:5000

## 🎮 Funcionalidades (ISA 6.0 Ultimate)
Comandos de Sistema
"Aumentar/Diminuir volume": Controla o áudio do PC.

"Aumentar/Diminuir brilho": Controla o brilho do monitor principal.

"Tirar print": Salva uma captura de tela na pasta static.

"Abrir [programa]": Abre calculadora, bloco de notas, CMD, etc.

Navegação
"Acesse o Q-Acadêmico": Abre o portal do aluno.

"Abrir YouTube/Globo": Navegação direta.

Inteligência Artificial
Qualquer pergunta que não seja um comando de sistema será processada pelo Google Gemini, permitindo conversas naturais, geração de textos criativos e tira-dúvidas.

## 📝 Autor
Desenvolvido por Valnicio Gomes Silva Junior (conforme estrutura de pastas). Projeto vinculado ao IFCE Campus Canindé.

## ⚠️ Aviso de Segurança: Este repositório continha arquivos .env e config.json com chaves de API expostas no histórico. Recomenda-se revogar as chaves antigas e nunca comitar arquivos de credenciais em repositórios públicos.
