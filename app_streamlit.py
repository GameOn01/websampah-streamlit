import streamlit as st
import streamlit.components.v1 as components
from collections import Counter
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore
import base64

# === Konfigurasi ===
TEMPLATE_PATH = "index_template.html"

# === Firebase Setup ===
if not firebase_admin._apps:
    cred = credentials.Certificate("websampah-31358-firebase-adminsdk-fbsvc-9be0fc3d2b.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

st.set_page_config(page_title="Sistem Deteksi Sampah", layout="wide")

# === Ambil semua data deteksi dari Firestore ===
def get_detections():
    docs = db.collection("detections").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
    rows = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id   # simpan id dokumen untuk hapus per item
        rows.append(data)
    return rows

# === Hapus semua data ===
def delete_all_detections():
    docs = db.collection("detections").stream()
    for doc in docs:
        doc.reference.delete()

# === Hapus satu data ===
def delete_one_detection(doc_id):
    db.collection("detections").document(doc_id).delete()

# === Build tabel HTML ===
def build_table_rows(data):
    rows_html = ""
    for idx, row in enumerate(data, start=1):
        persen = row.get("confidence", 0) * 100
        if persen >= 80:
            warna = 'bg-success'
        elif persen >= 50:
            warna = 'bg-warning'
        else:
            warna = 'bg-danger'
        img_b64 = row.get("image_base64", "")
        img_tag = f'<img src="data:image/jpeg;base64,{img_b64}" class="detection-img img-thumbnail">' if img_b64 else '<span class="text-muted">Tidak ada gambar</span>'
        rows_html += f"""
        <tr>
          <td>{idx}</td>
          <td>{row.get("timestamp","-")}</td>
          <td>{row.get("class","-")}</td>
          <td>
            <div class="progress">
              <div class="progress-bar {warna}" style="width: {persen:.2f}%">{persen:.2f}%</div>
            </div>
          </td>
          <td>{img_tag}</td>
          <td>
            <form action="" method="post">
              <input type="hidden" name="delete_id" value="{row.get('id')}">
            </form>
          </td>
        </tr>
        """
    return rows_html

# === Build statistik jenis sampah ===
def build_detail_jenis(data):
    jenis_list = [row.get("class","") for row in data]
    counter = Counter(jenis_list)
    if not counter:
        return '<p class="text-muted">Belum ada data</p>'
    html = ""
    for jenis, total in counter.items():
        html += f"""
        <div class="mb-3">
          <div class="d-flex justify-content-between">
            <span>{jenis}</span>
            <span class="badge bg-primary">{total}</span>
          </div>
        </div>
        """
    return html

# === Ambil gambar terbaru dari Firestore (opsional) ===
def get_latest_firestore_image():
    docs = db.collection("detections").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        return data.get("image_base64",""), data.get("class",""), data.get("timestamp","")
    return "", "", ""

# === Layout Web ===
left, right = st.columns([3,1], gap="large")

with left:
    st.markdown("### Data Deteksi Sampah")
    data = get_detections()

    # tombol hapus semua
    if st.button("🗑️ Hapus Semua Data"):
        delete_all_detections()
        st.success("Semua data berhasil dihapus.")
        st.rerun()

    # tampilkan data
    template_html = Path(TEMPLATE_PATH).read_text(encoding="utf-8")
    template_html = template_html.replace("{{TABLE_ROWS}}", build_table_rows(data))
    template_html = template_html.replace("{{TOTAL_DETEKSI}}", str(len(data)))
    template_html = template_html.replace("{{DETAIL_JENIS}}", build_detail_jenis(data))

    components.html(template_html, height=900, scrolling=True)

    # hapus data per item (dropdown + tombol)
    if data:
        options = {f"{d['class']} - {d['timestamp']}": d["id"] for d in data}
        selected = st.selectbox("Pilih data untuk dihapus:", list(options.keys()))
        if st.button("Hapus Data Terpilih"):
            delete_one_detection(options[selected])
            st.success("Data berhasil dihapus.")
            st.rerun()

with right:
    st.markdown("### 📷 Gambar Terbaru")
    img_b64, cls, ts = get_latest_firestore_image()
    if img_b64:
        st.image(base64.b64decode(img_b64), caption=f"{cls} - {ts}", use_container_width=True)
    else:
        st.info("Belum ada gambar di Firestore.")
