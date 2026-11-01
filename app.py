"""
Tampilan Utama (Streamlit UI) - Puzzle World
Mengimpor modul:
- puzzle_generator.py (Tahap 1: Pembuat potongan teka-teki)
- puzzle_solver.py    (Tahap 2: Penyusun kembali potongan menjadi citra utuh)
"""
import io
import os
import sys
import glob
import time
import subprocess
import numpy as np
import streamlit as st
from PIL import Image
from streamlit.runtime.scriptrunner import get_script_run_ctx

# Jika dijalankan langsung dengan tombol Run (python app.py), otomatis alihkan ke `streamlit run`
if __name__ == "__main__" and get_script_run_ctx(suppress_warning=True) is None:
    subprocess.run([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)])
    sys.exit(0)

from puzzle_generator import buat_puzzle
from puzzle_solver import solve_puzzle

OUT_DIR = "output"
PIECES_DIR = os.path.join(OUT_DIR, "pieces")

st.set_page_config(page_title="Puzzle World - PCD", layout="wide")
S = st.session_state


# ==============================================================================
# FUNGSI AKSI & STATE PERMAINAN
# ==============================================================================
def jalankan_generator(img_pil, M, margin_rasio, rotasi_acak, acak_urutan):
    """Memanggil modul puzzle_generator dan menyimpan state ke aplikasi."""
    arr, frame, pot_list, kunci = buat_puzzle(
        img_pil=img_pil,
        M=M,
        margin_rasio=margin_rasio,
        rotasi_acak=rotasi_acak,
        acak_urutan=acak_urutan,
        out_dir=OUT_DIR
    )
    S.asli = arr
    S.frame = frame
    S.pot = pot_list
    S.kunci = kunci
    S.solver_result = None
    reset_papan()


def reset_papan():
    """Mengosongkan papan permainan tanpa memotong ulang gambar."""
    S.placed = {}
    S.urot = {i: 0 for i in range(len(S.pot))}
    S.sel = None
    S.hasil = None


def pilih(i):
    S.sel = i


def putar(i):
    S.urot[i] = (S.urot[i] + 1) % 4


def taruh(slot):
    if S.sel is not None:
        S.placed[slot] = S.sel
        S.sel = None
        S.hasil = None


def ambil(slot):
    S.sel = S.placed.pop(slot)
    S.hasil = None


def tampil(i):
    return np.rot90(S.pot[i], S.urot[i])


def benar(slot, i):
    """Pengecekan permainan manual: hanya mengecek kebenaran posisi slot."""
    M = S.kunci["M"]
    q = S.kunci["potongan"][i]
    return q["baris_asli"] * M + q["kolom_asli"] == slot


def cek():
    S.hasil = (sum(benar(s, i) for s, i in S.placed.items()), len(S.placed))


def isi_papan_otomatis_solver():
    """Menjalankan modul puzzle_solver dan langsung menaruh hasilnya ke papan permainan manual."""
    _, board, _, _ = solve_puzzle(S.frame, S.pot)
    M = S.kunci["M"]
    S.placed = {}
    for (r, c), (i, k) in board.items():
        slot = r * M + c
        S.placed[slot] = i
        S.urot[i] = k
    S.sel = None
    cek()


def jawaban():
    """Susun ulang dari potongan + kunci jawaban (untuk tombol petunjuk)."""
    h = S.frame.copy()
    for q, p in zip(S.kunci["potongan"], S.pot):
        x0, y0, x1, y1 = q["posisi_di_bingkai_xyxy"]
        h[y0:y1, x0:x1] = np.rot90(p, -(q["rotasi_derajat"] // 90))
    return h


# ==============================================================================
# SIDEBAR: PARAMETER GENERATOR
# ==============================================================================
with st.sidebar:
    st.title("🧩 Puzzle World")
    st.caption("Tugas Besar Pengolahan Citra Digital")

    st.subheader("1. Unggah Gambar (Generator)")
    uploaded_file = st.file_uploader(
        "Pilih citra utuh (RGB / Grayscale)",
        type=["png", "jpg", "jpeg", "bmp", "webp"],
        key="gen_uploader"
    )

    st.subheader("2. Parameter Generator")
    M_input = st.slider("Ukuran Grid (M × M)", min_value=2, max_value=8, value=4)
    margin_input = st.slider("Rasio Margin Bingkai", min_value=0.01, max_value=0.25, value=0.07, step=0.01)
    rotasi_input = st.checkbox("Rotasi Acak (0°/90°/180°/270°)", value=True)
    acak_input = st.checkbox("Acak Urutan Potongan", value=True)

    tombol_acak_ulang = st.button(
        "🔀 Buat / Acak Ulang Puzzle",
        disabled=uploaded_file is None,
        width="stretch"
    )

    if "kunci" in S:
        st.divider()
        st.subheader("3. Kontrol Papan Permainan")
        st.button("🤖 Susun Otomatis di Papan", on_click=isi_papan_otomatis_solver, width="stretch")
        st.button("🧹 Bersihkan Papan", on_click=reset_papan, width="stretch")
        petunjuk = st.toggle("Tampilkan jawaban (petunjuk)")
    else:
        petunjuk = False


# Jalankan Generator HANYA saat gambar/parameter berubah atau tombol acak ulang diklik
if uploaded_file is not None:
    config_sekarang = (uploaded_file.name, uploaded_file.size, M_input, margin_input, rotasi_input, acak_input)
    if S.get("config_aktif") != config_sekarang or tombol_acak_ulang:
        img_in = Image.open(uploaded_file)
        jalankan_generator(img_in, M_input, margin_input, rotasi_input, acak_input)
        S.config_aktif = config_sekarang


# ==============================================================================
# LAYAR UTAMA: 2 TAB (TAHAP 1: GENERATOR & PERMAINAN | TAHAP 2: PUZZLE SOLVER)
# ==============================================================================
st.header("🧩 Puzzle World — Generator & Solver (PCD)")

tab_gen, tab_solver = st.tabs([
    "🛠️ Tahap 1: Puzzle Generator & Permainan Manual",
    "🤖 Tahap 2: Puzzle Solver Otomatis (1 Bingkai + N Potongan)"
])

# ------------------------------------------------------------------------------
# TAB 1: PUZZLE GENERATOR & PERMAINAN MANUAL
# ------------------------------------------------------------------------------
with tab_gen:
    if "kunci" not in S:
        st.info(
            "👈 Silakan unggah gambar utuh pada sidebar di sebelah kiri untuk membuat bingkai & potongan puzzle, "
            "atau buka tab **🤖 Tahap 2: Puzzle Solver Otomatis** jika Anda ingin langsung mengunggah 1 bingkai dan N potongan."
        )
    else:
        kunci = S.kunci
        M = kunci["M"]
        N = M * M
        W, H = kunci["ukuran_asli"]

        st.caption(
            f"Ukuran citra: **{W} × {H} px** | Mode: **{kunci.get('mode', 'RGB')}** | "
            f"Grid: **{M} × {M} ({N} potongan)** | Keluaran disimpan di: `{OUT_DIR}/`"
        )

        kiri, kanan = st.columns([1, 1.3])

        with kiri:
            st.subheader("Bingkai")
            st.image(S.frame, width="stretch")
            if petunjuk:
                st.image(jawaban(), caption="Susunan yang benar", width="stretch")

            st.subheader("Potongan tersedia")
            sisa = [i for i in range(N) if i not in S.placed.values()]
            if not sisa:
                st.caption("Semua potongan sudah ditaruh di papan.")
            kol = st.columns(min(4, max(1, len(sisa))))
            for n, i in enumerate(sisa):
                with kol[n % len(kol)]:
                    st.image(
                        tampil(i),
                        caption=("✅ " if S.sel == i else "") + kunci["potongan"][i]["file"],
                        width="stretch"
                    )
                    st.button("Pilih", key=f"p{i}", on_click=pilih, args=(i,), width="stretch")
                    if S.sel == i:
                        st.button("↺ Putar", key=f"r{i}", on_click=putar, args=(i,), width="stretch")

        with kanan:
            st.subheader("Papan puzzle")
            if S.sel is not None:
                st.info(f"**{kunci['potongan'][S.sel]['file']}** dipilih. Klik **Taruh** pada slot tujuan.")

            area = kunci["area_bingkai"]
            slot_h = max(1, (area["y1"] - area["y0"]) // M)
            slot_w = max(1, (area["x1"] - area["x0"]) // M)
            kosong = np.full((slot_h, slot_w, 3), 235, np.uint8)

            for r in range(M):
                cols = st.columns(M)
                for c in range(M):
                    slot = r * M + c
                    with cols[c]:
                        if slot in S.placed:
                            i = S.placed[slot]
                            st.image(tampil(i), width="stretch")
                            if S.hasil is not None:
                                st.caption("✅" if benar(slot, i) else "❌")
                            st.button("Ambil", key=f"a{slot}", on_click=ambil, args=(slot,), width="stretch")
                        else:
                            st.image(kosong, caption=f"slot {slot + 1}", width="stretch")
                            st.button(
                                "Taruh",
                                key=f"t{slot}",
                                on_click=taruh,
                                args=(slot,),
                                disabled=S.sel is None,
                                width="stretch"
                            )

            st.button("✔️ Cek jawaban (Posisi)", on_click=cek, disabled=not S.placed, width="stretch")
            if S.hasil:
                n, total = S.hasil
                if n == N:
                    st.success("🎉 Puzzle selesai, semua potongan berada di posisi yang benar!")
                    st.balloons()
                else:
                    st.warning(f"{n} dari {total} potongan yang ditaruh sudah benar posisinya (target {N}).")


# ------------------------------------------------------------------------------
# TAB 2: PUZZLE SOLVER OTOMATIS (INPUT: 1 CITRA BINGKAI + N POTONGAN CITRA)
# ------------------------------------------------------------------------------
with tab_solver:
    st.subheader("Tahap 2: Puzzle Solver Otomatis")
    st.markdown(
        "Modul ini menerima **1 citra bingkai** dan **N potongan citra** (tanpa membaca `kunci_jawaban.json`), "
        "mendeteksi area kosong pada bingkai, lalu merangkai kembali seluruh potongan beserta rotasinya "
        "menggunakan analisis kontinuitas piksel dan gradien tepi (PCD)."
    )

    sumber_solver = st.radio(
        "Pilih Sumber Masukan Solver:",
        [
            "Gunakan hasil Generator saat ini (1 Bingkai + N Potongan aktif)",
            "Unggah manual 1 Citra Bingkai + N Potongan Citra dari komputer"
        ],
        horizontal=True
    )

    frame_solver = None
    pieces_solver = []
    nama_pieces_solver = []

    if sumber_solver.startswith("Gunakan hasil Generator"):
        if "frame" in S and "pot" in S:
            frame_solver = S.frame
            pieces_solver = S.pot
            nama_pieces_solver = [q["file"] for q in S.kunci["potongan"]]
            st.success(f"Siap menyusun **1 citra bingkai** dan **{len(pieces_solver)} potongan citra** dari hasil Generator.")
        elif os.path.exists(os.path.join(OUT_DIR, "frame.png")) and os.path.exists(PIECES_DIR):
            piece_paths = sorted(glob.glob(os.path.join(PIECES_DIR, "piece_*.png")))
            if piece_paths:
                frame_solver = np.array(Image.open(os.path.join(OUT_DIR, "frame.png")))
                pieces_solver = [np.array(Image.open(p)) for p in piece_paths]
                nama_pieces_solver = [os.path.basename(p) for p in piece_paths]
                st.success(f"Memuat **1 citra bingkai** dan **{len(pieces_solver)} potongan citra** dari folder `{OUT_DIR}/`.")
            else:
                st.warning("Belum ada potongan citra di folder `output/pieces/`. Silakan buat puzzle di Tab 1 atau pilih unggah manual.")
        else:
            st.warning("Belum ada puzzle yang dibuat. Silakan unggah gambar di Sidebar atau pilih opsi unggah manual di atas.")
    else:
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            up_frame = st.file_uploader(
                "1. Unggah 1 Citra Bingkai (frame.png)",
                type=["png", "jpg", "jpeg", "bmp", "webp"],
                key="solver_frame_up"
            )
        with col_up2:
            up_pieces = st.file_uploader(
                "2. Unggah N Potongan Citra (pilih semua file piece_XX.png)",
                type=["png", "jpg", "jpeg", "bmp", "webp"],
                accept_multiple_files=True,
                key="solver_pieces_up"
            )

        if up_frame is not None and up_pieces:
            img_f = Image.open(up_frame)
            if img_f.mode not in ("RGB", "L"):
                img_f = img_f.convert("RGB")
            frame_solver = np.array(img_f)

            up_pieces_sorted = sorted(up_pieces, key=lambda f: f.name)
            for pf in up_pieces_sorted:
                im_p = Image.open(pf)
                if im_p.mode not in ("RGB", "L"):
                    im_p = im_p.convert("RGB")
                pieces_solver.append(np.array(im_p))
                nama_pieces_solver.append(pf.name)

            st.info(f"Masukan diterima: **1 Bingkai** (`{up_frame.name}`) dan **{len(pieces_solver)} Potongan Citra**.")

    if frame_solver is not None and len(pieces_solver) > 0:
        with st.expander("👁️ Lihat Masukan (1 Citra Bingkai & N Potongan)", expanded=False):
            c_in1, c_in2 = st.columns([1, 1.5])
            with c_in1:
                st.image(frame_solver, caption="Citra Bingkai Masukan", width="stretch")
            with c_in2:
                n_p = len(pieces_solver)
                cols_p = st.columns(min(6, max(1, n_p)))
                for idx_p, (im_p, nm_p) in enumerate(zip(pieces_solver, nama_pieces_solver)):
                    with cols_p[idx_p % len(cols_p)]:
                        st.image(im_p, caption=nm_p, width="stretch")

        if st.button("🚀 Jalankan Puzzle Solver (Rangkai Citra Utuh)", type="primary", width="stretch"):
            try:
                t_mulai = time.time()
                with st.spinner("Menganalisis tepi piksel & merangkai potongan puzzle..."):
                    hasil_citra, board_sol, detail_sol, area_sol = solve_puzzle(frame_solver, pieces_solver)
                durasi = time.time() - t_mulai

                os.makedirs(OUT_DIR, exist_ok=True)
                solved_path = os.path.join(OUT_DIR, "solved.png")
                Image.fromarray(hasil_citra).save(solved_path)

                S.solver_result = {
                    "frame": frame_solver,
                    "hasil": hasil_citra,
                    "detail": detail_sol,
                    "area": area_sol,
                    "nama_pieces": nama_pieces_solver,
                    "durasi": durasi,
                    "M": int(round(np.sqrt(len(pieces_solver))))
                }
            except Exception as e:
                st.error(f"Gagal menyusun puzzle: {e}")

    if S.get("solver_result") is not None:
        res = S.solver_result
        st.divider()
        st.success(
            f"✅ Puzzle berhasil dirangkai menjadi citra utuh dalam **{res['durasi']:.2f} detik**! "
            f"(Area bingkai terdeteksi: `x={res['area']['x0']}..{res['area']['x1']}`, `y={res['area']['y0']}..{res['area']['y1']}`)"
        )

        col_out1, col_out2 = st.columns(2)
        with col_out1:
            st.subheader("Input: Citra Bingkai")
            st.image(res["frame"], caption="1 Citra Bingkai + Area Kosong", width="stretch")
        with col_out2:
            st.subheader("Luaran: Citra Utuh Hasil Rangkaian")
            st.image(res["hasil"], caption="Citra Utuh Hasil Puzzle Solver (output/solved.png)", width="stretch")

        buf = io.BytesIO()
        Image.fromarray(res["hasil"]).save(buf, format="PNG")
        st.download_button(
            label="💾 Unduh Citra Utuh (solved.png)",
            data=buf.getvalue(),
            file_name="solved.png",
            mime="image/png",
            width="stretch"
        )

        with st.expander("📋 Detail Penempatan & Rotasi Setiap Slot", expanded=False):
            M_sol = res["M"]
            for r in range(M_sol):
                cols_d = st.columns(M_sol)
                for c in range(M_sol):
                    slot_idx = r * M_sol + c
                    d = res["detail"][slot_idx]
                    nm = res["nama_pieces"][d["idx_potongan"]]
                    with cols_d[c]:
                        st.markdown(
                            f"**Slot {slot_idx + 1}** `(Baris {r}, Kolom {c})`  \n"
                            f"📄 `{nm}`  \n"
                            f"🔄 Putar balik: `{d['derajat_putar']}°` CCW"
                        )
