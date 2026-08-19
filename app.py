# app.py
# Slocum G2 Ballasting Tool — 5-step guided workflow
# Run with: streamlit run app.py

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from density import density_from_ctd
from ballast import (
    analyze_profile,
    ballast_recommendation,
    GLIDER_MASS,
    GLIDER_VOLUME,
    PUMP_RANGE,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Slocum Glider G2 Ballasting Tool",
    layout="wide",
)

st.markdown("""
<style>
html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
    }

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 12px;
}
.stTabs [data-baseweb="tab"] {
    font-size: 16px;
    font-weight: 500;
    padding: 16px 20px;
    border-radius: 6px;
    border: 1.5px solid #00b4d8;
    color: #00b4d8;
    background-color: transparent;
}
.stTabs [aria-selected="true"] {
    background-color: #00b4d8;
    color: #0f1923;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

st.title("Slocum G2 Ballasting Tool")
st.caption("Step-by-step guided ballasting workflow for Slocum G2 gliders. This tool was created using the RUTGERS University RUCOOL Ballasting SOP")

# ---------------------------------------------------------------------------
# Step tabs
# ---------------------------------------------------------------------------
steps = st.tabs([
    "① Volume",
    "② Density & Ballast",
    "③ Trim / Balance",
    "④ Roll",
    "⑤ H-Moment",
])


# ===========================================================================
# STEP 1 — Volume
# ===========================================================================
with steps[0]:
    st.header("Step 1 — Glider Volume & Mass")
    st.markdown("Enter the volume and the weighed glider mass. These values feed into every subsequent calculation.")

    col1, col2 = st.columns(2)
    with col1:
        glider_volume_L = st.number_input(
            "Glider volume (L)",
            value=55.0, step=0.1, format="%.1f", 
            help="G2 volume is typically 55-60L. If your entered volume is outside this range, double-check with Teledyne specs"
        )
        glider_volume = glider_volume_L / 1000.0   # convert to m³

    with col2:
        glider_mass = st.number_input(
            "Total glider mass — weighed (kg)",
            value=GLIDER_MASS, step=0.001, format="%.3f",
            help="Weigh glider with all components installed for mission - wings, batteries, additional sensors, etc."
        )

    st.session_state['glider_volume'] = glider_volume
    st.session_state['glider_mass']   = glider_mass

    st.divider()

    # Sigma rule of thumb
    st.subheader("Rule of thumb — ballast sigma")
    glider_volume_mL = glider_volume_L * 1000
    sigma_g = 0.001 * glider_volume_mL
    pump_range_mL = PUMP_RANGE * 1e6 / 2    # half pump range in mL
    sigma_count = pump_range_mL / sigma_g
    if 55.0 <= glider_volume_L <= 60.0:
        st.success(f"SUCCESS! Volume {glider_volume_L:.1f}L is within expected G2 range (55-60L)")
    else:
        st.warning(f"WARNING! Volume {glider_volume_L:.1f}L is outside typical G2 range (55-60L)")

    col1, col2, col3 = st.columns(3)
    col1.metric("Glider volume", f"{glider_volume_mL:.0f} mL")
    col2.metric("1 sigma", f"{sigma_g:.1f} g", help="Mass needed to shift density by 0.001 g/mL")
    col3.metric("Pump authority", f"±{sigma_count:.1f} sigma", help="How many sigma the pump can correct")

    st.info(f"**Interpretation:** A 0.001 g/mL density error requires **{sigma_g:.1f} g** of ballast correction. "
            f"Your pump can compensate up to **±{sigma_count:.1f} sigma** — anything beyond that requires physical ballast adjustment.")


# ===========================================================================
# STEP 2 — Density & Ballast
# ===========================================================================
with steps[1]:
    st.header("Step 2 — Density & Ballast Recommendation")

    glider_volume = st.session_state.get('glider_volume', GLIDER_VOLUME)
    glider_mass   = st.session_state.get('glider_mass', GLIDER_MASS)

    col1, col2 = st.columns(2)
    with col1:
        tank_density = st.number_input("Tank density (kg/m³)", value=1020.1, step=0.1, format="%.1f")
        weight_in_tank = st.number_input("Weight in tank (g)", value=26.0, step=1.0, format="%.1f",
                                          help="Scale reading when glider is submerged in tank")

    with col2:
        target_density = st.number_input("Target deployment density (kg/m³)", value=1025.0, step=0.1, format="%.1f", 
                                         help="Ballast for the lowest surface density across deployment span - NOT the avg. Ballast no more than 2.5 sigma units higher than this unless experienced glider pilot"
                                         )

    st.divider()
    st.subheader("CTD profile")
    data_source = st.radio(
        "Data source",
        ["Use synthetic profile (thermocline test)", "Upload CTD CSV file"],
        horizontal=True,
    )

    if data_source == "Upload CTD CSV file":
        st.info("CSV must have columns: **depth** (m), **temperature** (°C), **salinity** (PSU)")
        uploaded = st.file_uploader("Upload CTD CSV", type=["csv"])
        if uploaded is not None:
            df = pd.read_csv(uploaded)
            st.write("Preview:", df.head())
            col_depth = st.selectbox("Depth column", df.columns.tolist())
            col_temp  = st.selectbox("Temperature column", df.columns.tolist(), index=1)
            col_sal   = st.selectbox("Salinity column", df.columns.tolist(), index=2)
            depth       = df[col_depth].values.astype(float)
            temperature = df[col_temp].values.astype(float)
            salinity    = df[col_sal].values.astype(float)
            sort_idx    = np.argsort(depth)
            depth, temperature, salinity = depth[sort_idx], temperature[sort_idx], salinity[sort_idx]
        else:
            st.stop()
    else:
        depth       = np.linspace(0, 200, 200)
        temperature = 20 - 10 * (1 - np.exp(-depth / 50))
        salinity    = 33 + 1.5 * (1 - np.exp(-depth / 80))
        st.caption("Synthetic thermocline: warm fresh surface, cold salty deep.")

    rho     = density_from_ctd(depth, temperature, salinity)
    results = analyze_profile(depth, rho, glider_mass, glider_volume, PUMP_RANGE)
    rec     = ballast_recommendation(results, glider_mass, glider_volume)

    st.divider()
    st.subheader("Ballast recommendation")
    st.info("Always confirm m_ballast_pumped = 0 and m_battpos = 0 before dunk")

    if rec['status'] == 'OK':
        st.success(rec['message'])
    elif rec['status'] == 'ADD':
        st.warning(rec['message'])
    else:
        st.error(rec['message'])

    col1, col2, col3 = st.columns(3)
    col1.metric("Target density", f"{rec['rho_target']:.3f} kg/m³")
    col2.metric("Mass adjustment", f"{rec['delta_g']:+.1f} g")
    col3.metric("Max safe depth", f"{results['max_safe_depth']:.1f} m")

    # Plots
    fig, axes = plt.subplots(1, 3, figsize=(13, 5), sharey=True)
    fig.patch.set_facecolor('#0f1923')
    for ax in axes:
        ax.set_facecolor('#0f1923')
        ax.tick_params(colors='#a0b4c8')
        ax.xaxis.label.set_color('#a0b4c8')
        ax.yaxis.label.set_color('#a0b4c8')
        ax.title.set_color('white')
        for spine in ax.spines.values():
            spine.set_edgecolor('#2a3f5f')
        ax.grid(alpha=0.15, color='white')
        ax.invert_yaxis()

    axes[0].plot(rho, depth, color='#00b4d8', linewidth=2)
    axes[0].set_xlabel("Density (kg/m³)")
    axes[0].set_ylabel("Depth (m)")
    axes[0].set_title("Water column density")

    axes[1].plot(results['pump_fraction'], depth, color='#f77f00', linewidth=2)
    axes[1].axvline(0,  color='#a0b4c8', linewidth=0.8, linestyle='--', alpha=0.6)
    axes[1].axvline(1,  color='#e63946', linewidth=1.2, linestyle='--', label='Pump limit')
    axes[1].axvline(-1, color='#e63946', linewidth=1.2, linestyle='--')
    axes[1].set_xlabel("Pump fraction (−1 to +1)")
    axes[1].set_title("Pump usage through column")
    axes[1].legend(fontsize=8, facecolor='#0f1923', labelcolor='white')

    colors = ['#2dc653' if s else '#e63946' for s in results['can_surface']]
    axes[2].scatter(results['pump_headroom'], depth, c=colors, s=10, zorder=3)
    axes[2].axvline(0, color='#e63946', linewidth=1.2, linestyle='--', label='No headroom')
    axes[2].set_xlabel("Pump headroom")
    axes[2].set_title("Surfacing ability\n🟢 safe  🔴 risk of entrapment")
    axes[2].legend(fontsize=8, facecolor='#0f1923', labelcolor='white')

    plt.tight_layout()
    st.pyplot(fig)

    with st.expander("View raw profile data"):
        df_out = pd.DataFrame({
            'Depth (m)':        results['depth'],
            'Density (kg/m³)':  results['rho'].round(4),
            'Pump fraction':    results['pump_fraction'].round(3),
            'Can surface':      results['can_surface'],
            'Pump headroom':    results['pump_headroom'].round(3),
        })
        st.dataframe(df_out, use_container_width=True)


# ===========================================================================
# STEP 3 — Trim / Balance
# ===========================================================================
with steps[2]:
    st.header("Step 3 — Trim / Balance")
    st.markdown("With the glider suspended in the tank, record the fore and aft scale readings. ")
    st.info("Place scales equal distant from glider's center of gravity which is approx. the middle of the science bay")

    col1, col2, col3 = st.columns(3)
    with col1:
        s1 = st.number_input("S1 — fore scale reading (g)", value=0.0, step=0.1, format="%.1f", help="Weight in Tank = Scale reading - external weights added to submerge glider")
    with col2:
        s2 = st.number_input("S2 — aft scale reading (g)", value=0.0, step=0.1, format="%.1f")
    with col3:
        tank_den_trim = st.number_input("Tank density (kg/m³)", value=1020.1, step=0.1,
                                         format="%.1f", key="trim_tank_den")

    glider_mass = st.session_state.get('glider_mass', GLIDER_MASS)
    glider_volume = st.session_state.get('glider_volume', GLIDER_VOLUME)

    st.divider()

    delta = s1 - s2
    col1, col2, col3 = st.columns(3)
    col1.metric("S1 (fore)", f"{s1:.1f} g")
    col2.metric("S2 (aft)", f"{s2:.1f} g")
    col3.metric("S1 − S2", f"{delta:+.1f} g")

    if abs(delta) < 10:
        st.success(f"✅ Trim is balanced. S1 − S2 = {delta:+.1f} g — within acceptable range.")
    elif abs(delta) < 30:
        heavier = "fore" if delta < 0 else "aft"
        st.warning(f"⚠️ Minor trim offset. Glider is {abs(delta):.1f} g {heavier}-heavy. "
                   f"Consider shifting ballast fore/aft.")
    else:
        heavier = "fore" if delta < 0 else "aft"
        st.error(f"🚨 Significant trim imbalance. Glider is {abs(delta):.1f} g {heavier}-heavy. "
                 f"Adjust ballast bottles before deployment.")

    # Visual balance indicator
    st.divider()
    st.subheader("Balance visualization")
    fig, ax = plt.subplots(figsize=(8, 2.5))
    fig.patch.set_facecolor('#0f1923')
    ax.set_facecolor('#0f1923')

    max_val = max(abs(s1), abs(s2), 1)
    bar_colors = ['#2dc653' if abs(delta) < 10 else '#f77f00' if abs(delta) < 30 else '#e63946'] * 2
    ax.barh(['S2 (aft)', 'S1 (fore)'], [s2, s1], color=bar_colors, height=0.4)
    ax.axvline(0, color='white', linewidth=0.8, alpha=0.4)
    ax.set_xlabel("Scale reading (g)", color='#a0b4c8')
    ax.tick_params(colors='#a0b4c8')
    for spine in ax.spines.values():
        spine.set_edgecolor('#2a3f5f')
    ax.set_title("Fore / Aft balance", color='white')
    plt.tight_layout()
    st.pyplot(fig)


# ===========================================================================
# STEP 4 — Roll
# ===========================================================================
with steps[3]:
    st.header("Step 4 — Roll")
    st.info("Get the glider to just negatively buoyant before reading roll — "
        "use the ballast pump to obtain ±~200g. Read roll while glider is hovering, barely submerged.")
    st.markdown("With the glider in LAB MODE and suspended horizontally in the tank, "
                "record the roll angle from the glider's IMU. Target is 0°.")

    roll_angle = st.number_input(
        "Roll angle — from glider IMU (degrees)",
        value=0.0, step=0.1, format="%.1f",
        help="Read this from the glider's lab mode output"
    )

    st.divider()

    col1, col2 = st.columns(2)
    col1.metric("Roll angle", f"{roll_angle:.1f}°", delta=f"{roll_angle:.1f}° from target")

    if abs(roll_angle) < 2:
        st.success(f"Roll is within tolerance ({roll_angle:.1f}°). Glider is laterally balanced.")
    elif abs(roll_angle) < 5:
        side = "port" if roll_angle < 0 else "starboard"
        st.warning(f"Minor roll offset ({roll_angle:.1f}°). Glider is rolling {side}. "
                   f"Shift lateral ballast to compensate.")
    else:
        side = "port" if roll_angle < 0 else "starboard"
        st.error(f"Significant roll ({roll_angle:.1f}°). Glider is heavily {side}-biased. "
                 f"Resolve before deployment — pitch battery may not compensate.")

    # Roll gauge
    st.divider()
    fig, ax = plt.subplots(figsize=(6, 3))
    fig.patch.set_facecolor('#0f1923')
    ax.set_facecolor('#0f1923')

    theta = np.linspace(-30, 30, 300)
    ax.plot(theta, np.zeros_like(theta), color='#2a3f5f', linewidth=40, solid_capstyle='round')
    ax.axvline(0, color='#a0b4c8', linewidth=1, linestyle='--', alpha=0.5, label='Target (0°)')

    color = '#2dc653' if abs(roll_angle) < 2 else '#f77f00' if abs(roll_angle) < 5 else '#e63946'
    ax.axvline(roll_angle, color=color, linewidth=3, label=f'Current ({roll_angle:.1f}°)')

    ax.fill_betweenx([-1, 1], -2, 2, alpha=0.15, color='#2dc653', label='OK zone (±2°)')
    ax.set_xlim(-30, 30)
    ax.set_ylim(-1, 1)
    ax.set_xlabel("Roll angle (degrees)", color='#a0b4c8')
    ax.tick_params(colors='#a0b4c8')
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_edgecolor('#2a3f5f')
    ax.set_title("Roll gauge  (+ = starboard,  − = port)", color='white')
    ax.legend(facecolor='#0f1923', labelcolor='white', fontsize=8)
    plt.tight_layout()
    st.pyplot(fig)


# ===========================================================================
# STEP 5 — H-Moment
# ===========================================================================
with steps[4]:
    st.header("Step 5 — H-Moment (Stability)")
    st.markdown(
        "The H-moment is the vertical distance between the glider's center of buoyancy and "
        "center of gravity."
    )
    st.caption("Only required for new glider, new payload configuration, or new/strange sensors.")

    col1, col2 = st.columns(2)
    with col1:
        angle_before = st.number_input("Roll angle — before adding weight (°)",
                                        value=0.0, step=0.1, format="%.2f")
        angle_after  = st.number_input("Roll angle — after adding weight (°)",
                                        value=2.5, step=0.1, format="%.2f")
    with col2:
        weight_added = st.number_input("Weight added (g)", value=290.0, step=1.0, format="%.1f", help= "When unsure, keep weight low. A stable glider (higher H-moment) is safer than an unstable one")
        hull_radius  = st.number_input("Radius of hull (mm)",
                                        value=107.0, step=1.0, format="%.1f",
                                        help="107mm for G2, 125mm for G2+")

    glider_mass = st.session_state.get('glider_mass', GLIDER_MASS)

    st.divider()

    delta_angle_deg = angle_after - angle_before
    delta_angle_rad = np.radians(abs(delta_angle_deg))

    if delta_angle_rad > 0:
        h_moment_mm = (weight_added * hull_radius) / (glider_mass * 1000 * np.sin(delta_angle_rad))
    else:
        h_moment_mm = 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Δ Roll angle", f"{delta_angle_deg:.2f}°")
    col2.metric("H-moment", f"{h_moment_mm:.2f} mm")
    col3.metric("Target range", "4 – 8 mm")

    if 4 <= h_moment_mm <= 8:
        st.success(f"✅ H-moment is {h_moment_mm:.2f} mm — within the 4–8 mm target range. Glider is stable.")
    elif h_moment_mm < 4:
        st.warning(f"⚠️ H-moment is {h_moment_mm:.2f} mm — below target. Glider may be unstable. "
                   f"Move weight lower to increase stability.")
    elif h_moment_mm > 8:
        st.warning(f"⚠️ H-moment is {h_moment_mm:.2f} mm — above target. Glider is over-stable. "
                   f"Pitch battery will work harder to maintain glide angle.")
    else:
        st.info("Enter angle before and after to compute H-moment.")

    # H-moment gauge
    st.divider()
    fig, ax = plt.subplots(figsize=(7, 2.5))
    fig.patch.set_facecolor('#0f1923')
    ax.set_facecolor('#0f1923')

    ax.barh(['H-moment'], [h_moment_mm],
            color='#2dc653' if 4 <= h_moment_mm <= 8 else '#f77f00',
            height=0.3)
    ax.axvline(4, color='#2dc653', linewidth=1.5, linestyle='--', label='Min (4 mm)')
    ax.axvline(8, color='#2dc653', linewidth=1.5, linestyle='--', label='Max (8 mm)')
    ax.fill_betweenx([-1, 1], 4, 8, alpha=0.1, color='#2dc653')
    ax.set_xlim(0, max(15, h_moment_mm + 2))
    ax.set_xlabel("H-moment (mm)", color='#a0b4c8')
    ax.tick_params(colors='#a0b4c8')
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_edgecolor('#2a3f5f')
    ax.set_title("H-moment gauge", color='white')
    ax.legend(facecolor='#0f1923', labelcolor='white', fontsize=8)
    plt.tight_layout()
    st.pyplot(fig)

    st.divider()
    st.subheader("Formula used")
    st.latex(r"H = \frac{W_{added} \times R_{hull}}{M_g \times \sin(\Delta\theta)}")
    st.caption("Where W_added is weight added (g), R_hull is hull radius (mm), "
               "M_g is glider mass (g), and Δθ is change in roll angle (radians).")