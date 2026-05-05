import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import tempfile
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
import html

# -----------------------------
# Titel
# -----------------------------
st.title("Kinetik der Bleichreaktion von Erioglaucin mit Natriumhypochlorit")

# -----------------------------
# Eingabefelder
# -----------------------------
handy = st.text_input("Hersteller und Typ des Handys:", "z.B. iPhone 14, Samsung Galaxy S10")
dimm = st.text_input("Dimmstufe:", "z.B. 1 oder 1,5")

st.markdown("**Übertragen Sie die Messdaten (zwei Messreihen):**")
text_input = st.text_area("Messdaten eingeben:", height=250)
# -----------------------------
# Parser
# -----------------------------
def parse_data(text):
    lines = text.splitlines()

    data1 = []
    data2 = []

    current_data = data1
    last_t = -np.inf
    second_started = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if ";" in line:
            parts = line.split(";")
            decimal_comma = True
        else:
            parts = line.split(",")
            decimal_comma = False

        if len(parts) != 3:
            continue

        try:
            values = []
            for p in parts:
                p = p.strip()
                if decimal_comma:
                    p = p.replace(",", ".")
                values.append(float(p))

            _, t_val, I_val = values

            if t_val < last_t and not second_started:
                current_data = data2
                second_started = True
                last_t = -np.inf

            last_t = t_val
            current_data.append((t_val, I_val))

        except:
            continue

    data1 = np.array(data1) if len(data1) >= 2 else None
    data2 = np.array(data2) if len(data2) >= 2 else None

    return data1, data2

# -----------------------------
# Linearbereich
# -----------------------------
def find_linear_range(t2, y, slope0, tol_percent=30.0):
    alpha0 = np.degrees(np.arctan(slope0))

    window_center = 20.0
    window_range = 10.0
    step_size = 2.0

    while True:
        window_start = window_center - window_range/2.0
        window_end = window_center + window_range/2.0

        mask = (t2 >= window_start) & (t2 <= window_end)
        t_win = t2[mask]
        y_win = y[mask]

        if len(t_win) < 2:
            break

        coeffs = np.polyfit(t_win, y_win, 1)
        slope = coeffs[0]

        alpha = np.degrees(np.arctan(slope))
        percent_change = abs(100.0 * (alpha - alpha0) / alpha0)

        if percent_change > tol_percent:
            return window_start + step_size

        window_center += step_size

    return window_center

# -----------------------------
# Analyse
# -----------------------------
def analyze_dataset(data, title, prefix):
    t = data[:, 0]
    I = data[:, 1]

    ymax = max(100, np.max(I))

    # Plot 1
    fig1, ax1 = plt.subplots()
    ax1.plot(t, I, 'o-')
    ax1.set_xlabel('Zeit t (s)')
    ax1.set_ylabel('Intensität I')
    ax1.set_ylim(0, ymax)
    ax1.set_title(title)
    fig1.savefig(f"{prefix}_plot1.png")
    st.pyplot(fig1)
    plt.close(fig1)

    # Transformation
    mask = I > 0.01
    t2 = t[mask]
    I2 = I[mask]

    y = np.log10(np.log10(100.0 / I2))

    mask_fit = t2 <= 20
    t_fit = t2[mask_fit]
    y_fit = y[mask_fit]

    coeffs = np.polyfit(t_fit, y_fit, 1)
    slope = coeffs[0]

    y_reg = np.polyval(coeffs, t2)
    lin_max = find_linear_range(t2, y, slope)

    # Plot 2
    fig2, ax2 = plt.subplots()
    ax2.plot(t2, y, 'o')
    ax2.plot(t2, y_reg, 'r-')
    ax2.axvline(lin_max, color='gray', linestyle='--', alpha=0.3)
    ax2.set_xlabel('Zeit t (s)')
    ax2.set_ylabel('lg(lg(100 / I))')
    ax2.set_title('Linearisierte Darstellung zur Bestimmung der Geschwindigkeitskonstanten')
    fig2.savefig(f"{prefix}_plot2.png")
    st.pyplot(fig2)
    plt.close(fig2)

    return -slope, lin_max

def create_pdf(filename, k1, k2, ratio, handy, dimm, lin_max1, lin_max2):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filename)

    story = []

    story.append(Paragraph("Kinetik der Bleichreaktion von Erioglaucin mit Natriumhypochlorit", styles["Title"]))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph(f"<b>Handytyp:</b> {html.escape(handy)}", styles["Normal"]))
    story.append(Paragraph(f"<b>Dimmstufe:</b> {html.escape(dimm)}", styles["Normal"]))
    story.append(Spacer(1, 0.2*cm))

    # Messreihe 1
    story.append(Paragraph("<b>1. Messreihe (hohe Hypochlorit-Konzentration)</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.2*cm))

    story.append(Table([[
        Image("d1_plot1.png", width=8*cm, height=6*cm),
        Image("d1_plot2.png", width=8*cm, height=6*cm)
    ]]))

    story.append(Spacer(1, 0.5*cm))

    # Messreihe 2
    story.append(Paragraph("<b>2. Messreihe (halbhohe Hypochlorit-Konzentration)</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.2*cm))

    story.append(Table([[
        Image("d2_plot1.png", width=8*cm, height=6*cm),
        Image("d2_plot2.png", width=8*cm, height=6*cm)
    ]]))

    story.append(Spacer(1, 0.5*cm))

    # Ergebnisse
    story.append(Paragraph("<b>Ergebnisse</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(f"Linearer Bereich (hohe Konzentration): {lin_max1:.1f} s", styles["Normal"]))
    story.append(Paragraph(f"Linearer Bereich (halbe Konzentration): {lin_max2:.1f} s", styles["Normal"]))

    story.append(Paragraph(f"Geschwindigkeitskonstante (hohe Konzentration): k<sub>1</sub> = {k1:.5f}", styles["Normal"]))
    story.append(Paragraph(f"Geschwindigkeitskonstante (halbe Konzentration): k<sub>2</sub> = {k2:.5f}", styles["Normal"]))
    story.append(Paragraph(f"Verhältnis: k<sub>1</sub>/k<sub>2</sub> = {ratio:.3f}. Erwarteter Wert: 2.0", styles["Normal"]))

    doc.build(story)


# -----------------------------
# Button
# -----------------------------
if st.button("Auswerten"):

    data1, data2 = parse_data(text_input)

    if data1 is None:
        st.error("Fehler: Keine gültigen Daten gefunden.")
    else:
        st.write("Messreihe 1 (hohe Hypochlorit-Konzentration)")
        k1, lin_max1 = analyze_dataset(data1, "Verlauf der Lichtintensität", "d1")

        st.write("")
        st.write(f"Linearer Bereich: {lin_max1:.1f} s")
        st.write(f"Geschwindigkeitskonstante: k₁ = {k1:.5f}")

        if data2 is not None:
            st.write("")
            st.write("Messreihe 2 (halbhohe Hypochlorit-Konzentration)")

            k2, lin_max2 = analyze_dataset(data2, "Verlauf der Lichtintensität", "d2")

            st.write("")
            st.write(f"Linearer Bereich: {lin_max2:.1f} s")
            st.write(f"Geschwindigkeitskonstante: k₂ = {k2:.5f}")
            st.write(f"Verhältnis: k₁/k₂ = {k1/k2:.3f}. Erwarteter Wert: 2.0")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = tmp.name

            create_pdf(pdf_path, k1, k2, k1/k2, handy, dimm, lin_max1, lin_max2)

#            os.remove(pdf_path)

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            st.download_button(
                label="PDF herunterladen",
                data=pdf_bytes,
                file_name="Auswertung.pdf",
                mime="application/pdf"
            )

