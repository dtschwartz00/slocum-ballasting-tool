# src/ballast.py
# Ballasting calculations for Slocum G2 glider
# Given a CTD density profile, computes optimal ballast configuration
# and flags risk zones where the glider may not be able to surface.

import numpy as np
from density import density_from_ctd



# Slocum G2 default parameters — update these to match your specific glider
GLIDER_MASS       = 52.000   # kg  — total glider mass (weigh it)
GLIDER_VOLUME     = 0.05080  # m³  — hull displaced volume at neutral
PUMP_RANGE        = 0.000260 # m³  — total pump volume (±130 mL each side)
G                 = 9.81     # m/s²


# Core ballast math
#GOAL : GET GLIDER DENSITY = OCEAN DENSITY
def neutral_buoyancy_mass(rho_water, glider_volume=GLIDER_VOLUME):
    """
    Mass the glider needs to achieve neutral buoyancy
    in water of density rho_water

    Neutral buoyancy: glider_mass = rho_water * glider_volume
    
    Density of glider = density of tank
    Args:
        rho_water      : water density at target depth (kg/m³)
        glider_volume  : glider displaced volume (m³)

    Returns:
        m_neutral      : required glider mass for neutral buoyancy (kg)
    """
    return rho_water * glider_volume


def buoyancy_force(glider_mass, rho_water, glider_volume=GLIDER_VOLUME):
    """
    Net buoyancy force on the glider (N).
    Positive = net upward force (glider rises)
    Negative = net downward force (glider sinks)

    Args:
        glider_mass   : current glider mass including ballast (kg)
        rho_water     : local water density (kg/m³)
        glider_volume : glider displaced volume (m³)

    Returns:
        F_b : net buoyancy force (N)
    """
    return (rho_water * glider_volume - glider_mass) * G


def pump_fraction_needed(glider_mass, rho_water,
                         glider_volume=GLIDER_VOLUME,
                         pump_range=PUMP_RANGE):
    """
    Fraction of pump range needed to achieve neutral buoyancy.
    0.0   = pump at neutral (midpoint)
    +1.0  = pump fully extended (maximum buoyancy, glider lightest)
    -1.0  = pump fully retracted (minimum buoyancy, glider heaviest)

    Args:
        glider_mass   : current glider mass (kg)
        rho_water     : local water density (kg/m³)
        glider_volume : glider displaced volume (m³)
        pump_range    : total pump volume range (m³)

    Returns:
        fraction : pump fraction needed (-1 to +1), or None if out of range
    """
    m_neutral = neutral_buoyancy_mass(rho_water, glider_volume)
    delta_m   = glider_mass - m_neutral          # positive = too heavy, need to pump out
    delta_V   = delta_m / rho_water              # volume of oil to move
    fraction  = -delta_V / (pump_range / 2)      # normalize to ±1

    return fraction


# analyze a CTD profile
def analyze_profile(depth, rho,
                    glider_mass=GLIDER_MASS,
                    glider_volume=GLIDER_VOLUME,
                    pump_range=PUMP_RANGE):
    """
    Analyze the glider's buoyancy state through an entire CTD profile

    For each depth, computes:
    - Net buoyancy force
    - Pump fraction needed to be neutral
    - Whether the glider can surface from that depth

    Args:
        depth         : array of depths (m)
        rho           : array of water densities (kg/m³)
        glider_mass   : glider mass (kg)
        glider_volume : glider volume (m³)
        pump_range    : pump volume range (m³)

    Returns:
        dict with arrays for each computed quantity
    """
    F_b       = buoyancy_force(glider_mass, rho, glider_volume)
    fractions = pump_fraction_needed(glider_mass, rho, glider_volume, pump_range)

    # Can the glider surface? It needs pump fraction <= +1.0 to generate
    # enough upward buoyancy force to overcome gravity at every depth
    can_surface   = fractions <= 1.0
    can_dive      = fractions >= -1.0
    pump_headroom = 1.0 - fractions    # how much pump room is left for surfacing

    # Find the deepest depth from which the glider can still surface
    surface_risk_depths = depth[~can_surface]
    if len(surface_risk_depths) > 0:
        max_safe_depth = surface_risk_depths[0]
    else:
        max_safe_depth = depth[-1]

    return {
        'depth':            depth,
        'rho':              rho,
        'F_buoyancy':       F_b,
        'pump_fraction':    fractions,
        'can_surface':      can_surface,
        'can_dive':         can_dive,
        'pump_headroom':    pump_headroom,
        'max_safe_depth':   max_safe_depth,
    }


def ballast_recommendation(results, glider_mass=GLIDER_MASS,
                            glider_volume=GLIDER_VOLUME):
    """
    Given a profile analysis, recommend how much ballast mass to add or remove.

    Target: glider should be neutral at mid-column depth with ~30% pump headroom.

    Returns:
        dict with recommendation string and mass adjustment (kg)
    """
    mid_idx   = len(results['depth']) // 2
    rho_mid   = results['rho'][mid_idx]
    m_neutral = neutral_buoyancy_mass(rho_mid, glider_volume)
    delta_kg  = m_neutral - glider_mass
    delta_g   = delta_kg * 1000

    if abs(delta_g) < 5:
        status = 'OK'
        msg    = f"Glider is well ballasted. No adjustment needed ({delta_g:+.1f} g)."
    elif delta_g > 0:
        status = 'ADD'
        msg    = f"Glider is too light. Add {delta_g:.1f} g of ballast."
    else:
        status = 'REMOVE'
        msg    = f"Glider is too heavy. Remove {abs(delta_g):.1f} g of ballast."

    return {
        'status':      status,
        'delta_g':     delta_g,
        'message':     msg,
        'rho_target':  rho_mid,
    }


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # Synthetic profile
    depth       = np.linspace(0, 200, 200)
    temperature = 20 - 10 * (1 - np.exp(-depth / 50))
    salinity    = 33 + 1.5 * (1 - np.exp(-depth / 80))
    rho         = density_from_ctd(depth, temperature, salinity)

    results = analyze_profile(depth, rho)
    rec     = ballast_recommendation(results)

    print("\n--- Ballast Recommendation ---")
    print(rec['message'])
    print(f"Target water density:  {rec['rho_target']:.3f} kg/m³")
    print(f"Max safe dive depth:   {results['max_safe_depth']:.1f} m")

    # Plot pump fraction through the water column
    fig, axes = plt.subplots(1, 3, figsize=(12, 6), sharey=True)
    fig.suptitle("Slocum G2 — Ballast Analysis", fontsize=13)

    axes[0].plot(rho, depth, color='#0077b6', linewidth=2)
    axes[0].set_xlabel("Density (kg/m³)")
    axes[0].set_ylabel("Depth (m)")
    axes[0].set_title("Water column density")
    axes[0].invert_yaxis()
    axes[0].grid(alpha=0.3)

    axes[1].plot(results['pump_fraction'], depth, color='#f77f00', linewidth=2)
    axes[1].axvline(0, color='gray', linewidth=0.8, linestyle='--')
    axes[1].axvline(1, color='red', linewidth=0.8, linestyle='--', label='Pump limit')
    axes[1].axvline(-1, color='red', linewidth=0.8, linestyle='--')
    axes[1].set_xlabel("Pump fraction (−1 to +1)")
    axes[1].set_title("Pump usage through column")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)

    colors = ['#2dc653' if s else '#e63946' for s in results['can_surface']]
    axes[2].scatter(results['pump_headroom'], depth, c=colors, s=8)
    axes[2].axvline(0, color='red', linewidth=0.8, linestyle='--', label='No headroom')
    axes[2].set_xlabel("Pump headroom")
    axes[2].set_title("Surfacing ability\n(green = safe, red = trapped)")
    axes[2].legend(fontsize=8)
    axes[2].grid(alpha=0.3)

    plt.tight_layout()
    plt.show()