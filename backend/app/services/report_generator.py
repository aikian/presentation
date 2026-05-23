import io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer

# 한글 폰트 설정 (Windows Malgun Gothic)
_MALGUN = Path("C:/Windows/Fonts/malgun.ttf")
if _MALGUN.exists():
    pdfmetrics.registerFont(TTFont("KR", str(_MALGUN)))
    fm.fontManager.addfont(str(_MALGUN))
    plt.rcParams["font.family"] = "Malgun Gothic"
    _KR = "KR"
else:
    _KR = "Helvetica"


def _make_chart(gaze: float, tilt: float, gestures: int) -> bytes:
    labels = ["시선 이탈률 (%)", "어깨 기울기 (도)", "제스처 횟수 (회)"]
    values = [round(gaze * 100, 1), round(tilt, 1), gestures]
    bar_colors = [
        "#ef4444" if gaze > 0.3 else "#f59e0b" if gaze > 0.15 else "#22c55e",
        "#ef4444" if tilt > 15 else "#f59e0b" if tilt > 8 else "#22c55e",
        "#f59e0b" if gestures < 5 or gestures > 50 else "#22c55e",
    ]

    fig, ax = plt.subplots(figsize=(5.5, 2.6))
    bars = ax.barh(labels, values, color=bar_colors, height=0.45)
    ax.bar_label(bars, fmt="%.1f", padding=4, fontsize=9)
    ax.set_xlim(0, max(values) * 1.35 + 1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=9)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_report(record: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2.5 * cm, bottomMargin=2.5 * cm,
    )

    title_s = ParagraphStyle("T", fontName=_KR, fontSize=20, spaceAfter=4,
                              alignment=TA_CENTER, textColor=colors.HexColor("#1e293b"))
    date_s = ParagraphStyle("D", fontName=_KR, fontSize=10, spaceAfter=2,
                             alignment=TA_CENTER, textColor=colors.HexColor("#64748b"))
    section_s = ParagraphStyle("S", fontName=_KR, fontSize=13, spaceBefore=14, spaceAfter=6,
                                textColor=colors.HexColor("#1e293b"))
    body_s = ParagraphStyle("B", fontName=_KR, fontSize=10, leading=17,
                             textColor=colors.HexColor("#374151"))
    metric_s = ParagraphStyle("M", fontName=_KR, fontSize=10, leading=15,
                               textColor=colors.HexColor("#374151"))

    # 날짜 파싱
    try:
        dt = datetime.fromisoformat(record.get("created_at", "").replace("Z", "+00:00"))
        date_str = dt.strftime("%Y년 %m월 %d일 %H:%M")
    except Exception:
        date_str = record.get("created_at", "")

    gaze = record.get("gaze_away_ratio", 0)
    tilt = record.get("shoulder_tilt_avg", 0)
    gestures = record.get("gesture_count", 0)
    coaching = (record.get("coaching") or "코칭 없음").replace("\n", "<br/>")

    chart_png = _make_chart(gaze, tilt, gestures)
    chart_img = RLImage(io.BytesIO(chart_png), width=12 * cm, height=5.8 * cm)

    gaze_status = "좋음" if gaze <= 0.15 else "주의" if gaze <= 0.3 else "개선 필요"
    tilt_status = "좋음" if tilt <= 8 else "주의" if tilt <= 15 else "개선 필요"
    gesture_status = "적절함" if 5 <= gestures <= 50 else "주의"

    metrics_text = (
        f"• 시선 이탈률: {gaze * 100:.0f}%  ({gaze_status})<br/>"
        f"• 어깨 기울기: {tilt:.1f}도  ({tilt_status})<br/>"
        f"• 제스처 횟수: {gestures}회  ({gesture_status})"
    )

    story = [
        Paragraph("PresentationCoach 발표 분석 보고서", title_s),
        Paragraph(date_str, date_s),
        Spacer(1, 0.3 * cm),
        Paragraph("분석 지표", section_s),
        chart_img,
        Spacer(1, 0.2 * cm),
        Paragraph(metrics_text, metric_s),
        Paragraph("AI 코칭 피드백", section_s),
        Paragraph(coaching, body_s),
    ]

    doc.build(story)
    buf.seek(0)
    return buf.read()
