from pathlib import Path
import json
import re
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

st.set_page_config(
    page_title="Piyasa İstihbaratı",
    page_icon="📈",
    layout="wide",
)

# --- UI translations ---
CATEGORY_TR = {
    "earnings": "Bilanço",
    "dc_capex": "Veri Merkezi / AI Yatırımı",
    "guidance": "Şirket Beklentisi",
    "contract": "Sözleşme",
    "macro": "Makro",
    "official": "Resmî Açıklama",
    "technical": "Teknik Analiz",
    "analyst": "Analist Yorumu",
    "dividend": "Temettü",
    "rumor": "Söylenti",
    "options": "Opsiyon",
    "deliveries": "Teslimatlar",
    "hype": "Abartı / Hype",
    "ad": "Reklam",
    "ticker_spam": "Hisse Etiketi Spamı",
    "noise": "Değersiz / Çöp",
    "other": "Diğer",
    "prefilter": "Ön Filtre",
}

DIRECTION_TR = {
    "bullish": "Yükseliş",
    "bearish": "Düşüş",
    "neutral": "Nötr",
}


UI = {
    "tr": {
        "title": "Piyasa İstihbaratı",
        "caption": "Yerel kontrol merkezi — sinyaller, olaylar, kaynaklar, tahminler ve benchmark kalitesi",
        "tabs": ["🏠 Genel Bakış","📰 Olaylar","🤖 AI Kararları","🏆 Kaynaklar","📈 Tahminler","📊 Benchmark","⚙️ İşlem Akışı"],
        "messages": "Mesaj",
        "precision": "Kesinlik",
        "recall": "Yakalama",
        "direction": "Yön Doğruluğu",
        "elapsed": "Süre",
        "pipeline": "İşlem akışı özeti",
        "recent_events": "Son olay akışı",
        "dataset": "Veri seti özeti",
        "valuable": "Değerli",
        "discard": "Değersiz",
        "sources": "kaynak",
        "message_word": "mesaj",
        "event_explorer": "Olay inceleme",
        "source_messages": "Kaynak mesajları",
        "ai_decisions": "AI kararları",
        "source_intel": "Kaynak güvenilirliği",
        "pred_perf": "Tahmin performansı",
        "benchmark": "Benchmark inceleme",
        "pipeline_details": "İşlem akışı ayrıntıları",
    },
    "en": {
        "title": "Market Intelligence",
        "caption": "Local control center — signals, events, sources, predictions and benchmark quality",
        "tabs": ["🏠 Overview","📰 Events","🤖 AI Decisions","🏆 Sources","📈 Predictions","📊 Benchmark","⚙️ Pipeline"],
        "messages": "Messages",
        "precision": "Precision",
        "recall": "Recall",
        "direction": "Direction",
        "elapsed": "Elapsed",
        "pipeline": "Pipeline snapshot",
        "recent_events": "Recent event feed",
        "dataset": "Dataset pulse",
        "valuable": "Valuable",
        "discard": "Discard",
        "sources": "sources",
        "message_word": "messages",
        "event_explorer": "Event explorer",
        "source_messages": "Source messages",
        "ai_decisions": "AI decisions",
        "source_intel": "Source intelligence",
        "pred_perf": "Prediction performance",
        "benchmark": "Benchmark explorer",
        "pipeline_details": "Pipeline internals",
    }
}


def tr_category(value):
    if value is None:
        return "—"
    return CATEGORY_TR.get(str(value).lower(), str(value))

def tr_direction(value):
    if value is None:
        return "—"
    return DIRECTION_TR.get(str(value).lower(), str(value))



def event_summary(text, ticker=None, category=None, direction=None, lang="tr"):
    raw = str(text or "").strip()
    low = raw.lower()

    if lang == "en":
        return raw

    # Full Turkish rewrites for benchmark/event patterns.
    patterns = [
        (
            "hyperscaler ai capex",
            f"{ticker or 'Bu hisse'} için büyük bulut sağlayıcılarının AI altyapı yatırımı beklentileri yükseldi; veri merkezi gelir tahminlerinde yukarı yönlü potansiyel oluşuyor."
        ),
        (
            "distributor checks indicate stronger mi-series accelerator demand",
            f"{ticker or 'Bu hisse'} için distribütör kontrolleri MI serisi hızlandırıcılara talebin güçlendiğini gösteriyor."
        ),
        (
            "tesla china registrations",
            "Tesla Çin haftalık araç kayıtları piyasa beklentisinin altında seyrediyor; teslimat hedefinin kaçırılma riski artıyor."
        ),
        (
            "new defense contract",
            f"{ticker or 'Şirket'} yeni bir savunma sözleşmesi açıkladı; sözleşme büyüklüğü şirket ölçeğine göre anlamlı."
        ),
        (
            "refinery margins",
            f"{ticker or 'Şirket'} rafineri marjları beklentilerin üzerinde seyrediyor; FAVÖK tahminlerinde yukarı yönlü potansiyel bulunuyor."
        ),
        (
            "channel checks suggest organic revenue growth",
            f"{ticker or 'Şirket'} için kanal kontrolleri organik gelir büyümesinin piyasa beklentisini aşabileceğine işaret ediyor."
        ),
        (
            "government awards",
            f"{ticker or 'Şirket'} için son kamu sözleşmeleri sipariş bakiyesini ve gelir büyümesini destekleyebilir."
        ),
        (
            "passenger yield guidance",
            f"{ticker or 'Şirket'} için yolcu birim gelir beklentisi zayıfladı; doluluk güçlü kalsa da kârlılık riski arttı."
        ),
        (
            "management raised full-year guidance",
            f"{ticker or 'Şirket'} yönetimi yıl sonu beklentilerini yukarı revize etti."
        ),
        (
            "rate expectations imply potential nim improvement",
            f"{ticker or 'Banka'} için faiz beklentileri net faiz marjında iyileşme potansiyeline işaret ediyor."
        ),
        (
            "call volume",
            f"{ticker or 'Bu hisse'} opsiyonlarında call hacmi belirgin biçimde arttı; kısa vadeli pozitif akış izleniyor."
        ),
    ]
    for needle, tr in patterns:
        if needle in low:
            return tr

    # Never show hybrid/mixed language in Turkish mode.
    c = tr_category(category)
    d = tr_direction(direction)
    return f"{ticker or 'Bu hisse'} için {c.lower()} kaynaklı {d.lower()} yönlü bir gelişme tespit edildi."


# --- Hard CSS fix for dark cards / text contrast ---
st.markdown("""
<style>
:root {
    --card-bg: #111318;
    --card-border: #2a2d35;
    --card-text: #f5f7fb;
    --muted: #a7aeba;
}

.block-container {
    padding-top: 1.15rem;
    padding-bottom: 2rem;
}

h1, h2, h3 {
    letter-spacing: -0.02em;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    padding: 14px 16px !important;
    border-radius: 16px !important;
}

[data-testid="stMetric"] *,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    color: var(--card-text) !important;
}

[data-testid="stMetricLabel"] p {
    color: var(--muted) !important;
}

/* Custom event cards */
.event-card {
    background: var(--card-bg) !important;
    color: var(--card-text) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 16px;
    padding: 16px 18px;
    margin-bottom: 12px;
}

.event-card,
.event-card *,
.event-card div,
.event-card span {
    color: var(--card-text) !important;
}

.event-card .small {
    color: var(--muted) !important;
}

.badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 999px;
    background: #242832 !important;
    color: #eef2f8 !important;
    font-size: 12px;
    margin-right: 6px;
}

.small {
    color: var(--muted) !important;
    font-size: 13px;
}

/* Keep dataframe readable */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

/* Tabs */
button[data-baseweb="tab"] p {
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def load_jsonl(path, limit=None):
    rows = []
    p = Path(path).expanduser()
    if not p.exists():
        return rows
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def pct(v):
    return "—" if not isinstance(v, (int, float)) else f"%{v*100:.1f}"


def last_summary():
    for name in [
        "v091_summary.json",
        "v09_summary.json",
        "v08_summary.json",
        "v07_summary.json",
    ]:
        p = RESULTS / name
        if p.exists():
            s = load_json(p)
            if s:
                return s, name
    return None, None


summary, summary_name = last_summary()

benchmark_default = str(
    Path.home()
    / "Downloads/market_intelligence_benchmark_100k_v1/data/benchmark_100k.jsonl"
)

benchmark_path = st.sidebar.text_input("Benchmark JSONL", benchmark_default)
preview_limit = st.sidebar.slider(
    "Önizleme kayıt sayısı", 100, 5000, 1000, 100
)
st.sidebar.markdown("---")
st.sidebar.caption("Yerel kontrol paneli • Piyasa İstihbaratı")

rows = load_jsonl(benchmark_path, preview_limit)
df = pd.DataFrame(rows) if rows else pd.DataFrame()

top_left, top_right = st.columns([8, 2])
with top_right:
    language = st.selectbox(
        "Dil / Language",
        ["Türkçe", "English"],
        index=0,
        label_visibility="collapsed",
    )
lang = "tr" if language == "Türkçe" else "en"
T = UI[lang]

with top_left:
    st.title(T["title"])
    st.caption(T["caption"])

tabs = st.tabs(T["tabs"])

# ---------------- OVERVIEW ----------------
with tabs[0]:
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    if summary:
        c1.metric(T["messages"], summary.get("messages", "—"))
        c2.metric(T["precision"], pct(summary.get("precision")))
        c3.metric(T["recall"], pct(summary.get("recall")))
        c4.metric("F1", pct(summary.get("f1")))
        c5.metric(T["direction"], pct(summary.get("direction_accuracy")))
        elapsed = summary.get("elapsed_seconds") or summary.get("total_seconds")
        c6.metric(
            T["elapsed"],
            f"{elapsed:.1f} sn" if isinstance(elapsed, (int, float)) else "—",
        )
    else:
        for c, label in zip(
            [c1, c2, c3, c4, c5, c6],
            ["Mesaj", "Kesinlik", "Yakalama", "F1", "Yön Doğruluğu", "Süre"],
        ):
            c.metric(label, "—")

    st.markdown(f"### {T['pipeline']}")

    if summary:
        pipe = pd.DataFrame(
            [
                {
                    "Girdi": summary.get("messages", 0),
                    "Hızlı elenen": summary.get("fast_discarded")
                    or summary.get("discarded")
                    or 0,
                    "Aday": summary.get("candidates")
                    or summary.get("llm_reviewed")
                    or 0,
                    "Olay": summary.get("events")
                    or summary.get("duplicate_clusters")
                    or 0,
                    "8B'ye aktarılan": summary.get("large_model_escalations") or 0,
                }
            ]
        )
        st.dataframe(pipe, use_container_width=True, hide_index=True)
    else:
        st.info("Henüz çalışma özeti bulunamadı.")

    left, right = st.columns([1.4, 1])

    with left:
        st.markdown(f"### {T['recent_events']}")

        if not df.empty and "duplicate_group" in df:
            events = df[df["duplicate_group"].notna()].copy()

            if not events.empty:
                groups = (
                    events.groupby(
                        [
                            "duplicate_group",
                            "ticker",
                            "gold_category",
                            "gold_direction",
                        ],
                        dropna=False,
                    )
                    .agg(
                        mesaj=("id", "count"),
                        kaynak=("author", "nunique"),
                        ornek=("text", "first"),
                    )
                    .reset_index()
                    .sort_values(["kaynak", "mesaj"], ascending=False)
                    .head(8)
                )

                for _, r in groups.iterrows():
                    category_label = tr_category(r["gold_category"])
                    direction_label = tr_direction(r["gold_direction"])
                    event_text_tr = event_summary(
                        r["ornek"],
                        ticker=r["ticker"],
                        category=r["gold_category"],
                        direction=r["gold_direction"],
                        lang=lang,
                    )

                    st.markdown(
                        f"""
                        <div class="event-card">
                            <div>
                                <span class="badge">{r['ticker']}</span>
                                <span class="badge">{category_label}</span>
                                <span class="badge">{direction_label}</span>
                            </div>
                            <div style="font-size:16px;font-weight:700;margin-top:8px;color:#f5f7fb !important;">
                                {event_text_tr}
                            </div>
                            <div class="small" style="margin-top:8px;">
                                {int(r['kaynak'])} {T["sources"]} • {int(r['mesaj'])} {T["message_word"]} • {r['duplicate_group']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("Geçerli önizlemede olay grubu bulunamadı.")
        else:
            st.info("Olay akışı için duplicate_group alanına sahip benchmark gerekli.")

    with right:
        st.markdown(f"### {T['dataset']}")

        if not df.empty:
            d1, d2 = st.columns(2)

            if "gold_keep" in df:
                keep = df["gold_keep"].fillna(False).astype(bool)
                d1.metric(T["valuable"], int(keep.sum()))
                d2.metric(T["discard"], int((~keep).sum()))

            if "gold_category" in df:
                cat_counts = (
                    df["gold_category"]
                    .fillna("other")
                    .map(tr_category)
                    .value_counts()
                    .head(8)
                )
                st.bar_chart(cat_counts)
        else:
            st.info("Benchmark yüklenmedi.")

# ---------------- EVENTS ----------------
with tabs[1]:
    st.markdown(f"### {T['event_explorer']}")

    if not df.empty and "duplicate_group" in df:
        ev = df[df["duplicate_group"].notna()].copy()

        if ev.empty:
            st.info("Geçerli önizlemede olay grubu bulunamadı.")
        else:
            g = (
                ev.groupby(
                    [
                        "duplicate_group",
                        "ticker",
                        "gold_category",
                        "gold_direction",
                    ],
                    dropna=False,
                )
                .agg(
                    mesaj_sayisi=("id", "count"),
                    kaynak_sayisi=("author", "nunique"),
                    ornek=("text", "first"),
                    ortalama_basari=("author_true_hit_rate", "mean"),
                )
                .reset_index()
            )

            g["Kategori"] = g["gold_category"].map(tr_category)
            g["Yön"] = g["gold_direction"].map(tr_direction)
            g["Özet"] = g.apply(
                lambda r: event_summary(
                    r["ornek"],
                    ticker=r["ticker"],
                    category=r["gold_category"],
                    direction=r["gold_direction"],
                    lang=lang,
                ),
                axis=1,
            )

            display_g = g[
                [
                    "duplicate_group",
                    "ticker",
                    "Kategori",
                    "Yön",
                    "mesaj_sayisi",
                    "kaynak_sayisi",
                    "ortalama_basari",
                    "Özet",
                ]
            ].rename(
                columns={
                    "duplicate_group": "Olay",
                    "ticker": "Hisse",
                    "mesaj_sayisi": "Mesaj",
                    "kaynak_sayisi": "Kaynak",
                    "ortalama_basari": "Ort. Kaynak Başarısı",
                }
            )

            st.dataframe(display_g, use_container_width=True, hide_index=True)

            event_id = st.selectbox(
                "Olay detayı",
                g["duplicate_group"].astype(str).tolist(),
            )

            selected = ev[ev["duplicate_group"].astype(str) == event_id]

            if not selected.empty:
                r = selected.iloc[0]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Hisse", r.get("ticker", "—"))
                c2.metric("Yön", tr_direction(r.get("gold_direction")))
                c3.metric("Kaynak", selected["author"].nunique())
                c4.metric("Mesaj", len(selected))

                st.markdown(f"#### {T['source_messages']}")

                table = selected[
                    [
                        c
                        for c in [
                            "author",
                            "ticker",
                            "text",
                            "gold_keep",
                            "gold_category",
                            "gold_direction",
                            "author_true_hit_rate",
                        ]
                        if c in selected.columns
                    ]
                ].copy()

                table = table.rename(
                    columns={
                        "author": "Kaynak",
                        "ticker": "Hisse",
                        "text": "Mesaj",
                        "gold_keep": "Değerli mi?",
                        "gold_category": "Kategori",
                        "gold_direction": "Yön",
                        "author_true_hit_rate": "Kaynak Başarı Oranı",
                    }
                )

                if "Kategori" in table:
                    table["Kategori"] = table["Kategori"].map(tr_category)
                if "Yön" in table:
                    table["Yön"] = table["Yön"].map(tr_direction)

                st.dataframe(table, use_container_width=True, hide_index=True)
    else:
        st.info("Benchmark yüklenmedi.")

# ---------------- AI DECISIONS ----------------
with tabs[2]:
    st.markdown(f"### {T['ai_decisions']}")

    pred_path = RESULTS / "predictions.jsonl"
    preds = (
        pd.DataFrame(load_jsonl(pred_path, 5000))
        if pred_path.exists()
        else pd.DataFrame()
    )

    if not preds.empty:
        if "category" in preds:
            preds["category_tr"] = preds["category"].map(tr_category)
        if "direction" in preds:
            preds["direction_tr"] = preds["direction"].map(tr_direction)

        st.dataframe(preds, use_container_width=True, hide_index=True)
    else:
        st.info(
            "Henüz `results/predictions.jsonl` yok. Şimdilik Gold veri seti aşağıda gösteriliyor."
        )

        if not df.empty:
            wanted = [
                c
                for c in [
                    "id",
                    "author",
                    "ticker",
                    "text",
                    "gold_keep",
                    "gold_category",
                    "gold_direction",
                    "gold_importance",
                    "gold_confidence",
                ]
                if c in df.columns
            ]

            view = df[wanted].copy()

            view = view.rename(
                columns={
                    "id": "ID",
                    "author": "Kaynak",
                    "ticker": "Hisse",
                    "text": "Mesaj",
                    "gold_keep": "Değerli mi?",
                    "gold_category": "Kategori",
                    "gold_direction": "Yön",
                    "gold_importance": "Önem",
                    "gold_confidence": "Güven",
                }
            )

            if "Kategori" in view:
                view["Kategori"] = view["Kategori"].map(tr_category)
            if "Yön" in view:
                view["Yön"] = view["Yön"].map(tr_direction)

            st.dataframe(view.head(500), use_container_width=True, hide_index=True)

# ---------------- SOURCES ----------------
with tabs[3]:
    st.markdown(f"### {T['source_intel']}")

    if not df.empty and {"author", "author_true_hit_rate"}.issubset(df.columns):
        rel = (
            df.groupby("author", as_index=False)
            .agg(
                basari=("author_true_hit_rate", "mean"),
                paylasim=("id", "count"),
                degerli=("gold_keep", "sum"),
            )
        )

        rel["degerli_orani"] = rel["degerli"] / rel["paylasim"]
        rel = rel.sort_values(["basari", "paylasim"], ascending=[False, False])

        rel_tr = rel.rename(
            columns={
                "author": "Kaynak",
                "basari": "Başarı Oranı",
                "paylasim": "Paylaşım",
                "degerli": "Değerli Paylaşım",
                "degerli_orani": "Değerli Oranı",
            }
        )

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### En güçlü kaynaklar")
            st.dataframe(rel_tr.head(25), use_container_width=True, hide_index=True)

        with c2:
            st.markdown("#### En zayıf kaynaklar")
            st.dataframe(
                rel_tr.sort_values("Başarı Oranı").head(25),
                use_container_width=True,
                hide_index=True,
            )

        author = st.selectbox("Kaynak incele", rel["author"].tolist())
        adf = df[df["author"] == author]

        if not adf.empty:
            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Başarı", f"%{adf['author_true_hit_rate'].mean()*100:.1f}")
            a2.metric("Paylaşım", len(adf))

            if "gold_keep" in adf:
                a3.metric("Değerli", int(adf["gold_keep"].sum()))

            if "outcome" in adf:
                a4.metric("Başarılı Tahmin", int((adf["outcome"] == "success").sum()))

            table = adf[
                [
                    c
                    for c in [
                        "ticker",
                        "text",
                        "gold_keep",
                        "gold_category",
                        "gold_direction",
                        "outcome",
                    ]
                    if c in adf.columns
                ]
            ].copy()

            table = table.rename(
                columns={
                    "ticker": "Hisse",
                    "text": "Mesaj",
                    "gold_keep": "Değerli mi?",
                    "gold_category": "Kategori",
                    "gold_direction": "Yön",
                    "outcome": "Sonuç",
                }
            )

            if "Kategori" in table:
                table["Kategori"] = table["Kategori"].map(tr_category)
            if "Yön" in table:
                table["Yön"] = table["Yön"].map(tr_direction)
            if "Sonuç" in table:
                table["Sonuç"] = table["Sonuç"].replace(
                    {
                        "success": "Başarılı",
                        "fail": "Başarısız",
                        "unresolved": "Sonuçlanmadı",
                    }
                )

            st.dataframe(table.head(200), use_container_width=True, hide_index=True)
    else:
        st.info("Kaynak alanları mevcut değil.")

# ---------------- PREDICTIONS ----------------
with tabs[4]:
    st.markdown(f"### {T['pred_perf']}")

    if not df.empty and "outcome" in df:
        pred = df[df["outcome"].isin(["success", "fail"])].copy()

        if not pred.empty:
            success = (pred["outcome"] == "success").sum()
            fail = (pred["outcome"] == "fail").sum()

            p1, p2, p3 = st.columns(3)
            p1.metric("Sonuçlanan tahmin", len(pred))
            p2.metric("Başarılı", success)
            p3.metric("Başarı oranı", f"%{success/len(pred)*100:.1f}")

            if "ticker" in pred:
                by_ticker = (
                    pred.groupby("ticker")
                    .agg(
                        sonuclanan=("outcome", "count"),
                        basarili=("outcome", lambda x: (x == "success").sum()),
                    )
                    .reset_index()
                )

                by_ticker["basari_orani"] = (
                    by_ticker["basarili"] / by_ticker["sonuclanan"]
                )

                by_ticker = by_ticker.rename(
                    columns={
                        "ticker": "Hisse",
                        "sonuclanan": "Sonuçlanan",
                        "basarili": "Başarılı",
                        "basari_orani": "Başarı Oranı",
                    }
                )

                st.dataframe(
                    by_ticker.sort_values("Başarı Oranı", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("Geçerli önizlemede sonuçlanan tahmin yok.")
    else:
        st.info("Tahmin sonucu alanı mevcut değil.")

# ---------------- BENCHMARK ----------------
with tabs[5]:
    st.markdown(f"### {T['benchmark']}")

    if df.empty:
        st.warning(f"Benchmark bulunamadı: {benchmark_path}")
    else:
        f1, f2, f3, f4 = st.columns(4)

        ticker = f1.selectbox(
            "Hisse",
            ["TÜM"]
            + sorted(df["ticker"].dropna().astype(str).unique())
            if "ticker" in df
            else ["TÜM"],
            key="bench_ticker",
        )

        decision = f2.selectbox(
            "Gold karar",
            ["TÜM", "DEĞERLİ", "DEĞERSİZ"],
        )

        categories_raw = (
            sorted(df["gold_category"].dropna().astype(str).unique())
            if "gold_category" in df
            else []
        )
        category_map = {tr_category(x): x for x in categories_raw}
        category_label = f3.selectbox(
            "Kategori",
            ["TÜM"] + sorted(category_map.keys()),
        )

        author = f4.selectbox(
            "Kaynak",
            ["TÜM"]
            + sorted(df["author"].dropna().astype(str).unique())
            if "author" in df
            else ["TÜM"],
        )

        view = df.copy()

        if ticker != "TÜM":
            view = view[view["ticker"].astype(str) == ticker]

        if decision != "TÜM" and "gold_keep" in view:
            view = view[
                view["gold_keep"].astype(bool) == (decision == "DEĞERLİ")
            ]

        if category_label != "TÜM" and "gold_category" in view:
            raw_category = category_map[category_label]
            view = view[view["gold_category"].astype(str) == raw_category]

        if author != "TÜM" and "author" in view:
            view = view[view["author"].astype(str) == author]

        preferred = [
            "id",
            "author",
            "ticker",
            "text",
            "gold_keep",
            "gold_category",
            "gold_direction",
            "gold_importance",
            "gold_novelty",
            "gold_confidence",
            "duplicate_group",
            "outcome",
        ]

        table = view[
            [c for c in preferred if c in view.columns]
        ].copy()

        table = table.rename(
            columns={
                "id": "ID",
                "author": "Kaynak",
                "ticker": "Hisse",
                "text": "Mesaj",
                "gold_keep": "Değerli mi?",
                "gold_category": "Kategori",
                "gold_direction": "Yön",
                "gold_importance": "Önem",
                "gold_novelty": "Yenilik",
                "gold_confidence": "Güven",
                "duplicate_group": "Olay Grubu",
                "outcome": "Sonuç",
            }
        )

        if "Kategori" in table:
            table["Kategori"] = table["Kategori"].map(tr_category)

        if "Yön" in table:
            table["Yön"] = table["Yön"].map(tr_direction)

        if "Sonuç" in table:
            table["Sonuç"] = table["Sonuç"].replace(
                {
                    "success": "Başarılı",
                    "fail": "Başarısız",
                    "unresolved": "Sonuçlanmadı",
                }
            )

        st.dataframe(
            table.head(500),
            use_container_width=True,
            hide_index=True,
        )

# ---------------- PIPELINE ----------------
with tabs[6]:
    st.markdown(f"### {T['pipeline_details']}")

    if summary:
        st.json(summary)
        st.caption(f"Yüklenen özet dosyası: {summary_name}")
    else:
        st.info("results/ klasöründe özet JSON bulunamadı.")

    st.markdown("#### Model mimarisi")

    st.code(
        """Collector / Veri Toplayıcı
  ↓
Hızlı Filtre
  ↓
Olay / Tekrar Birleştirme
  ↓
Qwen 1.7B
  ↓
Qwen 8B (yalnızca zor olaylar)
  ↓
Sinyal Motoru
  ↓
Sonuç Motoru
  ↓
Kaynak Güvenilirliği"""
    )
