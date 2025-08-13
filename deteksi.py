import cv2
import os
import sqlite3
import uuid
from datetime import datetime
from ultralytics import YOLO

# === Konfigurasi ===
DB_PATH = "database.db"
UPLOAD_FOLDER = "static/uploads"
MODEL_PATH = "best.pt"  # ganti sesuai model kamu
CONFIDENCE_DEFAULT = 0.5
CONFIDENCE_BOTOL_KACA = 0.3  # khusus botol kaca

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deteksi_sampah (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jenis_sampah TEXT,
                confidence REAL,
                gambar_path TEXT,
                waktu_deteksi TEXT
            )
        """)
        conn.commit()

def simpan_deteksi(jenis_sampah, confidence, gambar_filename):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO deteksi_sampah (jenis_sampah, confidence, gambar_path, waktu_deteksi)
            VALUES (?, ?, ?, ?)
        """, (jenis_sampah, confidence, gambar_filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

def deteksi_video(source=0):
    model = YOLO(MODEL_PATH)
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print("Tidak bisa membuka sumber video.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, stream=True)

        ada_temuan = False
        label_tertinggi = None
        conf_tertinggi = 0.0

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label = model.names[cls_id]

                threshold = CONFIDENCE_BOTOL_KACA if label.lower() == "botol kaca" else CONFIDENCE_DEFAULT
                if conf < threshold:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{label} {conf*100:.1f}%",
                            (x1, max(0, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                ada_temuan = True
                if conf > conf_tertinggi:
                    conf_tertinggi = conf
                    label_tertinggi = label

        if ada_temuan and label_tertinggi is not None:
            filename = f"{uuid.uuid4().hex}.jpg"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            cv2.imwrite(filepath, frame)
            simpan_deteksi(label_tertinggi, conf_tertinggi, filename)
            print(f"Deteksi: {label_tertinggi} ({conf_tertinggi*100:.2f}%) -> {filename}")

        cv2.imshow("Deteksi Sampah (tekan 'q' untuk keluar)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    init_db()
    deteksi_video(0)
