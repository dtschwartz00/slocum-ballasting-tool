# app.py
# Slocum G2 Ballasting Tool — Streamlit web interface
# Run with: streamlit run app.py

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

import sys
import os
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
    page_title="Slocum G2 Ballasting Tool",
    page_icon="🌊",
    layout="wide",
)

st.title("🌊 Slocum G2 Ballasting Tool")
st.caption("Upload a CTD cast or use the synthetic profile to analyze glider ballast configuration.")

# ---------------------------------------------------------------------------
# Sidebar — glider parameters
# ---------------------------------------------------------------------------
st.sidebar.header("Glider parameters")

glider_mass = st.sidebar.number_input(
    "Glider mass (kg)", value=GLIDER_MASS, step=0.001, format="%.3f"
)
glider_volume = st.sidebar.number_input(
    "Glider volume (m³)", value=GLIDER_VOLUME, step=0.00001, format="%.5f"
)
pump_range = st.sidebar.number_input(
    "Pump range (m³)", value=PUMP_RANGE, step=0.00001, format="%.5f"
)

st.sidebar.markdown("---")
st.sidebar.caption("Adjust these to match your specific glider before deployment.")

# ---------------------------------------------------------------------------
# Data source — upload or synthetic
# ---------------------------------------------------------------------------
st.subheader("1. Load CTD profile")

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

        # Sort by depth
        sort_idx    = np.argsort(depth)
        depth       = depth[sort_idx]
        temperature = temperature[sort_idx]
        salinity    = salinity[sort_idx]
    else:
        st.stop()

else:
    depth       = np.linspace(0, 200, 200)
    temperature = 20 - 10 * (1 - np.exp(-depth / 50))
    salinity    = 33 + 1.5 * (1 - np.exp(-depth / 80))
    st.caption("Using synthetic thermocline: warm fresh surface, cold salty deep.")

# ---------------------------------------------------------------------------
# Compute
# ---------------------------------------------------------------------------
rho     = density_from_ctd(depth, temperature, salinity)
results = analyze_profile(depth, rho, glider_mass, glider_volume, pump_range)
rec     = ballast_recommendation(results, glider_mass, glider_volume)

# ---------------------------------------------------------------------------
# Recommendation banner
# ---------------------------------------------------------------------------
st.subheader("2. Ballast recommendation")

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

# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
st.subheader("3. Profile analysis")

fig, axes = plt.subplots(1, 3, figsize=(13, 6), sharey=True)
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

# Panel 1 — density profile
axes[0].plot(rho, depth, color='#00b4d8', linewidth=2)
axes[0].set_xlabel("Density (kg/m³)")
axes[0].set_ylabel("Depth (m)")
axes[0].set_title("Water column density")

# Panel 2 — pump fraction
axes[1].plot(results['pump_fraction'], depth, color='#f77f00', linewidth=2)
axes[1].axvline(0,  color='#a0b4c8', linewidth=0.8, linestyle='--', alpha=0.6)
axes[1].axvline(1,  color='#e63946', linewidth=1.2, linestyle='--', label='Pump limit')
axes[1].axvline(-1, color='#e63946', linewidth=1.2, linestyle='--')
axes[1].set_xlabel("Pump fraction (−1 to +1)")
axes[1].set_title("Pump usage through column")
axes[1].legend(fontsize=8, facecolor='#0f1923', labelcolor='white')

# Panel 3 — surfacing ability
colors = ['#2dc653' if s else '#e63946' for s in results['can_surface']]
axes[2].scatter(results['pump_headroom'], depth, c=colors, s=10, zorder=3)
axes[2].axvline(0, color='#e63946', linewidth=1.2, linestyle='--', label='No headroom')
axes[2].set_xlabel("Pump headroom")
axes[2].set_title("Surfacing ability\n🟢 safe  🔴 risk of entrapment")
axes[2].legend(fontsize=8, facecolor='#0f1923', labelcolor='white')

plt.tight_layout()
st.pyplot(fig)

# ---------------------------------------------------------------------------
# Raw data table
# ---------------------------------------------------------------------------
with st.expander("View raw profile data"):
    df_out = pd.DataFrame({
        'Depth (m)':        results['depth'],
        'Density (kg/m³)':  results['rho'].round(4),
        'Pump fraction':    results['pump_fraction'].round(3),
        'Can surface':      results['can_surface'],
        'Pump headroom':    results['pump_headroom'].round(3),
    })
    st.dataframe(df_out, use_container_width=True)