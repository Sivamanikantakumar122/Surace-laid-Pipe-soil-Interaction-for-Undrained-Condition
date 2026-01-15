import streamlit as st
import pandas as pd
from psi_backend import PSI_Undrained_Model

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="PSI Analysis (Undrained)", layout="wide")

st.title("Pipe-Soil Interaction Analysis (Undrained Case)")
st.markdown("### Python Conversion of Undrained PSI VBA Model")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Geometry & Soil Inputs")

col1, col2 = st.sidebar.columns(2)
with col1:
    Dop = st.number_input("Outer Diameter (Dop) [m]", value=0.40, format="%.3f")
    tp = st.number_input("Wall Thickness (tp) [m]", value=0.015, format="%.3f")
    Z = st.number_input("Embedment Depth (Z) [m]", value=0.10, format="%.3f")
with col2:
    Su = st.number_input("Shear Strength (Su) [kPa]", value=5.0, format="%.2f")
    OCR = st.number_input("OCR", value=1.0, format="%.2f")
    St = st.number_input("Sensitivity (St)", value=3.0, format="%.2f")

st.sidebar.header("2. Interaction Factors")
alpha = st.sidebar.number_input("Adhesion Factor (alpha)", value=1.0, format="%.2f")
rate = st.sidebar.number_input("Displacement Rate", value=1.0, format="%.2f")
sub_wt_input = st.sidebar.number_input("Submerged Wt Input (from B9)", value=18.0, help="Value from Excel Cell B9. Code will subtract 10.05 automatically.")

with st.sidebar.expander("Advanced Coefficients (SSR & Prem)"):
    st.markdown("**Concrete Surface**")
    c_ssr = [
        st.number_input("Conc SSR (Low)", value=0.25),
        st.number_input("Conc SSR (Best)", value=0.25),
        st.number_input("Conc SSR (High)", value=0.25)
    ]
    c_prem = [
        st.number_input("Conc Prem (Low)", value=0.2),
        st.number_input("Conc Prem (Best)", value=0.25),
        st.number_input("Conc Prem (High)", value=0.3)
    ]
    
    st.markdown("**PET Surface**")
    p_ssr = [
        st.number_input("PET SSR (Low)", value=0.25),
        st.number_input("PET SSR (Best)", value=0.25),
        st.number_input("PET SSR (High)", value=0.25)
    ]
    p_prem = [
        st.number_input("PET Prem (Low)", value=0.15),
        st.number_input("PET Prem (Best)", value=0.2),
        st.number_input("PET Prem (High)", value=0.25)
    ]

# --- EXECUTION ---
if st.button("Run Analysis", type="primary"):
    # Initialize Backend
    model = PSI_Undrained_Model(
        Dop, tp, Z, Su, OCR, St, alpha, rate, sub_wt_input,
        c_ssr, c_prem, p_ssr, p_prem
    )
    
    # Run Calculations
    weights, geo, df_results = model.run_simulation()
    
    # --- DISPLAY INTERMEDIATE RESULTS ---
    st.divider()
    st.subheader("Intermediate Calculations")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pipe Weight (Wp)", f"{weights['Wp']:.2f} kg/m")
    c2.metric("Flooded Weight (Wpf)", f"{weights['Wpf']:.2f} kN/m")
    c3.metric("Effective Force (V)", f"{weights['V']:.2f} kN/m")
    c4.metric("Wedging Factor (zeta)", f"{geo['zeta']:.3f}")
    
    c5, c6 = st.columns(2)
    c5.metric("Penetration Area (Abm)", f"{geo['Abm']:.4f} m²")
    
    # Visual Alert for V vs Qv
    delta_v_qv = weights['V'] - geo['Qv']
    color = "inverse" if delta_v_qv < 0 else "normal" # Streamlit doesn't support red text directly in metric, but we can use delta
    c6.metric("Soil Resistance (Qv)", f"{geo['Qv']:.2f} kN/m", delta=f"{delta_v_qv:.2f} (V-Qv)", delta_color="inverse")
    
    if weights['V'] >= geo['Qv']:
        st.error(f"WARNING: Effective Force V ({weights['V']:.2f}) >= Soil Resistance Qv ({geo['Qv']:.2f})")
    else:
        st.success("Check Passed: V < Qv")

    # --- DISPLAY TABLES ---
    st.divider()
    st.subheader("Resistance & Displacement Tables")
    
    # Split by surface for cleaner view
    st.markdown("#### Concrete Surface")
    st.dataframe(df_results[df_results["Surface"] == "Concrete"].drop(columns=["Surface"]), use_container_width=True)
    
    st.markdown("#### PET Surface")
    st.dataframe(df_results[df_results["Surface"] == "PET"].drop(columns=["Surface"]), use_container_width=True)

    # --- PLOTTING (Replaces VBA Graphs) ---
    st.divider()
    st.subheader("Force-Displacement Curves")
    
    # Allow user to select what to plot to avoid clutter
    plot_surface = st.selectbox("Select Surface to Plot", ["Concrete", "PET"])
    
    subset = df_results[df_results["Surface"] == plot_surface]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Axial Plot
    for index, row in subset.iterrows():
        # Plot simplified bilinear behavior (0 -> Break -> Res)
        x_pts = [0, row['Xbrk (mm)'], row['Xres (mm)']]
        y_pts = [0, row['Axial Brk (kN/m)'], row['Axial Res (kN/m)']]
        ax1.plot(x_pts, y_pts, marker='o', label=row['Estimate'])
    
    ax1.set_title(f"{plot_surface} - Axial Resistance")
    ax1.set_xlabel("Displacement (mm)")
    ax1.set_ylabel("Resistance (kN/m)")
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()

    # Lateral Plot
    for index, row in subset.iterrows():
        x_pts = [0, row['Ybrk (mm)'], row['Yres (mm)']]
        y_pts = [0, row['Lat Brk (kN/m)'], row['Lat Res (kN/m)']]
        ax2.plot(x_pts, y_pts, marker='o', label=row['Estimate'])

    ax2.set_title(f"{plot_surface} - Lateral Resistance")
    ax2.set_xlabel("Displacement (mm)")
    ax2.set_ylabel("Resistance (kN/m)")
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend()
    
    st.pyplot(fig)

else:
    st.info("Adjust inputs in the sidebar and click 'Run Analysis'.")


