import streamlit as st
import sqlite3, os, base64
from pathlib import Path
import streamlit.components.v1 as components
from collections import Counter

DB_PATH = "database.db"
UPLOAD_FOLDER = "static/uploads"
TEMPLATE_PATH = "index_template.html"

st.set_page_config(page_title="Sistem Deteksi Sampah", layout="wide")

def get_detections():
    if not Path(DB_PATH).exists():
        return []
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT id, jenis_sampah, confidence, gambar_path,
                   strftime('%d/%m/%Y %H:%M', waktu_deteksi) as waktu_format
            FROM deteksi_sampah
            ORDER BY waktu_deteksi DESC
            """
        ).fetchall()
    return rows

def delete_all():
    if Path(DB_PATH).exists():
        with sqlite3.connect(DB_PATH) as conn:
            imgs = conn.execute("SELECT gambar_path FROM deteksi_sampah").fetchall()
            for (g,) in imgs:
                p = Path(UPLOAD_FOLDER) / g
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass
            conn.execute("DELETE FROM deteksi_sampah")
            conn.commit()

def img_to_base64(path):
    p = Path(path)
    if not p.exists():
        return ""
    try:
        data = p.read_bytes()
        return base64.b64encode(data).decode("utf-8")
    except Exception:
        return ""

def build_table_rows(data):
    rows_html = ""
    for idx, (id_, jenis, conf, gambar, waktu) in enumerate(data, start=1):
        persen = conf * 100.0 if conf is not None else 0.0
        if persen >= 80:
            warna = 'bg-success'
        elif persen >= 50:
            warna = 'bg-warning'
        else:
            warna = 'bg-danger'
        img_b64 = img_to_base64(os.path.join(UPLOAD_FOLDER, gambar)) if gambar else ""
        img_tag = f'<img src="data:image/jpeg;base64,{img_b64}" class="detection-img img-thumbnail">' if img_b64 else '<span class="text-muted">Tidak ada gambar</span>'
        rows_html += f"""
        <tr>
          <td>{idx}</td>
          <td>{waktu}</td>
          <td>{jenis}</td>
          <td>
            <div class="progress">
              <div class="progress-bar {warna}" style="width: {persen:.2f}%">{persen:.2f}%</div>
            </div>
          </td>
          <td>{img_tag}</td>
        </tr>
        """
    return rows_html

def build_detail_jenis(data):
    jenis_list = [row[1] for row in data]
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

left, right = st.columns([3,1], gap="large")
with left:
    st.markdown("### Data Deteksi Sampah")
    if st.button("🗑️ Hapus Semua Data", use_container_width=True):
        delete_all()
        st.success("Semua data berhasil dihapus.")
        st.experimental_rerun()

data = get_detections()
template_html = Path(TEMPLATE_PATH).read_text(encoding="utf-8")
template_html = template_html.replace("{{TABLE_ROWS}}", build_table_rows(data))
template_html = template_html.replace("{{TOTAL_DETEKSI}}", str(len(data)))
template_html = template_html.replace("{{DETAIL_JENIS}}", build_detail_jenis(data))

components.html(template_html, height=900, scrolling=True)
