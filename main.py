import cv2
import json
import os
import time
import glob
import urllib.request
import threading
from ultralytics import YOLO

# Caminhos absolutos do projeto
DIRETORIO_ATUAL = os.path.dirname(os.path.realpath(__file__))
CAMINHO_BANCO = os.path.join(DIRETORIO_ATUAL, "banco.json")
CAMINHO_STATUS = os.path.join(DIRETORIO_ATUAL, "web", "status.json")
CAMINHO_HISTORICO = os.path.join(DIRETORIO_ATUAL, "web", "historico.json")
CAMINHO_XML = os.path.join(DIRETORIO_ATUAL, "haarcascade_frontalface_default.xml")
PASTA_ALUNOS = os.path.join(DIRETORIO_ATUAL, "alunos")

# Controle de histórico em memória
ULTIMOS_REGISTROS = {}

class WebcamStream:
    """Thread dedicada para leitura de frames da câmera em alta velocidade (Sem LAG)."""
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.grabbed, self.frame = self.cap.read()
        self.stopped = False

    def start(self):
        threading.Thread(target=self.update, args=(), daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            if not self.cap.isOpened():
                break
            grabbed, frame = self.cap.read()
            if grabbed:
                self.grabbed, self.frame = grabbed, frame

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.cap.release()

def garantir_xml_cascade():
    if not os.path.exists(CAMINHO_XML):
        print("📥 Baixando arquivo de detecção de rostos...")
        url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
        try:
            urllib.request.urlretrieve(url, CAMINHO_XML)
            print("✅ Classificador baixado com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao baixar o XML: {e}")

def carregar_banco_json():
    if not os.path.exists(CAMINHO_BANCO):
        dados_padrao = {
            "123456": "Pedro Henrique Terencio Faxina",
            "654321": "Maria Souza"
        }
        with open(CAMINHO_BANCO, "w", encoding="utf-8") as f:
            json.dump(dados_padrao, f, indent=4, ensure_ascii=False)
        return dados_padrao

    with open(CAMINHO_BANCO, "r", encoding="utf-8") as f:
        return json.load(f)

def carregar_fotos_alunos(face_cascade):
    perfis_alunos = {}
    if not os.path.exists(PASTA_ALUNOS):
        os.makedirs(PASTA_ALUNOS)
        return perfis_alunos

    arquivos = glob.glob(os.path.join(PASTA_ALUNOS, "*.[jJ][pP][gG]")) + \
               glob.glob(os.path.join(PASTA_ALUNOS, "*.[pP][nN][gG]"))

    for filepath in arquivos:
        nome_arquivo = os.path.basename(filepath)
        ra = os.path.splitext(nome_arquivo)[0]

        img = cv2.imread(filepath)
        if img is None:
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        rostos = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        if len(rostos) > 0:
            rx, ry, rw, rh = rostos[0]
            rosto_crop = gray[ry:ry+rh, rx:rx+rw]
            rosto_crop = cv2.resize(rosto_crop, (100, 100))
            
            hist = cv2.calcHist([rosto_crop], [0], None, [256], [0, 256])
            cv2.normalize(hist, hist)
            perfis_alunos[ra] = hist

    return perfis_alunos

def identificar_aluno(rosto_gray, perfis_alunos, limiar_similaridade=0.42):
    if not perfis_alunos:
        return None

    rosto_resize = cv2.resize(rosto_gray, (100, 100))
    hist_frame = cv2.calcHist([rosto_resize], [0], None, [256], [0, 256])
    cv2.normalize(hist_frame, hist_frame)

    melhor_ra = None
    maior_score = -1

    for ra, hist_cadastrado in perfis_alunos.items():
        score = cv2.compareHist(hist_cadastrado, hist_frame, cv2.HISTCMP_CORREL)
        if score > maior_score:
            maior_score = score
            melhor_ra = ra

    if maior_score >= limiar_similaridade:
        return melhor_ra
    return None

def celular_pertence_a_pessoa(box_pessoa, box_celular):
    px1, py1, px2, py2 = box_pessoa
    cx1, cy1, cx2, cy2 = box_celular

    ix1 = max(px1, cx1)
    iy1 = max(py1, cy1)
    ix2 = min(px2, cx2)
    iy2 = min(py2, cy2)

    if ix1 >= ix2 or iy1 >= iy2:
        return False

    area_intersecao = (ix2 - ix1) * (iy2 - iy1)
    area_celular = (cx2 - cx1) * (cy2 - cy1)

    return (area_intersecao / area_celular) >= 0.55

def registrar_log_historico(alerta):
    global ULTIMOS_REGISTROS
    ra = alerta["ra"]
    agora = time.time()

    if ra in ULTIMOS_REGISTROS and (agora - ULTIMOS_REGISTROS[ra]) < 10:
        return

    ULTIMOS_REGISTROS[ra] = agora

    historico = []
    if os.path.exists(CAMINHO_HISTORICO):
        try:
            with open(CAMINHO_HISTORICO, "r", encoding="utf-8") as f:
                historico = json.load(f)
        except Exception:
            historico = []

    novo_registro = {
        "id": len(historico) + 1,
        "data": time.strftime("%Y-%m-%d"),
        "hora": time.strftime("%H:%M:%S"),
        "ra": alerta["ra"],
        "nome": alerta["nome"],
        "status": alerta["status"]
    }

    historico.insert(0, novo_registro)

    try:
        with open(CAMINHO_HISTORICO, "w", encoding="utf-8") as f:
            json.dump(historico, f, indent=4, ensure_ascii=False)
        print(f"🚨 INFRAÇÃO REGISTRADA: {alerta['nome']} (RA: {alerta['ra']})")
    except Exception as e:
        print(f"Erro ao salvar historico.json: {e}")

def salvar_status_web(total_alunos, distraidos, alertas):
    pasta_web = os.path.dirname(CAMINHO_STATUS)
    if not os.path.exists(pasta_web):
        os.makedirs(pasta_web)

    foco = 100.0
    if total_alunos > 0:
        foco = round(((total_alunos - distraidos) / total_alunos) * 100, 1)

    dados = {
        "total_alunos": total_alunos,
        "alunos_distraidos": distraidos,
        "foco_turma": foco,
        "alertas": alertas,
        "ultima_atualizacao": time.strftime("%H:%M:%S")
    }

    try:
        with open(CAMINHO_STATUS, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar status.json: {e}")

def main():
    garantir_xml_cascade()

    banco_alunos = carregar_banco_json()
    model = YOLO("yolov8n.pt")
    face_cascade = cv2.CascadeClassifier(CAMINHO_XML)

    perfis_alunos = carregar_fotos_alunos(face_cascade)

    # Inicia a câmera em Thread para alta performance (FPS)
    vs = WebcamStream(0).start()
    time.sleep(1.0) # Espera a câmera aquecer

    prev_time = time.time()

    while True:
        frame = vs.read()
        if frame is None:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Otimização de FPS: O YOLO roda em 480px de resolução interna (muito mais rápido)
        results = model(frame, imgsz=480, conf=0.35, verbose=False)

        pessoas_boxes = []
        celulares_boxes = []

        for r in results:
            for box in r.boxes:
                classe_id = int(box.cls[0])
                coords = list(map(int, box.xyxy[0]))

                if classe_id == 0:        # Pessoa
                    pessoas_boxes.append(coords)
                elif classe_id == 67:     # Celular
                    celulares_boxes.append(coords)

        alunos_cadastrados_detectados = []
        alertas_atuais = []
        distraidos_count = 0

        # Processa apenas as caixas das pessoas encontradas
        for p_box in pessoas_boxes:
            px1, py1, px2, py2 = p_box
            
            # Recorta a região da pessoa para procurar o rosto (Acelera drasticamente o Haar Cascade)
            pessoa_gray_crop = gray[max(0, py1):min(frame.shape[0], py2), max(0, px1):min(frame.shape[1], px2)]
            
            if pessoa_gray_crop.size == 0:
                continue

            rostos = face_cascade.detectMultiScale(pessoa_gray_crop, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))

            ra_identificado = None
            for (rx, ry, rw, rh) in rostos:
                rosto_crop = pessoa_gray_crop[ry:ry+rh, rx:rx+rw]
                ra_identificado = identificar_aluno(rosto_crop, perfis_alunos)
                if ra_identificado:
                    break

            # --- FILTRAGEM: SÓ PROCESSA E DESENHA SE FOR ALUNO CADASTRADO ---
            if ra_identificado and ra_identificado in banco_alunos:
                nome = banco_alunos[ra_identificado]
                label_exibicao = f"{nome} ({ra_identificado})"

                alunos_cadastrados_detectados.append({
                    "ra": ra_identificado,
                    "nome": nome,
                    "box": p_box
                })

                # Desenha o retângulo azul do aluno conhecido
                cv2.rectangle(frame, (px1, py1), (px2, py2), (255, 0, 0), 2)
                cv2.putText(frame, label_exibicao, (px1, py1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)

        # Desenha caixas dos celulares identificados
        for c_box in celulares_boxes:
            cx1, cy1, cx2, cy2 = c_box
            cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (0, 255, 255), 2)

        # Checa se o celular está com um ALUNO CADASTRADO
        for aluno in alunos_cadastrados_detectados:
            usando_celular = False
            for cel_box in celulares_boxes:
                if celular_pertence_a_pessoa(aluno["box"], cel_box):
                    usando_celular = True
                    break

            if usando_celular:
                distraidos_count += 1
                alerta = {
                    "ra": aluno["ra"],
                    "nome": aluno["nome"],
                    "status": "Usando Celular",
                    "hora": time.strftime("%H:%M:%S")
                }
                alertas_atuais.append(alerta)
                
                # Grava no historico.json
                registrar_log_historico(alerta)

                # Destaque de Alerta Vermelho
                px1, py1, px2, py2 = aluno["box"]
                cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 0, 255), 3)
                cv2.putText(frame, f"ALERTA: CELULAR!", (px1, py1 - 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

        # Atualiza a Dashboard Web com a contagem apenas dos cadastrados
        salvar_status_web(len(alunos_cadastrados_detectados), distraidos_count, alertas_atuais)

        # Cálculo de FPS real na tela
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
        prev_time = curr_time
        cv2.putText(frame, f"FPS: {int(fps)}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Monitoramento de Sala de Aula", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    vs.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()