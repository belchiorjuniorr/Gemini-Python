from flask import (
    Flask,
    render_template,
    request,
    Response,
    stream_with_context,
    jsonify,
)
from werkzeug.utils import secure_filename
from PIL import Image
import io

import google.generativeai as genai

# WARNING: Do not share code with you API key hard coded in it.
# Get your Gemini API key from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY="AIzaSyDdLsOpU2AAgN0Lrt7BDrsR115Ew5TIbnE"
genai.configure(api_key=GOOGLE_API_KEY)

# The rate limits are low on this model, so you might need to switch to `gemini-pro`
model = genai.GenerativeModel('gemini-1.5-pro-latest')

app = Flask(__name__)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

chat_session = model.start_chat(history=[])
next_message = ""
next_image = ""

def allowed_file(filename):
    """Retorna-se um nome de arquivo for suportado por sua extensão"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/upload", methods=["POST"])
def upload_file():
    """Pega um arquivo, verifica se é válido e salva para a próxima solicitação à API"""
    global next_image

    if "file" not in request.files:
        return jsonify(success=False, message="No file part")

    file = request.files["file"]

    if file.filename == "":
        return jsonify(success=False, message="Nenhum arquivo selecionado")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        # Read the file stream into a BytesIO object
        file_stream = io.BytesIO(file.read())
        file_stream.seek(0)
        next_image = Image.open(file_stream)

        return jsonify(
            success=True,
            message="Arquivo enviado com sucesso e adicionado à conversa",
            filename=filename,
        )
    return jsonify(success=False, message="Tipo de arquivo não permitido")

@app.route("/", methods=["GET"])
def index():
    """Renderiza a página inicial principal do aplicativo"""
    return render_template("index.html", chat_history=chat_session.history)

@app.route("/chat", methods=["POST"])
def chat():
    """Recebe a mensagem que o usuário deseja enviar para a API Gemini e a salva"""
    global next_message
    next_message = request.json["message"]
    print(chat_session.history)

    return jsonify(success=True)

@app.route("/stream", methods=["GET"])
def stream():
    """Transmite a resposta do serviço para solicitações multimodais e de texto simples"""
    def generate():
        global next_message
        global next_image
        assistant_response_content = ""

        if next_image != "":
            # This only works with `gemini-1.5-pro-latest`
            response = chat_session.send_message([next_message, next_image], stream=True)
            next_image = ""
        else:
            response = chat_session.send_message(next_message, stream=True)
            next_message = ""
        
        for chunk in response:
            assistant_response_content += chunk.text
            yield f"data: {chunk.text}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")
