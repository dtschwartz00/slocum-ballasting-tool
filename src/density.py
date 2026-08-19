# src/density.py
# Seawater density calculations using TEOS-10 equation of state
# Reference: McDougall & Barker (2011), gsw Python library

import numpy as np
import gsw
import matplotlib.pyplot as plt


def density_from_ctd(depth, temperature, salinity):
    """
    Compute seawater density profile from raw CTD measurements.

    Args:
        depth       : array of depths (m, positive downward)
        temperature : array of in-situ temperatures (°C)
        salinity    : array of practical salinity (PSU)

    Returns:
        rho         : array of seawater density (kg/m³)
    """
    pressure    = gsw.p_from_z(-depth, lat=0)          # depth -> pressure (dbar)
    SA          = gsw.SA_from_SP(salinity, pressure, lon=0, lat=0)  # practical -> absolute salinity
    CT          = gsw.CT_from_t(SA, temperature, pressure)          # in-situ -> conservative temp
    rho         = gsw.density.rho(SA, CT, pressure)                 # TEOS-10 density

    return rho


def plot_density_profile(depth, rho, title="Density profile"):
    """
    Plot a density vs. depth profile the way oceanographers read it:
    depth increasing downward, density on the x-axis.
    """
    fig, ax = plt.subplots(figsize=(4, 7))

    ax.plot(rho, depth, color='#0077b6', linewidth=2)
    ax.invert_yaxis()
    ax.set_xlabel("Density (kg/m³)")
    ax.set_ylabel("Depth (m)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # fake test profile — a simple thermocline
    depth       = np.linspace(0, 200, 100)
    temperature = 20 - 10 * (1 - np.exp(-depth / 50))   # warm surface, cold deep
    salinity    = 33 + 1.5 * (1 - np.exp(-depth / 80))  # fresher surface, saltier deep

    rho = density_from_ctd(depth, temperature, salinity)

    print(f"Surface density: {rho[0]:.3f} kg/m³")
    print(f"Deep density:    {rho[-1]:.3f} kg/m³")
    print(f"Max gradient:    {np.max(np.diff(rho)):.4f} kg/m³ per 2m")

    plot_density_profile(depth, rho, title="Synthetic CTD — thermocline test")